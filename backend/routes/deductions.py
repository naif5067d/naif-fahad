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
    action: str  # approve | reject
    note: Optional[str] = ""


# ============================================================
# STATUS CONSTANTS
# ============================================================

DEDUCTION_STATUS = {
    "pending_stas": "بانتظار STAS",
    "executed": "منفذ",
    "rejected": "مرفوض"
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
async def get_pending_deductions(user=Depends(require_roles('stas'))):
    """Get deductions/bonuses pending STAS execution"""
    items = await db.deductions_bonuses.find(
        {"status": "pending_stas"}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
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
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Create a new deduction or bonus
    Sultan/Naif: creates, goes to STAS
    STAS: can create and execute directly
    """
    # التحقق من وجود الموظف
    employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من عدم وجود معاملة pending للموظف
    pending = await db.deductions_bonuses.find_one({
        "employee_id": req.employee_id,
        "status": "pending_stas"
    })
    if pending:
        raise HTTPException(
            status_code=400, 
            detail="يوجد طلب خصم/مكافأة قيد المعالجة لهذا الموظف. يجب انتظار التنفيذ أولاً."
        )
    
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
        "status": "pending_stas",
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name_ar") or user.get("full_name"),
        "created_at": now,
        "executed_by": None,
        "executed_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "rejection_note": None
    }
    
    # إذا كان STAS يمكنه التنفيذ مباشرة
    if user.get("role") == "stas":
        item["status"] = "executed"
        item["executed_by"] = user["user_id"]
        item["executed_at"] = now
        
        # إضافة للسجل المالي
        await add_to_finance_ledger(item, user)
    
    await db.deductions_bonuses.insert_one(item)
    item.pop("_id", None)
    
    return item


# ============================================================
# EXECUTE/REJECT DEDUCTION/BONUS (STAS ONLY)
# ============================================================

@router.post("/{item_id}/action")
async def execute_deduction_bonus(
    item_id: str,
    req: DeductionBonusAction,
    user=Depends(require_roles('stas'))
):
    """
    Execute or reject a deduction/bonus
    STAS exclusive operation
    """
    item = await db.deductions_bonuses.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    
    if item["status"] != "pending_stas":
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

async def add_to_finance_ledger(item: dict, executor: dict):
    """Add executed deduction/bonus to finance_ledger"""
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
        "settled": False,  # سيتم تسويتها في المخالصة
        "date": now,
        "created_at": now,
        "created_by": executor["user_id"]
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
