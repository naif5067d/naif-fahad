from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from utils.auth import get_current_user
from utils.workflow import (
    WORKFLOW_MAP, should_skip_supervisor_stage, 
    build_workflow_for_transaction, get_employee_by_user_id,
    should_escalate_to_ceo
)
from utils.leave_rules import (
    get_employee_with_contract, validate_leave_request, 
    get_leave_balance, get_all_holidays
)
from services.hr_policy import (
    check_blocking_transaction,
    get_status_for_viewer,
    format_datetime_riyadh
)
from routes.transactions import get_next_ref_no
from datetime import datetime, timezone
from typing import Optional
import uuid

router = APIRouter(prefix="/api/leave", tags=["leave"])


class LeaveRequest(BaseModel):
    leave_type: str  # annual, sick, emergency, marriage, bereavement, exam, unpaid
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    reason: str
    medical_file_url: Optional[str] = None  # مطلوب للإجازة المرضية


@router.post("/request")
async def create_leave_request(req: LeaveRequest, user=Depends(get_current_user)):
    """
    Create a leave request with full pre-validation.
    Validates:
    - Employee is active with contract
    - No blocking transaction of same type (قاعدة Blocking)
    - Sufficient leave balance
    - No overlapping dates
    - Holiday adjustments
    - Medical file for sick leave
    """
    # التحقق من رفع ملف للإجازة المرضية
    if req.leave_type == 'sick' and not req.medical_file_url:
        raise HTTPException(
            status_code=400, 
            detail="الإجازة المرضية تتطلب رفع ملف تقرير طبي PDF"
        )
    
    # Step 1: Validate employee and contract
    emp, contract, errors = await get_employee_with_contract(user['user_id'])
    
    if errors:
        # Return first error - بالعربية دائماً
        error = errors[0]
        raise HTTPException(status_code=400, detail=error.get('message_ar', error['message']))
    
    # Step 1.5: قاعدة Blocking - التحقق من عدم وجود معاملة نشطة من نفس النوع
    is_blocked, blocking_tx = await check_blocking_transaction(emp['id'], 'leave_request')
    
    if is_blocked:
        raise HTTPException(
            status_code=400,
            detail=f"لديك طلب إجازة قيد المراجعة ({blocking_tx['ref_no']}). يجب انتظار تنفيذه أو إلغائه قبل تقديم طلب جديد."
        )
    
    # Step 2: Validate leave request (balance, overlap, dates)
    validation = await validate_leave_request(
        employee=emp,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date
    )
    
    if not validation['valid']:
        error = validation['errors'][0]
        # تحسين رسائل الخطأ بالعربي
        error_msg = error.get('message_ar', error.get('message', ''))
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Step 3: Determine workflow (skip supervisor if applicable)
    skip_supervisor = await should_skip_supervisor_stage(emp, user['user_id'])
    escalate_to_ceo = await should_escalate_to_ceo(emp, user['user_id'], user.get('role', ''))
    
    base_workflow = WORKFLOW_MAP["leave_request"][:]
    workflow = build_workflow_for_transaction(base_workflow, skip_supervisor)
    
    # إذا سلطان/ناif يرفع طلب لنفسه، يذهب مباشرة للـ CEO
    if escalate_to_ceo:
        # إزالة ops من workflow وإضافة ceo قبل stas
        workflow = [s for s in workflow if s != 'ops']
        if 'ceo' not in workflow:
            stas_idx = workflow.index('stas') if 'stas' in workflow else len(workflow)
            workflow.insert(stas_idx, 'ceo')
    
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()
    ref_no = await get_next_ref_no()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "leave_request",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": emp['id'],
        "data": {
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "adjusted_end_date": validation['adjusted_end_date'],
            "working_days": validation['working_days'],
            "reason": req.reason,
            "employee_name": emp.get('full_name', ''),
            "employee_name_ar": emp.get('full_name_ar', ''),
            "balance_before": validation['balance_before'],
            "balance_after": validation['balance_after'],
            "sick_tier_info": validation.get('sick_tier_info'),
            "medical_file_url": req.medical_file_url,  # ملف التقرير الطبي للإجازة المرضية
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "workflow_skipped_stages": (['supervisor'] if skip_supervisor else []) + (['ops'] if escalate_to_ceo else []),
        "self_request_escalated": escalate_to_ceo,  # علامة للإشارة أن هذا طلب ذاتي تم تصعيده
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Leave request: {req.leave_type}, {validation['working_days']} working days",
            "stage": "created"
        }],
        "approval_chain": [],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }

    # Add warnings to transaction data if any
    if validation.get('warnings'):
        tx['data']['warnings'] = validation['warnings']

    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx


@router.get("/balance")
async def get_my_leave_balance(user=Depends(get_current_user)):
    """Get current user's leave balance breakdown - Pro-Rata"""
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="لست موظفاً")
    
    # استخدام خدمة الإجازات الجديدة Pro-Rata
    from services.hr_policy import calculate_pro_rata_entitlement, get_employee_annual_policy
    
    try:
        pro_rata = await calculate_pro_rata_entitlement(emp['id'])
        policy = await get_employee_annual_policy(emp['id'])
        
        # تنسيق النتيجة للفرونتند
        balance = {
            "annual": {
                "balance": round(pro_rata.get('available_balance', 0), 2),
                "available": round(pro_rata.get('available_balance', 0), 2),
                "earned_to_date": round(pro_rata.get('earned_to_date', 0), 2),
                "used": pro_rata.get('used_executed', 0),
                "entitlement": policy['days'],
                "policy_source": policy['source'],
                "policy_source_ar": policy['source_ar'],
                "formula": pro_rata.get('formula', ''),
                "message_ar": pro_rata.get('message_ar', '')
            }
        }
        
        return balance
    except Exception:
        # Fallback
        balance = {"annual": {"available": 0, "balance": 0}}
        return balance


@router.get("/used")
async def get_my_used_leaves(user=Depends(get_current_user)):
    """Get current user's consumed leaves by type"""
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="لست موظفاً")
    
    # جلب الإجازات المستهلكة من leave_ledger
    used = {}
    for leave_type in ['annual', 'sick', 'marriage', 'bereavement', 'exam', 'unpaid']:
        entries = await db.leave_ledger.find({
            "employee_id": emp['id'],
            "leave_type": leave_type,
            "type": "debit"
        }, {"_id": 0}).to_list(500)
        
        used[leave_type] = sum(e.get('days', 0) for e in entries)
    
    return used


class SickPreviewRequest(BaseModel):
    start_date: str
    end_date: str


@router.post("/sick-preview")
async def preview_sick_leave_deduction(req: SickPreviewRequest, user=Depends(get_current_user)):
    """
    معاينة خصم الإجازة المرضية حسب المادة 117
    يُعرض للموظف قبل تقديم الطلب
    """
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="لست موظفاً")
    
    from services.hr_policy import calculate_sick_leave_consumption, get_sick_leave_tier_for_request
    from utils.leave_rules import calculate_working_days
    
    # حساب عدد أيام العمل
    holidays = await db.public_holidays.find({}, {"date": 1, "_id": 0}).to_list(500)
    holiday_dates = [h['date'] for h in holidays]
    working_days = calculate_working_days(req.start_date, req.end_date, holiday_dates)
    
    # جلب الاستهلاك الحالي
    consumption = await calculate_sick_leave_consumption(emp['id'])
    current_used = consumption.get('total_sick_days_used', 0)
    
    # جلب توزيع الأيام الجديدة على الشرائح
    tier_info = await get_sick_leave_tier_for_request(emp['id'], working_days)
    
    # تحديد إذا كان هناك تحذير (دخول شريحة خصم)
    has_warning = False
    if tier_info.get('distribution'):
        for tier in tier_info['distribution']:
            if tier['salary_percent'] < 100:
                has_warning = True
                break
    
    return {
        "warning": has_warning,
        "current_used": current_used,
        "max_per_year": 120,
        "remaining": 120 - current_used,
        "requested_days": working_days,
        "tier_distribution": tier_info.get('distribution', []),
        "message_ar": tier_info.get('message_ar', ''),
        "current_tier_info": consumption.get('current_tier_info', {})
    }


@router.get("/permission-hours")
async def get_my_permission_hours(user=Depends(get_current_user)):
    """Get current user's permission hours usage for this month"""
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="لست موظفاً")
    
    # جلب ساعات الاستئذان من العقد
    contract = await db.contracts_v2.find_one({
        "employee_id": emp['id'],
        "status": "active"
    }, {"_id": 0})
    
    total_hours = 2  # الافتراضي
    if contract:
        total_hours = contract.get('monthly_permission_hours', 2)
    
    # جلب الاستخدام هذا الشهر
    today = datetime.now(timezone.utc)
    month_start = today.strftime("%Y-%m-01")
    month_end = today.strftime("%Y-%m-31")
    
    permissions = await db.permission_ledger.find({
        "employee_id": emp['id'],
        "date": {"$gte": month_start, "$lte": month_end},
        "type": "debit"
    }, {"_id": 0}).to_list(100)
    
    used_hours = sum(p.get('hours', 0) for p in permissions)
    
    return {
        "used": used_hours,
        "total": total_hours,
        "remaining": max(0, total_hours - used_hours),
        "month": today.strftime("%Y-%m")
    }


@router.get("/holidays")
async def get_holidays():
    """Get all holidays (system + manual)"""
    holidays = await db.public_holidays.find({}, {"_id": 0}).to_list(100)
    manual_holidays = await db.holidays.find({}, {"_id": 0}).to_list(100)
    
    all_holidays = []
    for h in holidays:
        h['source'] = 'system'
        all_holidays.append(h)
    for h in manual_holidays:
        h['source'] = 'manual'
        all_holidays.append(h)
    
    all_holidays.sort(key=lambda x: x.get('date', ''))
    return all_holidays


@router.post("/holidays")
async def add_holiday(req: dict, user=Depends(get_current_user)):
    """Add a holiday - Sultan, Naif, STAS only"""
    if user.get('role') not in ('sultan', 'naif', 'stas'):
        raise HTTPException(status_code=403, detail="غير مصرح")
    name = req.get('name')
    name_ar = req.get('name_ar', '')
    date = req.get('date')
    if not name or not date:
        raise HTTPException(status_code=400, detail="name and date required")
    holiday = {
        "id": str(uuid.uuid4()),
        "name": name,
        "name_ar": name_ar or name,
        "date": date,
        "created_by": user['user_id'],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.public_holidays.insert_one(holiday)
    holiday.pop('_id', None)
    return holiday


@router.put("/holidays/{holiday_id}")
async def update_holiday(holiday_id: str, req: dict, user=Depends(get_current_user)):
    """Update a holiday - Sultan, Naif, STAS only"""
    if user.get('role') not in ('sultan', 'naif', 'stas'):
        raise HTTPException(status_code=403, detail="غير مصرح")
    update = {}
    if 'name' in req:
        update['name'] = req['name']
    if 'name_ar' in req:
        update['name_ar'] = req['name_ar']
    if 'date' in req:
        update['date'] = req['date']
    if update:
        result = await db.public_holidays.update_one({"id": holiday_id}, {"$set": update})
        if result.matched_count == 0:
            await db.holidays.update_one({"id": holiday_id}, {"$set": update})
    updated = await db.public_holidays.find_one({"id": holiday_id}, {"_id": 0})
    if not updated:
        updated = await db.holidays.find_one({"id": holiday_id}, {"_id": 0})
    return updated


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, user=Depends(get_current_user)):
    """Delete a holiday - Sultan, Naif, STAS only"""
    if user.get('role') not in ('sultan', 'naif', 'stas'):
        raise HTTPException(status_code=403, detail="غير مصرح")
    r1 = await db.public_holidays.delete_one({"id": holiday_id})
    if r1.deleted_count == 0:
        await db.holidays.delete_one({"id": holiday_id})
    return {"message": "Holiday deleted"}
