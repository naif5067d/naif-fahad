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
    """Get current user's leave balance breakdown"""
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="لست موظفاً")
    
    # استخدام خدمة الإجازات الجديدة
    from services.leave_service import get_employee_leave_summary
    
    try:
        summary = await get_employee_leave_summary(emp['id'])
        
        # تنسيق النتيجة للفرونتند
        balance = {
            "annual": {
                "balance": summary['annual_leave']['balance'],
                "entitlement": summary['annual_leave']['entitlement'],
                "used": summary['annual_leave']['used'],
                "available": summary['annual_leave']['balance'],
                "rule": summary['annual_leave']['rule'],
                "message_ar": summary['annual_leave']['message_ar']
            },
            "sick": {
                "used_12_months": summary['sick_leave']['used_12_months'],
                "remaining": summary['sick_leave']['remaining'],
                "total_limit": summary['sick_leave']['total_limit'],
                "current_tier": summary['sick_leave']['current_tier'],
                "note_ar": summary['sick_leave']['note_ar']
            },
            "marriage": summary['other_leaves'].get('marriage', {'total_days': 0}),
            "bereavement": summary['other_leaves'].get('bereavement', {'total_days': 0}),
            "exam": summary['other_leaves'].get('exam', {'total_days': 0}),
            "unpaid": summary['other_leaves'].get('unpaid', {'total_days': 0}),
        }
        
        return balance
    except Exception as e:
        # Fallback للنظام القديم
        balance = {}
        for leave_type in ['annual', 'sick', 'marriage', 'bereavement', 'exam', 'unpaid']:
            balance[leave_type] = await get_leave_balance(emp['id'], leave_type)
        return balance


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
