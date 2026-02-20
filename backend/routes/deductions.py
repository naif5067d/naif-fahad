"""
Deductions & Bonuses Routes - نظام الخصومات والمكافآت
============================================================
- sultan يُنشئ الخصم/المكافأة
- STAS يُنفذ
- بعد التنفيذ يدخل في السجل المالي ويظهر في المخالصة
- إذا كان هناك معاملة pending لا يمكن إضافة خصم جديد
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/deductions", tags=["deductions"])


# ============================================================
# MODELS
# ============================================================

class DeductionBonusCreate(BaseModel):
    employee_id: str
    type: str  # deduction | bonus
    amount: float
    reason: str
    month: str  # YYYY-MM
    note: Optional[str] = ""


class DeductionBonusAction(BaseModel):
    action: str  # approve | reject | defer_to_settlement
    note: Optional[str] = ""
    defer_to_settlement: bool = False  # ترحيل للمخالصة


class MohammedDecision(BaseModel):
    """قرار محمد على العقوبة"""
    decision: str  # execute_from_salary | defer_to_settlement | reject
    note: Optional[str] = ""


# ============================================================
# STATUS CONSTANTS - التسلسل الإداري الجديد
# ============================================================

DEDUCTION_STATUS = {
    "pending_sultan": "بانتظار سلطان",
    "pending_mohammed": "بانتظار موافقة محمد",
    "approved_for_salary": "معتمد للخصم من الراتب",
    "deferred_to_settlement": "مؤجل للمخالصة",
    "executed": "منفذ",
    "rejected": "مرفوض"
}

DEDUCTION_STATUS_EN = {
    "pending_sultan": "Pending Sultan",
    "pending_mohammed": "Pending Mohammed's Approval",
    "approved_for_salary": "Approved - Deduct from Salary",
    "deferred_to_settlement": "Deferred to Settlement",
    "executed": "Executed",
    "rejected": "Rejected"
}


# ============================================================
# LIST DEDUCTIONS/BONUSES
# ============================================================

@router.get("")
async def list_deductions(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    type: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    List all deductions/bonuses
    - sultan/naif: can see all
    - stas: can see all + execute
    - employee: can see own only
    """
    role = user.get("role")
    query = {}
    
    if role == "employee":
        emp = await db.employees.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if emp:
            query["employee_id"] = emp["id"]
    
    if status:
        query["status"] = status
    if employee_id and role != "employee":
        query["employee_id"] = employee_id
    if type:
        query["type"] = type
    
    items = await db.deductions_bonuses.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/pending")
async def get_pending_deductions(user=Depends(require_roles('stas', 'mohammed'))):
    """Get deductions/bonuses pending approval"""
    items = await db.deductions_bonuses.find(
        {"status": {"$in": ["pending_mohammed", "approved_for_salary", "deferred_to_settlement"]}}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return items


@router.get("/pending-mohammed")
async def get_pending_for_mohammed(
    user=Depends(require_roles('mohammed', 'stas'))
):
    """جلب العقوبات المعلقة بانتظار قرار محمد"""
    items = await db.deductions_bonuses.find(
        {"status": "pending_mohammed"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return items


# ============================================================
# GET SINGLE ITEM
# ============================================================

@router.get("/{item_id}")
async def get_deduction(item_id: str, user=Depends(get_current_user)):
    """Get a single deduction/bonus by ID"""
    item = await db.deductions_bonuses.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    return item


# ============================================================
# CREATE DEDUCTION/BONUS
# ============================================================

@router.post("")
async def create_deduction_bonus(
    req: DeductionBonusCreate,
    user=Depends(require_roles('sultan', 'naif', 'mohammed'))
):
    """
    Create a new deduction or bonus
    ❌ المشرف لا يستطيع إنشاء عقوبات
    
    التسلسل الإداري:
    1. سلطان/نايف يُنشئ → الحالة: pending_mohammed
    2. محمد يقرر (خصم من الراتب / ترحيل للمخالصة / رفض)
    3. STAS ينفذ القرار
    """
    # التحقق من وجود الموظف
    employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من نوع العملية
    if req.type not in ["deduction", "bonus"]:
        raise HTTPException(status_code=400, detail="نوع العملية غير صحيح. يجب أن يكون deduction أو bonus")
    
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="المبلغ يجب أن يكون أكبر من صفر")
    
    now = datetime.now(timezone.utc).isoformat()
    
    item = {
        "id": str(uuid.uuid4()),
        "employee_id": req.employee_id,
        "employee_name": employee.get("full_name_ar") or employee.get("full_name"),
        "employee_code": employee.get("employee_number"),
        "type": req.type,
        "amount": req.amount,
        "reason": req.reason,
        "month": req.month,
        "note": req.note,
        "status": "pending_mohammed",  # ينتظر قرار محمد
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name_ar") or user.get("full_name"),
        "created_at": now,
        # قرار محمد
        "mohammed_decision": None,
        "mohammed_decision_note": None,
        "mohammed_decided_at": None,
        "mohammed_decided_by": None,
        # التنفيذ
        "executed_by": None,
        "executed_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "rejection_note": None,
        # للمخالصة
        "deferred_to_settlement": False,
        "settled_in_settlement_id": None
    }
    
    await db.deductions_bonuses.insert_one(item)
    item.pop("_id", None)
    
    # إرسال إشعار لمحمد
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        await create_notification(
            recipient_id="",
            notification_type=NotificationType.ACTION_REQUIRED,
            title="Deduction Pending Your Approval",
            title_ar="عقوبة بانتظار موافقتك",
            message=f"Deduction for {employee.get('full_name_ar', '')}: {req.amount} SAR",
            message_ar=f"عقوبة على {employee.get('full_name_ar', '')}: {req.amount} ر.س - {req.reason}",
            priority=NotificationPriority.CRITICAL,
            recipient_role="mohammed",
            reference_type="deduction",
            reference_id=item["id"]
        )
    except:
        pass
    
    return item


# ============================================================
# MOHAMMED'S DECISION - قرار محمد (إلزامي)
# ============================================================

class MohammedDecision(BaseModel):
    """قرار محمد على العقوبة"""
    decision: str  # execute_from_salary | defer_to_settlement | reject
    note: Optional[str] = ""


@router.post("/{item_id}/mohammed-decision")
async def mohammed_decision(
    item_id: str,
    req: MohammedDecision,
    user=Depends(require_roles('mohammed'))
):
    """
    قرار محمد على العقوبة - إلزامي قبل التنفيذ
    
    القرارات:
    - execute_from_salary: خصم من الراتب فوراً (لا تدخل المخالصة)
    - defer_to_settlement: ترحيل للمخالصة (لا تُخصم من الراتب)
    - reject: رفض العقوبة
    """
    if req.decision not in ['execute_from_salary', 'defer_to_settlement', 'reject']:
        raise HTTPException(status_code=400, detail="القرار غير صحيح")
    
    item = await db.deductions_bonuses.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    
    if item["status"] != "pending_mohammed":
        raise HTTPException(status_code=400, detail="هذا السجل تم اتخاذ قرار عليه مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if req.decision == 'execute_from_salary':
        # موافقة - خصم من الراتب
        new_status = "executed"
        
        await db.deductions_bonuses.update_one(
            {"id": item_id},
            {"$set": {
                "status": new_status,
                "mohammed_decision": "execute_from_salary",
                "mohammed_decision_note": req.note,
                "mohammed_decided_at": now,
                "mohammed_decided_by": user["user_id"],
                "deferred_to_settlement": False,
                "executed_by": user["user_id"],
                "executed_at": now
            }}
        )
        
        # إضافة للسجل المالي (خصم من الراتب)
        item["deferred_to_settlement"] = False
        await add_to_finance_ledger(item, user, deferred=False)
        
        message_ar = "تم اعتماد الخصم من الراتب وتنفيذه"
        message_en = "Deduction approved and executed from salary"
        
    elif req.decision == 'defer_to_settlement':
        # ترحيل للمخالصة
        new_status = "deferred_to_settlement"
        
        await db.deductions_bonuses.update_one(
            {"id": item_id},
            {"$set": {
                "status": new_status,
                "mohammed_decision": "defer_to_settlement",
                "mohammed_decision_note": req.note,
                "mohammed_decided_at": now,
                "mohammed_decided_by": user["user_id"],
                "deferred_to_settlement": True
            }}
        )
        
        # إضافة للسجل المالي (مؤجل للمخالصة)
        item["deferred_to_settlement"] = True
        await add_to_finance_ledger(item, user, deferred=True)
        
        message_ar = "تم ترحيل الخصم للمخالصة"
        message_en = "Deduction deferred to settlement"
        
    else:  # reject
        new_status = "rejected"
        await db.deductions_bonuses.update_one(
            {"id": item_id},
            {"$set": {
                "status": "rejected",
                "mohammed_decision": "reject",
                "mohammed_decision_note": req.note,
                "mohammed_decided_at": now,
                "mohammed_decided_by": user["user_id"],
                "rejected_by": user["user_id"],
                "rejected_at": now,
                "rejection_note": req.note
            }}
        )
        message_ar = "تم رفض العقوبة"
        message_en = "Deduction rejected"
    
    # إرسال إشعار للموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        decision_text = {
            'execute_from_salary': 'تم خصمها من راتبك',
            'defer_to_settlement': 'ستُخصم عند المخالصة',
            'reject': 'تم رفضها'
        }
        
        await create_notification(
            recipient_id=item["employee_id"],
            notification_type=NotificationType.ALERT if req.decision != 'reject' else NotificationType.INFO,
            title="Deduction Decision",
            title_ar="قرار بشأن العقوبة",
            message=f"Deduction of {item['amount']} SAR: {req.decision}",
            message_ar=f"عقوبة {item['amount']} ر.س: {decision_text.get(req.decision, req.decision)}",
            priority=NotificationPriority.HIGH,
            recipient_role="employee"
        )
    except:
        pass
    
    # حفظ في أرشيف STAS
    archive_entry = {
        "id": str(uuid.uuid4()),
        "year": item["month"][:4],
        "type": "deduction_decision",
        "deduction_id": item_id,
        "employee_id": item["employee_id"],
        "employee_name_ar": item.get("employee_name", ""),
        "amount": item["amount"],
        "reason": item["reason"],
        "decision": req.decision,
        "decision_note": req.note,
        "decided_by": user["user_id"],
        "decided_by_name": user.get("full_name_ar", ""),
        "decided_at": now,
        "archived_at": now
    }
    await db.stas_annual_archive.insert_one(archive_entry)
    
    return {
        "success": True,
        "message_ar": message_ar,
        "message_en": message_en,
        "decision": req.decision,
        "status": new_status
    }


# ============================================================
# EXECUTE/REJECT DEDUCTION/BONUS (STAS ONLY - Legacy)
# ============================================================

@router.post("/{item_id}/action")
async def execute_deduction_bonus(
    item_id: str,
    req: DeductionBonusAction,
    user=Depends(require_roles('stas'))
):
    """
    Legacy: Execute or reject a deduction/bonus
    يجب موافقة محمد أولاً
    """
    item = await db.deductions_bonuses.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    
    if item["status"] == "pending_mohammed":
        raise HTTPException(status_code=400, detail="يجب موافقة محمد أولاً قبل التنفيذ")
    
    if item["status"] not in ["approved_for_salary", "deferred_to_settlement"]:
        raise HTTPException(status_code=400, detail="هذا السجل تم معالجته مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    if req.action == "approve":
        # تنفيذ
        await db.deductions_bonuses.update_one(
            {"id": item_id},
            {"$set": {
                "status": "executed",
                "executed_by": user["user_id"],
                "executed_at": now
            }}
        )
        
        # إضافة للسجل المالي
        item["status"] = "executed"
        await add_to_finance_ledger(item, user)
        
        return {"message": "تم تنفيذ العملية", "status": "executed"}
    
    elif req.action == "reject":
        # رفض
        await db.deductions_bonuses.update_one(
            {"id": item_id},
            {"$set": {
                "status": "rejected",
                "rejected_by": user["user_id"],
                "rejected_at": now,
                "rejection_note": req.note
            }}
        )
        
        return {"message": "تم رفض العملية", "status": "rejected"}
    
    else:
        raise HTTPException(status_code=400, detail="الإجراء غير صحيح. يجب أن يكون approve أو reject")


# ============================================================
# DELETE DEDUCTION/BONUS (PENDING ONLY)
# ============================================================

@router.delete("/{item_id}")
async def delete_deduction_bonus(
    item_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """Delete a pending deduction/bonus"""
    item = await db.deductions_bonuses.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    
    if item["status"] != "pending_stas":
        raise HTTPException(status_code=400, detail="لا يمكن حذف سجل تم تنفيذه أو رفضه")
    
    await db.deductions_bonuses.delete_one({"id": item_id})
    return {"message": "تم حذف السجل"}


# ============================================================
# HELPER: ADD TO FINANCE LEDGER
# ============================================================

async def add_to_finance_ledger(item: dict, executor: dict, deferred: bool = False):
    """
    Add executed deduction/bonus to finance_ledger
    
    Args:
        item: Deduction/bonus item
        executor: User who executed the action
        deferred: True if deferred to settlement, False if deducted from salary
    """
    now = datetime.now(timezone.utc).isoformat()
    
    ledger_entry = {
        "id": str(uuid.uuid4()),
        "employee_id": item["employee_id"],
        "type": "debit" if item["type"] == "deduction" else "credit",
        "category": "deduction" if item["type"] == "deduction" else "bonus",
        "amount": item["amount"],
        "description": f"{'خصم' if item['type'] == 'deduction' else 'مكافأة'}: {item['reason']}",
        "description_en": f"{'Deduction' if item['type'] == 'deduction' else 'Bonus'}: {item['reason']}",
        "reference_id": item["id"],
        "month": item["month"],
        # إذا تم خصمها من الراتب = مسوّية، إذا مؤجلة = غير مسوّية (تدخل المخالصة)
        "settled": not deferred,  
        "deferred_to_settlement": deferred,
        "deducted_from_salary": not deferred,
        "date": now,
        "created_at": now,
        "created_by": executor["user_id"],
        "approved_by_mohammed": True  # تم اعتماده من محمد
    }
    
    await db.finance_ledger.insert_one(ledger_entry)


# ============================================================
# GET EMPLOYEE'S UNSETTLED DEDUCTIONS/BONUSES
# ============================================================

@router.get("/employee/{employee_id}/unsettled")
async def get_employee_unsettled(
    employee_id: str,
    user=Depends(get_current_user)
):
    """Get all unsettled deductions/bonuses for an employee (for settlement)"""
    # من finance_ledger
    items = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": {"$in": ["deduction", "bonus"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    deductions = [i for i in items if i["type"] == "debit"]
    bonuses = [i for i in items if i["type"] == "credit"]
    
    total_deductions = sum(i["amount"] for i in deductions)
    total_bonuses = sum(i["amount"] for i in bonuses)
    
    return {
        "deductions": deductions,
        "bonuses": bonuses,
        "total_deductions": total_deductions,
        "total_bonuses": total_bonuses,
        "net": total_bonuses - total_deductions
    }



# ============================================================
# CHECK DEDUCTION LIMIT (50%)
# ============================================================

@router.get("/employee/{employee_id}/deduction-limit")
async def check_employee_deduction_limit(
    employee_id: str,
    month: str,
    proposed_amount: float = 0,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    التحقق من حد الخصم (50% من الراتب)
    
    نظام العمل السعودي: لا يجوز خصم أكثر من 50% من راتب الموظف
    """
    from services.deduction_service import check_deduction_limit, get_employee_salary, get_month_deductions
    
    salary = await get_employee_salary(employee_id)
    current_deductions = await get_month_deductions(employee_id, month)
    max_allowed = salary * 0.5
    remaining = max_allowed - current_deductions
    
    can_deduct = True
    warning = ""
    if proposed_amount > 0:
        can_deduct, _, warning = await check_deduction_limit(employee_id, month, proposed_amount)
    
    return {
        "employee_id": employee_id,
        "month": month,
        "salary": salary,
        "max_allowed_deduction": max_allowed,
        "max_percentage": 50,
        "current_deductions": current_deductions,
        "remaining_allowed": max(0, remaining),
        "proposed_amount": proposed_amount,
        "can_deduct": can_deduct,
        "warning": warning
    }
