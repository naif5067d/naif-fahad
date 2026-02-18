from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from utils.pdf import generate_transaction_pdf
from datetime import datetime, timezone
import uuid
import hashlib

# Import Services
from services.stas_mirror_service import build_pre_checks, build_mirror_data
from services.settlement_service import (
    validate_settlement_request, 
    aggregate_settlement_data, 
    execute_settlement
)
from services.leave_service import get_leave_balance
from services.attendance_service import (
    get_ramadan_settings, 
    set_ramadan_mode, 
    deactivate_ramadan_mode,
    calculate_daily_attendance
)
from services.notification_service import (
    notify_transaction_executed,
    create_notification,
    NotificationType,
    NotificationPriority
)

router = APIRouter(prefix="/api/stas", tags=["stas"])


class HolidayCreate(BaseModel):
    name: str
    name_ar: str
    date: str  # YYYY-MM-DD


class PurgeRequest(BaseModel):
    confirm: bool = False


class RamadanModeRequest(BaseModel):
    start_date: str
    end_date: str
    work_start: Optional[str] = "09:00"
    work_end: Optional[str] = "15:00"


class ReturnRequest(BaseModel):
    note: Optional[str] = None


async def run_pre_checks(tx):
    """
    تشغيل الفحوصات المسبقة باستخدام Service Layer
    """
    return await build_pre_checks(tx)


async def get_trace_links(tx):
    links = []
    emp_id = tx.get('employee_id')
    tx_type = tx.get('type')

    if emp_id:
        emp = await db.employees.find_one({"id": emp_id}, {"_id": 0})
        if emp:
            links.append({"type": "employee", "label": f"Employee: {emp['full_name']}", "id": emp_id})

    if tx_type == 'leave_request':
        leave_entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": tx['data'].get('leave_type')}, {"_id": 0}
        ).to_list(100)
        links.append({"type": "ledger", "label": f"Leave Ledger ({len(leave_entries)} entries)", "id": emp_id})

    elif tx_type == 'finance_60':
        fin_entries = await db.finance_ledger.find({"employee_id": emp_id}, {"_id": 0}).to_list(100)
        links.append({"type": "ledger", "label": f"Finance Ledger ({len(fin_entries)} entries)", "id": emp_id})

    if emp_id:
        contracts = await db.contracts.find({"employee_id": emp_id}, {"_id": 0}).to_list(10)
        if contracts:
            links.append({"type": "contract", "label": f"Contracts ({len(contracts)})", "id": emp_id})

    links.append({"type": "transaction", "label": f"Transaction: {tx['ref_no']}", "id": tx['id']})
    return links


async def get_before_after(tx):
    tx_type = tx.get('type')
    data = tx.get('data', {})
    emp_id = tx.get('employee_id')

    if tx_type == 'leave_request':
        lt = data.get('leave_type', 'annual')
        entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": lt}, {"_id": 0}
        ).to_list(1000)
        balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in entries)
        wd = data.get('working_days', 0)
        entitlement = 0
        for e in entries:
            if e['type'] == 'credit':
                entitlement += e['days']
        used = entitlement - balance
        return {
            "before": {"total_entitlement": entitlement, "used": used, "remaining": balance},
            "after": {"total_entitlement": entitlement, "used": used + wd, "remaining": balance - wd}
        }

    elif tx_type == 'finance_60':
        return {
            "before": {"description": "Before finance entry"},
            "after": {"amount": data.get('amount', 0), "code": data.get('code_name', '')}
        }

    return {"before": {}, "after": {}}


@router.get("/mirror/{transaction_id}")
async def get_mirror(transaction_id: str, user=Depends(require_roles('stas'))):
    """
    مرآة STAS الشاملة - تعرض جميع البيانات قبل التنفيذ
    """
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")

    # استخدام Service Layer لبناء بيانات المرآة
    mirror_data = await build_mirror_data(tx)
    
    # إضافة بيانات إضافية للتوافقية
    mirror_data["trace_links"] = await get_trace_links(tx)
    
    # للمخالصة - إضافة تفاصيل إضافية
    if tx.get('type') == 'settlement' and tx.get('employee_id'):
        from services.settlement_service import get_settlement_mirror_data
        settlement_data = await get_settlement_mirror_data(tx['employee_id'])
        mirror_data["settlement_details"] = settlement_data
    
    return mirror_data


@router.post("/execute/{transaction_id}")
async def execute_transaction(transaction_id: str, user=Depends(require_roles('stas'))):
    """
    تنفيذ المعاملة - STAS فقط
    يمنع التنفيذ إذا فشل أي فحص (FAIL)
    """
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")

    # منع التنفيذ المكرر - CRITICAL: one-time execution only
    if tx['status'] == 'executed':
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ALREADY_EXECUTED",
                "message_ar": "تم تنفيذ هذه المعاملة مسبقاً - لا يمكن التنفيذ مرة أخرى",
                "message_en": "Transaction already executed - cannot execute again",
                "ref_no": tx['ref_no'],
                "executed_at": tx.get('executed_at')
            }
        )
    
    # حالات إضافية تمنع التنفيذ
    if tx['status'] in ('cancelled', 'rejected'):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_STATUS",
                "message_ar": f"لا يمكن تنفيذ معاملة بحالة {tx['status']}",
                "message_en": f"Cannot execute transaction with status {tx['status']}",
                "status": tx['status']
            }
        )

    # تشغيل الفحوصات المسبقة
    pre_checks = await run_pre_checks(tx)
    
    # فصل الفحوصات الفاشلة والتحذيرات
    failed_checks = [c for c in pre_checks if c['status'] == 'FAIL']
    warning_checks = [c for c in pre_checks if c['status'] == 'WARN']
    
    # منع التنفيذ إذا فشل أي فحص
    if failed_checks:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "EXECUTION_BLOCKED",
                "message_ar": "لا يمكن التنفيذ - توجد شروط فاشلة",
                "message_en": "Cannot execute - failed pre-checks",
                "failed_checks": [{"name": c['name'], "name_ar": c['name_ar'], "detail": c['detail']} for c in failed_checks]
            }
        )

    now = datetime.now(timezone.utc).isoformat()
    tx_type = tx.get('type')
    data = tx.get('data', {})
    emp_id = tx.get('employee_id')

    # تسجيل التحذيرات مع التنفيذ
    execution_warnings = [{"name": c['name'], "name_ar": c['name_ar'], "detail": c['detail']} for c in warning_checks]

    # Execute based on type
    if tx_type == 'leave_request':
        leave_type = data.get('leave_type', 'annual')
        working_days = data.get('working_days', 0)
        
        # تسجيل الإجازة في leave_ledger
        await db.leave_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "type": "debit",
            "leave_type": leave_type,
            "days": working_days,
            "start_date": data.get('start_date'),
            "end_date": data.get('adjusted_end_date') or data.get('end_date'),
            "note": f"Leave: {data.get('start_date')} to {data.get('adjusted_end_date')}",
            "ref_no": tx.get('ref_no'),
            "date": now,
            "created_at": now
        })
        
        # للإجازة المرضية: إشعار سلطان إذا دخل شريحة خصم
        if leave_type == 'sick':
            from services.hr_policy import calculate_sick_leave_consumption
            consumption = await calculate_sick_leave_consumption(emp_id)
            current_used = consumption.get('total_sick_days_used', 0)
            
            # إشعار إذا تجاوز 30 يوم (دخول شريحة 50%) أو 90 يوم (دخول شريحة 0%)
            notification_message = None
            if current_used > 90:
                notification_message = f"⚠️ الموظف {tx.get('employee_name_ar', emp_id)} دخل شريحة الخصم 100% (المادة 117) - استهلك {current_used} يوم من 120 يوم"
            elif current_used > 30:
                notification_message = f"تنبيه: الموظف {tx.get('employee_name_ar', emp_id)} دخل شريحة الخصم 50% (المادة 117) - استهلك {current_used} يوم من 120 يوم"
            
            if notification_message:
                # إنشاء إشعار لسلطان
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "type": "sick_leave_tier_alert",
                    "recipient_role": "sultan",
                    "employee_id": emp_id,
                    "transaction_id": tx['id'],
                    "message_ar": notification_message,
                    "message_en": f"Employee entered sick leave deduction tier - {current_used}/120 days used",
                    "read": False,
                    "created_at": now
                })
        
        # للإجازات الإدارية (وفاة، زواج): تسجيل الرصيد الثابت (5 أيام) كـ credit ثم debit
        # هذا يُظهر للإدارة أن الموظف استخدم 5 أيام من رصيد 5 أيام
        if leave_type in ['bereavement', 'marriage']:
            fixed_days = 5
            # إضافة رصيد (للعرض فقط)
            await db.leave_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": emp_id,
                "transaction_id": tx['id'],
                "type": "credit",
                "leave_type": leave_type,
                "days": fixed_days,
                "note": f"رصيد {leave_type} الثابت",
                "date": now,
                "created_at": now,
                "source": "fixed_entitlement"
            })

    elif tx_type == 'finance_60':
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "code": data.get('code'),
            "code_name": data.get('code_name', ''),
            "amount": data.get('amount', 0),
            "type": data.get('tx_type', 'credit'),
            "category": data.get('category', 'finance_60'),
            "description": data.get('description', ''),
            "date": now,
            "created_at": now
        })

    elif tx_type == 'settlement':
        # استخدام Settlement Service للتنفيذ
        if data.get('snapshot'):
            success, error, result = await execute_settlement(
                transaction_id=tx['id'],
                snapshot=data['snapshot'],
                executor_id=user['user_id']
            )
            if not success:
                raise HTTPException(status_code=400, detail=error)

    elif tx_type == 'add_finance_code':
        await db.finance_codes.insert_one({
            "id": str(uuid.uuid4()),
            "code": data.get('code'),
            "name": data.get('name'),
            "name_ar": data.get('name_ar', ''),
            "category": data.get('category', 'other'),
            "is_active": True,
            "created_at": now
        })

    elif tx_type == 'tangible_custody':
        # Record custody in custody_ledger
        await db.custody_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "item_name": data.get('item_name', ''),
            "item_name_ar": data.get('item_name_ar', ''),
            "serial_number": data.get('serial_number', ''),
            "estimated_value": data.get('estimated_value', 0),
            "description": data.get('description', ''),
            "employee_name": data.get('employee_name', ''),
            "employee_name_ar": data.get('employee_name_ar', ''),
            "status": "active",
            "assigned_at": now,
            "created_at": now
        })

    elif tx_type == 'tangible_custody_return':
        # Remove custody from employee
        custody_id = data.get('custody_id')
        if custody_id:
            await db.custody_ledger.update_one(
                {"id": custody_id},
                {"$set": {"status": "returned", "returned_at": now, "return_transaction_id": tx['id']}}
            )

    # Fetch company branding for PDF
    branding = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    if not branding:
        branding = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_data": None
        }

    # Generate PDF
    emp = await db.employees.find_one({"id": emp_id}, {"_id": 0}) if emp_id else None
    pdf_bytes, pdf_hash, integrity_id = generate_transaction_pdf(tx, emp, 'ar', branding)

    timeline_event = {
        "event": "executed",
        "actor": user['user_id'],
        "actor_name": "STAS",
        "timestamp": now,
        "note": "Transaction executed by STAS",
        "stage": "stas"
    }

    await db.transactions.update_one(
        {"id": transaction_id},
        {
            "$set": {
                "status": "executed",
                "current_stage": "completed",
                "pdf_hash": pdf_hash,
                "integrity_id": integrity_id,
                "executed_at": now,
                "updated_at": now
            },
            "$push": {
                "timeline": timeline_event,
                "approval_chain": {
                    "stage": "stas",
                    "approver_id": user['user_id'],
                    "approver_name": "STAS",
                    "status": "executed",
                    "timestamp": now,
                    "note": "Executed"
                }
            }
        }
    )
    
    # إرسال إشعار للموظف بتنفيذ معاملته
    if emp_id:
        await notify_transaction_executed(tx, emp_id)

    return {
        "message": "Transaction executed successfully",
        "status": "executed",
        "ref_no": tx['ref_no'],
        "pdf_hash": pdf_hash,
        "integrity_id": integrity_id,
        "warnings": execution_warnings if execution_warnings else None
    }


@router.post("/return/{transaction_id}")
async def return_transaction(transaction_id: str, body: ReturnRequest, user=Depends(require_roles('stas'))):
    """
    إرجاع المعاملة للمرحلة السابقة - مرة واحدة فقط
    """
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")
    
    # التحقق من عدم الإرجاع سابقاً
    if tx.get('returned_by_stas'):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "ALREADY_RETURNED",
                "message_ar": "تم إرجاع هذه المعاملة مسبقاً - لا يمكن الإرجاع مرة أخرى",
                "message_en": "Transaction already returned - cannot return again"
            }
        )
    
    if tx['status'] == 'executed':
        raise HTTPException(status_code=400, detail="لا يمكن إرجاع معاملة منفذة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديد المرحلة السابقة من workflow
    workflow = tx.get('workflow', ['supervisor', 'ops', 'stas'])
    current_idx = workflow.index('stas') if 'stas' in workflow else len(workflow) - 1
    previous_stage = workflow[current_idx - 1] if current_idx > 0 else workflow[0]
    
    # تحديث المعاملة
    await db.transactions.update_one(
        {"id": transaction_id},
        {
            "$set": {
                "current_stage": previous_stage,
                "status": f"pending_{previous_stage}",
                "returned_by_stas": True,  # يمنع الإرجاع مرة أخرى
                "return_count": 1,
                "returned_at": now,
                "updated_at": now
            },
            "$push": {
                "timeline": {
                    "event": "returned_by_stas",
                    "actor": user['user_id'],
                    "actor_name": "STAS",
                    "timestamp": now,
                    "note": body.note or "تم الإرجاع بواسطة STAS",
                    "stage": "stas",
                    "returned_to": previous_stage
                }
            }
        }
    )
    
    return {
        "message": "تم إرجاع المعاملة بنجاح",
        "message_en": "Transaction returned successfully",
        "returned_to": previous_stage,
        "note": body.note
    }


@router.get("/pending")
async def get_pending_executions(user=Depends(require_roles('stas'))):
    # Get transactions that are ready for STAS action
    # This includes: current_stage=stas OR status=pending_stas
    txs = await db.transactions.find(
        {
            "$or": [
                {"current_stage": "stas", "status": {"$nin": ["executed", "rejected", "cancelled"]}},
                {"status": "pending_stas"}
            ]
        }, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return txs



# ==================== HOLIDAY MANAGEMENT ====================

@router.get("/holidays")
async def get_manual_holidays(user=Depends(require_roles('stas'))):
    """Get all manual holidays added by STAS"""
    holidays = await db.holidays.find({}, {"_id": 0}).sort("date", 1).to_list(500)
    return holidays


@router.post("/holidays")
async def add_holiday(req: HolidayCreate, user=Depends(require_roles('stas'))):
    """Add a manual holiday"""
    existing = await db.holidays.find_one({"date": req.date})
    if existing:
        raise HTTPException(status_code=400, detail="العطلة موجودة مسبقاً لهذا التاريخ")
    
    holiday = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "name_ar": req.name_ar,
        "date": req.date,
        "year": int(req.date[:4]),
        "created_by": user['user_id'],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.holidays.insert_one(holiday)
    holiday.pop('_id', None)
    return holiday


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(holiday_id: str, user=Depends(require_roles('stas'))):
    """Delete a manual holiday"""
    result = await db.holidays.delete_one({"id": holiday_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holiday not found")
    return {"message": "Holiday deleted"}


# ==================== MAINTENANCE TOOLS ====================

PROTECTED_USERNAMES = ['stas', 'mohammed', 'sultan', 'naif', 'salah']


@router.post("/maintenance/purge-transactions")
async def purge_transactions(req: PurgeRequest, user=Depends(require_roles('stas'))):
    """Purge all transactions (STAS only). Requires confirm=true."""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to purge")
    
    # Delete all transactions
    tx_result = await db.transactions.delete_many({})
    # Reset transaction counter
    await db.counters.update_one({"id": "transaction_ref"}, {"$set": {"seq": 0}})
    # Clear ledgers
    leave_result = await db.leave_ledger.delete_many({"transaction_id": {"$ne": None}})
    finance_result = await db.finance_ledger.delete_many({})
    
    return {
        "message": "Transactions purged",
        "deleted": {
            "transactions": tx_result.deleted_count,
            "leave_ledger_entries": leave_result.deleted_count,
            "finance_ledger_entries": finance_result.deleted_count
        }
    }


@router.post("/maintenance/purge-users")
async def purge_users(req: PurgeRequest, user=Depends(require_roles('stas'))):
    """Purge non-admin users (STAS only). Preserves STAS, CEO, ops, finance roles."""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to purge")
    
    # Delete non-protected users
    user_result = await db.users.delete_many({"username": {"$nin": PROTECTED_USERNAMES}})
    emp_result = await db.employees.delete_many({"user_id": {"$nin": [
        u['user_id'] for u in await db.users.find({"username": {"$in": PROTECTED_USERNAMES}}, {"user_id": 1, "_id": 0}).to_list(10)
    ]}})
    
    return {
        "message": "Non-admin users purged",
        "deleted": {
            "users": user_result.deleted_count,
            "employees": emp_result.deleted_count
        }
    }


@router.post("/users/{user_id}/archive")
async def archive_user(user_id: str, user=Depends(require_roles('stas'))):
    """Archive (disable) a user. Archived users won't appear in user switcher."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target['username'] in PROTECTED_USERNAMES:
        raise HTTPException(status_code=403, detail="Cannot archive protected admin users")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": False, "is_archived": True, "archived_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": f"User {target['username']} archived"}


@router.post("/users/{user_id}/restore")
async def restore_user(user_id: str, user=Depends(require_roles('stas'))):
    """Restore an archived user"""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"is_active": True, "is_archived": False}, "$unset": {"archived_at": ""}}
    )
    return {"message": f"User {target['username']} restored"}


@router.get("/users/archived")
async def get_archived_users(user=Depends(require_roles('stas'))):
    """Get list of archived users"""
    users = await db.users.find({"is_archived": True}, {"_id": 0, "password_hash": 0}).to_list(100)
    return users


# ==================== RAMADAN MODE ====================

@router.get("/ramadan")
async def get_ramadan_mode(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """جلب إعدادات دوام رمضان"""
    settings = await get_ramadan_settings()
    if not settings:
        return {
            "is_active": False,
            "hours_per_day": 8,
            "message_ar": "الدوام العادي (8 ساعات)"
        }
    return settings


@router.post("/ramadan/activate")
async def activate_ramadan_mode(req: RamadanModeRequest, user=Depends(require_roles('stas'))):
    """تفعيل دوام رمضان - STAS فقط"""
    settings = await set_ramadan_mode(
        start_date=req.start_date,
        end_date=req.end_date,
        actor_id=user['user_id'],
        work_start=req.work_start,
        work_end=req.work_end
    )
    
    # تحديث أوقات جميع مواقع العمل تلقائياً
    now = datetime.now(timezone.utc).isoformat()
    await db.work_locations.update_many(
        {},
        {"$set": {
            "ramadan_hours_active": True,
            "original_work_start": {"$ifNull": ["$work_start", "08:00"]},
            "original_work_end": {"$ifNull": ["$work_end", "17:00"]},
            "work_start": req.work_start,
            "work_end": req.work_end,
            "ramadan_updated_at": now
        }}
    )
    
    # حفظ الأوقات الأصلية إذا لم تكن محفوظة
    locations = await db.work_locations.find({}, {"_id": 0}).to_list(100)
    for loc in locations:
        if not loc.get('original_work_start_saved'):
            await db.work_locations.update_one(
                {"id": loc['id']},
                {"$set": {
                    "original_work_start_saved": loc.get('work_start', '08:00'),
                    "original_work_end_saved": loc.get('work_end', '17:00'),
                    "work_start": req.work_start,
                    "work_end": req.work_end,
                    "ramadan_hours_active": True
                }}
            )
    
    return {
        "message": "تم تفعيل دوام رمضان بنجاح",
        "message_en": "Ramadan mode activated",
        "settings": settings,
        "work_locations_updated": True,
        "note_ar": f"تم تحديث أوقات جميع مواقع العمل إلى {req.work_start} - {req.work_end}"
    }


@router.post("/ramadan/deactivate")
async def deactivate_ramadan(user=Depends(require_roles('stas'))):
    """إلغاء تفعيل دوام رمضان"""
    settings = await deactivate_ramadan_mode(user['user_id'])
    
    # استعادة أوقات مواقع العمل الأصلية
    locations = await db.work_locations.find({}, {"_id": 0}).to_list(100)
    for loc in locations:
        if loc.get('original_work_start_saved'):
            await db.work_locations.update_one(
                {"id": loc['id']},
                {"$set": {
                    "work_start": loc.get('original_work_start_saved', '08:00'),
                    "work_end": loc.get('original_work_end_saved', '17:00'),
                    "ramadan_hours_active": False
                },
                "$unset": {
                    "original_work_start_saved": "",
                    "original_work_end_saved": ""
                }}
            )
    
    return {
        "message": "تم إلغاء دوام رمضان",
        "message_en": "Ramadan mode deactivated",
        "settings": settings,
        "work_locations_restored": True,
        "note_ar": "تم استعادة أوقات العمل الأصلية لجميع المواقع"
    }


# ==================== ATTENDANCE DAILY JOB ====================

@router.post("/attendance/calculate-daily")
async def run_daily_attendance_calculation(user=Depends(require_roles('stas'))):
    """
    تشغيل حساب الحضور اليومي يدوياً
    يُسجل الغياب لمن لم يسجل دخول ولا عنده إجازة
    """
    result = await calculate_daily_attendance()
    return {
        "message": "تم حساب الحضور اليومي",
        "result": result
    }


@router.post("/attendance/calculate-for-date")
async def run_attendance_for_date(date: str, user=Depends(require_roles('stas'))):
    """تشغيل حساب الحضور لتاريخ محدد"""
    result = await calculate_daily_attendance(date)
    return {
        "message": f"تم حساب الحضور لتاريخ {date}",
        "result": result
    }


# ==================== MAP VISIBILITY SETTING ====================

@router.get("/settings/map-visibility")
async def get_map_visibility(user=Depends(require_roles('stas'))):
    """جلب إعداد إظهار الخريطة للموظفين - للمدراء فقط"""
    setting = await db.settings.find_one({"type": "map_visibility"}, {"_id": 0})
    if not setting:
        return {"show_map_to_employees": False}
    return setting


@router.get("/settings/map-visibility/public")
async def get_map_visibility_public(user=Depends(get_current_user)):
    """جلب إعداد إظهار الخريطة - للجميع"""
    setting = await db.settings.find_one({"type": "map_visibility"}, {"_id": 0})
    if not setting:
        return {"show_map_to_employees": False}
    return {"show_map_to_employees": setting.get('show_map_to_employees', False)}


@router.post("/settings/map-visibility")
async def set_map_visibility(show: bool, user=Depends(require_roles('stas'))):
    """تحديث إعداد إظهار الخريطة للموظفين"""
    now = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one(
        {"type": "map_visibility"},
        {"$set": {
            "type": "map_visibility",
            "show_map_to_employees": show,
            "updated_by": user['user_id'],
            "updated_at": now
        }},
        upsert=True
    )
    return {
        "message": "تم تحديث إعداد الخريطة",
        "show_map_to_employees": show
    }
