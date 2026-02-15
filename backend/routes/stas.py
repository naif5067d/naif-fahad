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
        raise HTTPException(status_code=404, detail="Transaction not found")

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
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx['status'] == 'executed':
        return {"message": "Already executed (idempotent)", "status": "executed", "ref_no": tx['ref_no']}

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
        await db.leave_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "type": "debit",
            "leave_type": data.get('leave_type', 'annual'),
            "days": data.get('working_days', 0),
            "note": f"Leave: {data.get('start_date')} to {data.get('adjusted_end_date')}",
            "date": now,
            "created_at": now
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

    return {
        "message": "Transaction executed successfully",
        "status": "executed",
        "ref_no": tx['ref_no'],
        "pdf_hash": pdf_hash,
        "integrity_id": integrity_id
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
        raise HTTPException(status_code=400, detail="Holiday already exists for this date")
    
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
