"""
Settlement Routes - واجهات برمجة المخالصة
============================================================
المخالصة تُبنى من بيانات العقد الحالية:
1. اختيار الموظف
2. اختيار نوع المخالصة (إنهاء عقد، استقالة، إنهاء خلال التجربة، اتفاق طرفين)
3. النظام يجلب تلقائياً من العقد:
   - آخر راتب شامل جميع البدلات الثابتة
   - سياسة الإجازة 21 أو 30
   - تاريخ بداية الخدمة
   - تاريخ آخر يوم عمل
   - البدلات
4. إنشاء Preview قابل للتعديل الإداري (سلطان + STAS)
5. STAS يُنفذ مرة واحدة فقط
6. بعد التنفيذ: يُقفل الحساب
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from services.settlement_service import (
    validate_settlement_request,
    aggregate_settlement_data,
    execute_settlement,
    get_settlement_mirror_data
)
from services.service_calculator import (
    calculate_service_years,
    calculate_monthly_wage,
    calculate_eos
)
from services.leave_service import get_leave_balance
from services.hr_policy import calculate_pro_rata_entitlement
from datetime import datetime, timezone
import uuid
import io

router = APIRouter(prefix="/api/settlement", tags=["settlement"])


# ============================================================
# MODELS
# ============================================================

class SettlementCreate(BaseModel):
    employee_id: str
    termination_type: str  # contract_expiry | resignation | probation_termination | mutual_agreement
    last_working_day: str  # YYYY-MM-DD
    note: Optional[str] = ""


class SettlementExecute(BaseModel):
    note: Optional[str] = ""


class SettlementAdjustment(BaseModel):
    """تعديل إداري على قيم المخالصة"""
    adjustment_type: str  # add_deduction | add_bonus | adjust_leave | adjust_eos
    amount: float
    reason: str


# ============================================================
# TERMINATION TYPES
# ============================================================

TERMINATION_TYPES = {
    "contract_expiry": {
        "label_ar": "انتهاء العقد",
        "label_en": "Contract Expiry",
        "eos_percentage": 100
    },
    "resignation": {
        "label_ar": "استقالة",
        "label_en": "Resignation",
        "eos_percentage": "variable"  # حسب سنوات الخدمة
    },
    "probation_termination": {
        "label_ar": "إنهاء خلال فترة التجربة",
        "label_en": "Probation Termination",
        "eos_percentage": 0
    },
    "mutual_agreement": {
        "label_ar": "اتفاق طرفين",
        "label_en": "Mutual Agreement",
        "eos_percentage": 100
    },
    "termination": {
        "label_ar": "إنهاء من الشركة",
        "label_en": "Termination by Company",
        "eos_percentage": 100
    }
}


# ============================================================
# GET TERMINATION TYPES
# ============================================================

@router.get("/termination-types")
async def get_termination_types(user=Depends(get_current_user)):
    """Get list of termination types"""
    return TERMINATION_TYPES


# ============================================================
# LIST SETTLEMENTS
# ============================================================

@router.get("")
async def list_settlements(
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """List all settlements"""
    query = {}
    if status:
        query["status"] = status
    
    settlements = await db.settlements.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return settlements


@router.get("/pending")
async def get_pending_settlements(user=Depends(require_roles('stas'))):
    """Get settlements pending STAS execution"""
    settlements = await db.settlements.find(
        {"status": "pending_stas"}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return settlements


# ============================================================
# GET SINGLE SETTLEMENT
# ============================================================

@router.get("/{settlement_id}")
async def get_settlement(settlement_id: str, user=Depends(get_current_user)):
    """Get a single settlement by ID"""
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="المخالصة غير موجودة")
    return settlement


# ============================================================
# PREVIEW SETTLEMENT (CALCULATE WITHOUT SAVING)
# ============================================================

@router.post("/preview")
async def preview_settlement(
    req: SettlementCreate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Preview settlement calculation without saving.
    Returns all calculations for review before creating the settlement.
    """
    # جلب العقد النشط أو المنتهي
    contract = await db.contracts_v2.find_one({
        "employee_id": req.employee_id,
        "status": {"$in": ["active", "terminated"]}
    }, {"_id": 0})
    
    if not contract:
        raise HTTPException(status_code=404, detail="لا يوجد عقد نشط أو منتهي لهذا الموظف")
    
    # جلب بيانات الموظف
    employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # حساب مدة الخدمة
    service = calculate_service_years(contract["start_date"], req.last_working_day)
    
    # حساب الأجر الشامل (Last Wage)
    wages = calculate_monthly_wage(contract)
    
    # حساب مكافأة نهاية الخدمة
    termination_reason = req.termination_type
    if req.termination_type == "probation_termination":
        termination_reason = "termination"  # لا مكافأة خلال التجربة
    
    eos = calculate_eos(
        service_years=service["years"],
        monthly_wage=wages["last_wage"],  # استخدام الراتب الشامل
        termination_reason=termination_reason
    )
    
    # فترة التجربة - لا مكافأة
    if req.termination_type == "probation_termination":
        eos["final_amount"] = 0
        eos["percentage"] = 0
        eos["percentage_reason"] = "إنهاء خلال فترة التجربة - لا استحقاق"
    
    # حساب رصيد الإجازات (Pro-Rata)
    annual_policy = contract.get("annual_policy_days") or contract.get("annual_leave_days") or 21
    leave_data = await calculate_pro_rata_entitlement(
        employee_id=req.employee_id,
        start_date=contract["start_date"],
        end_date=req.last_working_day,
        annual_policy_days=annual_policy
    )
    leave_balance = leave_data.get("available_balance", 0)
    leave_compensation = round(leave_balance * wages["daily_wage"], 2)
    
    # جلب الخصومات غير المسواة
    deductions_data = await get_unsettled_deductions(req.employee_id)
    
    # جلب البونص غير المسوى
    bonuses_data = await get_unsettled_bonuses(req.employee_id)
    
    # جلب السلف غير المسددة
    loans_data = await get_unsettled_loans(req.employee_id)
    
    # حساب المجاميع
    total_entitlements = eos["final_amount"] + leave_compensation + bonuses_data["total"]
    total_deductions = deductions_data["total"] + loans_data["total"]
    net_amount = total_entitlements - total_deductions
    
    return {
        "preview": True,
        "employee": {
            "id": employee["id"],
            "name_ar": employee.get("full_name_ar") or employee.get("full_name"),
            "name_en": employee.get("full_name"),
            "employee_number": employee.get("employee_number"),
            "national_id": employee.get("national_id")
        },
        "contract": {
            "id": contract["id"],
            "serial": contract["contract_serial"],
            "start_date": contract["start_date"],
            "termination_type": req.termination_type,
            "termination_type_label": TERMINATION_TYPES[req.termination_type]["label_ar"],
            "last_working_day": req.last_working_day,
            "bank_name": contract.get("bank_name", ""),
            "bank_iban": contract.get("bank_iban", "")
        },
        "service": service,
        "wages": {
            "basic": wages["basic"],
            "housing": wages["housing"],
            "transport": wages["transport"],
            "nature_of_work": wages["nature_of_work"],
            "other": wages["other"],
            "last_wage": wages["last_wage"],
            "daily_wage": wages["daily_wage"],
            "formula": f"{wages['basic']:,.2f} + {wages['housing']:,.2f} + {wages['transport']:,.2f} + {wages['nature_of_work']:,.2f} + {wages['other']:,.2f} = {wages['last_wage']:,.2f}"
        },
        "eos": eos,
        "leave": {
            "policy_days": annual_policy,
            "balance": round(leave_balance, 2),
            "daily_wage": wages["daily_wage"],
            "compensation": leave_compensation,
            "formula": f"{leave_balance:.2f} يوم × {wages['daily_wage']:,.2f} = {leave_compensation:,.2f}"
        },
        "bonuses": bonuses_data,
        "deductions": deductions_data,
        "loans": loans_data,
        "totals": {
            "entitlements": {
                "eos": eos["final_amount"],
                "leave_compensation": leave_compensation,
                "bonuses": bonuses_data["total"],
                "total": round(total_entitlements, 2)
            },
            "deductions": {
                "deductions": deductions_data["total"],
                "loans": loans_data["total"],
                "total": round(total_deductions, 2)
            },
            "net_amount": round(net_amount, 2),
            "currency": "SAR"
        }
    }


# ============================================================
# CREATE SETTLEMENT (SAVE AS PENDING)
# ============================================================

@router.post("")
async def create_settlement(
    req: SettlementCreate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Create a new settlement request.
    Status will be 'pending_stas' for STAS to review and execute.
    """
    # التحقق من عدم وجود مخالصة قيد المعالجة
    existing = await db.settlements.find_one({
        "employee_id": req.employee_id,
        "status": {"$in": ["pending_stas", "preview"]}
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="يوجد طلب مخالصة قيد المعالجة لهذا الموظف"
        )
    
    # الحصول على Preview
    preview = await preview_settlement(req, user)
    
    now = datetime.now(timezone.utc).isoformat()
    transaction_number = await generate_settlement_number()
    
    settlement = {
        "id": str(uuid.uuid4()),
        "transaction_number": transaction_number,
        "employee_id": req.employee_id,
        "employee_name": preview["employee"]["name_ar"],
        "employee_code": preview["employee"]["employee_number"],
        "contract_id": preview["contract"]["id"],
        "contract_serial": preview["contract"]["serial"],
        "termination_type": req.termination_type,
        "termination_type_label": preview["contract"]["termination_type_label"],
        "last_working_day": req.last_working_day,
        "note": req.note,
        
        # Snapshot الكامل
        "snapshot": {
            "employee": preview["employee"],
            "contract": preview["contract"],
            "service": preview["service"],
            "wages": preview["wages"],
            "eos": preview["eos"],
            "leave": preview["leave"],
            "bonuses": preview["bonuses"],
            "deductions": preview["deductions"],
            "loans": preview["loans"],
            "totals": preview["totals"],
            "snapshot_date": now
        },
        
        # Admin adjustments
        "adjustments": [],
        
        "status": "pending_stas",
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name_ar") or user.get("full_name"),
        "created_at": now,
        "executed_by": None,
        "executed_at": None
    }
    
    await db.settlements.insert_one(settlement)
    settlement.pop("_id", None)
    
    return settlement


# ============================================================
# ADD ADJUSTMENT TO SETTLEMENT
# ============================================================

@router.post("/{settlement_id}/adjust")
async def add_adjustment(
    settlement_id: str,
    req: SettlementAdjustment,
    user=Depends(require_roles('sultan', 'stas'))
):
    """
    Add admin adjustment to a pending settlement.
    Only sultan and STAS can adjust.
    """
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="المخالصة غير موجودة")
    
    if settlement["status"] != "pending_stas":
        raise HTTPException(status_code=400, detail="لا يمكن التعديل على مخالصة منفذة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    adjustment = {
        "id": str(uuid.uuid4()),
        "type": req.adjustment_type,
        "amount": req.amount,
        "reason": req.reason,
        "added_by": user["user_id"],
        "added_by_name": user.get("full_name_ar") or user.get("full_name"),
        "added_at": now
    }
    
    # تحديث المجاميع
    snapshot = settlement["snapshot"]
    totals = snapshot["totals"]
    
    if req.adjustment_type in ["add_deduction", "adjust_leave"]:
        totals["deductions"]["total"] += req.amount
    elif req.adjustment_type in ["add_bonus", "adjust_eos"]:
        totals["entitlements"]["total"] += req.amount
    
    totals["net_amount"] = totals["entitlements"]["total"] - totals["deductions"]["total"]
    
    await db.settlements.update_one(
        {"id": settlement_id},
        {
            "$push": {"adjustments": adjustment},
            "$set": {"snapshot.totals": totals}
        }
    )
    
    return {"message": "تم إضافة التعديل", "adjustment": adjustment}


# ============================================================
# EXECUTE SETTLEMENT (STAS ONLY)
# ============================================================

@router.post("/{settlement_id}/execute")
async def execute_settlement_endpoint(
    settlement_id: str,
    req: SettlementExecute = SettlementExecute(),
    user=Depends(require_roles('stas'))
):
    """
    Execute a settlement - STAS exclusive.
    This is a ONE-TIME operation.
    
    Actions:
    1. Mark settlement as executed
    2. Record all financial entries
    3. Close the contract
    4. Lock the employee account
    5. Generate PDF
    """
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="المخالصة غير موجودة")
    
    if settlement["status"] == "executed":
        raise HTTPException(
            status_code=400, 
            detail="تم تنفيذ هذه المخالصة مسبقاً"
        )
    
    if settlement["status"] == "cancelled":
        raise HTTPException(
            status_code=400,
            detail="هذه المخالصة ملغاة"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    snapshot = settlement["snapshot"]
    employee_id = settlement["employee_id"]
    
    # 1. تسجيل مكافأة نهاية الخدمة في finance_ledger
    if snapshot["eos"]["final_amount"] > 0:
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "transaction_id": settlement["id"],
            "type": "credit",
            "category": "eos_payout",
            "amount": snapshot["eos"]["final_amount"],
            "description": f"مكافأة نهاية خدمة - {snapshot['service']['formatted_ar']}",
            "description_en": f"End of Service - {snapshot['service']['formatted_en']}",
            "settlement_ref": settlement_id,
            "date": now,
            "created_at": now
        })
    
    # 2. تسجيل بدل الإجازات
    if snapshot["leave"]["compensation"] > 0:
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "transaction_id": settlement["id"],
            "type": "credit",
            "category": "leave_compensation",
            "amount": snapshot["leave"]["compensation"],
            "description": f"بدل إجازات - {snapshot['leave']['balance']:.2f} يوم",
            "description_en": f"Leave compensation - {snapshot['leave']['balance']:.2f} days",
            "settlement_ref": settlement_id,
            "date": now,
            "created_at": now
        })
    
    # 3. تسوية جميع الخصومات والسلف
    await db.finance_ledger.update_many(
        {
            "employee_id": employee_id,
            "category": {"$in": ["deduction", "loan", "loan_issued", "advance", "penalty"]},
            "settled": {"$ne": True}
        },
        {"$set": {"settled": True, "settled_at": now, "settlement_ref": settlement_id}}
    )
    
    # 4. تسجيل المخالصة النهائية
    await db.finance_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "transaction_id": settlement["id"],
        "type": "settlement",
        "category": "settlement_final",
        "amount": snapshot["totals"]["net_amount"],
        "description": f"المخالصة النهائية - {settlement['transaction_number']}",
        "description_en": f"Final Settlement - {settlement['transaction_number']}",
        "settlement_ref": settlement_id,
        "snapshot": snapshot,
        "date": now,
        "created_at": now
    })
    
    # 5. إغلاق العقد
    contract = await db.contracts_v2.find_one({"id": settlement["contract_id"]})
    if contract:
        await db.contracts_v2.update_one(
            {"id": settlement["contract_id"]},
            {
                "$set": {
                    "status": "closed",
                    "closed_at": now,
                    "closed_by": user["user_id"],
                    "settlement_ref": settlement_id,
                    "termination_date": settlement["last_working_day"],
                    "termination_reason": settlement["termination_type"]
                },
                "$push": {
                    "status_history": {
                        "from_status": contract.get("status"),
                        "to_status": "closed",
                        "actor_id": user["user_id"],
                        "actor_name": "STAS",
                        "timestamp": now,
                        "note": f"تم إغلاق العقد بعد المخالصة - {settlement['transaction_number']}"
                    }
                }
            }
        )
    
    # 6. قفل حساب الموظف
    await db.users.update_one(
        {"employee_id": employee_id},
        {
            "$set": {
                "is_active": False,
                "deactivated_at": now,
                "deactivation_reason": "settlement_completed",
                "settlement_message": "يرجى مراجعة قسم الموارد البشرية لإكمال إجراءات المخالصة"
            }
        }
    )
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "is_active": False,
                "deactivated_at": now,
                "settlement_ref": settlement_id
            }
        }
    )
    
    # 7. تحديث المخالصة
    await db.settlements.update_one(
        {"id": settlement_id},
        {
            "$set": {
                "status": "executed",
                "executed_by": user["user_id"],
                "executed_at": now,
                "execution_note": req.note
            }
        }
    )
    
    return {
        "message": "تم تنفيذ المخالصة بنجاح",
        "settlement_id": settlement_id,
        "transaction_number": settlement["transaction_number"],
        "net_amount": snapshot["totals"]["net_amount"],
        "employee_locked": True
    }


# ============================================================
# CANCEL SETTLEMENT
# ============================================================

@router.post("/{settlement_id}/cancel")
async def cancel_settlement(
    settlement_id: str,
    note: str = "",
    user=Depends(require_roles('sultan', 'stas'))
):
    """Cancel a pending settlement"""
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="المخالصة غير موجودة")
    
    if settlement["status"] != "pending_stas":
        raise HTTPException(status_code=400, detail="لا يمكن إلغاء مخالصة منفذة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.settlements.update_one(
        {"id": settlement_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_by": user["user_id"],
                "cancelled_at": now,
                "cancellation_note": note
            }
        }
    )
    
    return {"message": "تم إلغاء المخالصة"}


# ============================================================
# SETTLEMENT PDF
# ============================================================

@router.get("/{settlement_id}/pdf")
async def get_settlement_pdf(
    settlement_id: str,
    user=Depends(get_current_user)
):
    """Generate and return settlement PDF"""
    from utils.pdf import generate_settlement_pdf
    
    settlement = await db.settlements.find_one({"id": settlement_id}, {"_id": 0})
    if not settlement:
        raise HTTPException(status_code=404, detail="المخالصة غير موجودة")
    
    if settlement["status"] != "executed":
        raise HTTPException(status_code=400, detail="لم يتم تنفيذ المخالصة بعد")
    
    # جلب بيانات الشركة
    branding = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    
    # توليد PDF
    pdf_bytes = generate_settlement_pdf(settlement, branding)
    
    filename = f"settlement_{settlement['transaction_number']}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}"
        }
    )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

async def generate_settlement_number() -> str:
    """Generate unique settlement transaction number: STL-YYYY-XXXX"""
    year = datetime.now(timezone.utc).year
    
    counter = await db.counters.find_one_and_update(
        {"type": "settlement", "year": year},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    
    seq = counter.get("seq", 1) if counter else 1
    return f"STL-{year}-{seq:04d}"


async def get_unsettled_deductions(employee_id: str) -> dict:
    """Get all unsettled deductions for employee"""
    items = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit",
        "category": {"$in": ["deduction", "penalty", "absence_deduction"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    return {
        "items": items,
        "total": sum(i["amount"] for i in items),
        "count": len(items)
    }


async def get_unsettled_bonuses(employee_id: str) -> dict:
    """Get all unsettled bonuses for employee"""
    items = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "credit",
        "category": "bonus",
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    return {
        "items": items,
        "total": sum(i["amount"] for i in items),
        "count": len(items)
    }


async def get_unsettled_loans(employee_id: str) -> dict:
    """Get all unsettled loans for employee"""
    items = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": {"$in": ["loan", "loan_issued", "advance"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    return {
        "items": items,
        "total": sum(i["amount"] for i in items),
        "count": len(items)
    }
