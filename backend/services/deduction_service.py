"""
Deduction Service - خدمة مقترحات الخصم

ممنوع الخصم المباشر!
السير: النظام يقترح → سلطان يراجع → STAS ينفذ → finance_ledger

لا يكتب في finance_ledger إلا STAS فقط.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from database import db
from models.deduction_proposals import DeductionType, ProposalStatus, DEDUCTION_TYPE_AR


async def create_deduction_proposal(
    employee_id: str,
    deduction_type: DeductionType,
    amount: float,
    period_start: str,
    period_end: str,
    month: str,
    reason: str,
    reason_ar: str,
    explanation: dict,
    source_records: List[str],
    calculation_formula: str,
    calculation_details: dict,
    monthly_hours_id: Optional[str] = None
) -> dict:
    """إنشاء مقترح خصم جديد"""
    now = datetime.now(timezone.utc).isoformat()
    
    proposal = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "deduction_type": deduction_type.value,
        "deduction_type_ar": DEDUCTION_TYPE_AR.get(deduction_type, deduction_type.value),
        "amount": amount,
        "currency": "SAR",
        "period_start": period_start,
        "period_end": period_end,
        "month": month,
        "reason": reason,
        "reason_ar": reason_ar,
        "explanation": explanation,
        "source_records": source_records,
        "monthly_hours_id": monthly_hours_id,
        "calculation_formula": calculation_formula,
        "calculation_details": calculation_details,
        "status": ProposalStatus.PENDING.value,
        "created_at": now,
        "created_by": "system",
        "status_history": [{
            "from_status": None,
            "to_status": ProposalStatus.PENDING.value,
            "actor": "system",
            "timestamp": now,
            "note": "تم إنشاء المقترح تلقائياً"
        }]
    }
    
    await db.deduction_proposals.insert_one(proposal)
    proposal.pop('_id', None)
    
    return proposal


async def create_absence_deduction_proposal(employee_id: str, date: str, daily_status: dict) -> dict:
    """إنشاء مقترح خصم غياب"""
    # جلب بيانات الراتب
    contract = await db.contracts.find_one({
        "employee_id": employee_id,
        "$or": [{"status": "active"}, {"is_active": True}]
    }, {"_id": 0})
    
    if not contract:
        contract = await db.contracts_v2.find_one({
            "employee_id": employee_id,
            "status": "active"
        }, {"_id": 0})
    
    daily_salary = 0
    if contract:
        total_salary = (contract.get('salary', 0) or contract.get('basic_salary', 0)) + \
                      contract.get('housing_allowance', 0) + \
                      contract.get('transport_allowance', 0)
        daily_salary = total_salary / 30
    
    month = date[:7]  # YYYY-MM
    
    explanation = {
        "سبب القرار": "غياب بدون عذر",
        "التاريخ": date,
        "السجلات المرجعية": {
            "إجازة": "لا يوجد",
            "مهمة": "لا يوجد",
            "بصمة": "لا يوجد",
            "عطلة": "لا يوجد"
        },
        "الراتب اليومي": daily_salary,
        "المعادلة": "الراتب الشهري ÷ 30 = الخصم اليومي"
    }
    
    return await create_deduction_proposal(
        employee_id=employee_id,
        deduction_type=DeductionType.ABSENCE,
        amount=round(daily_salary, 2),
        period_start=date,
        period_end=date,
        month=month,
        reason="Absence without excuse",
        reason_ar="غياب بدون عذر",
        explanation=explanation,
        source_records=[daily_status.get('id', '')],
        calculation_formula="الراتب الشهري ÷ 30",
        calculation_details={
            "total_salary": contract.get('salary', 0) if contract else 0,
            "days_in_month": 30,
            "daily_rate": daily_salary
        }
    )


async def create_monthly_deduction_proposal(employee_id: str, month: str, monthly_hours: dict) -> dict:
    """إنشاء مقترح خصم نقص ساعات شهري"""
    deficit_days = monthly_hours.get('deficit_days', 0)
    
    if deficit_days <= 0:
        return None
    
    # جلب بيانات الراتب
    contract = await db.contracts.find_one({
        "employee_id": employee_id,
        "$or": [{"status": "active"}, {"is_active": True}]
    }, {"_id": 0})
    
    if not contract:
        contract = await db.contracts_v2.find_one({
            "employee_id": employee_id,
            "status": "active"
        }, {"_id": 0})
    
    daily_salary = 0
    if contract:
        total_salary = (contract.get('salary', 0) or contract.get('basic_salary', 0)) + \
                      contract.get('housing_allowance', 0) + \
                      contract.get('transport_allowance', 0)
        daily_salary = total_salary / 30
    
    amount = deficit_days * daily_salary
    
    # تحديد الفترة
    year, mon = month.split('-')
    period_start = f"{month}-01"
    # آخر يوم في الشهر
    if int(mon) == 12:
        period_end = f"{int(year)+1}-01-01"
    else:
        period_end = f"{year}-{int(mon)+1:02d}-01"
    
    explanation = {
        "سبب القرار": "نقص ساعات شهري",
        "الشهر": month,
        "الساعات المطلوبة": monthly_hours.get('required_hours', 0),
        "الساعات الفعلية": monthly_hours.get('actual_hours', 0),
        "ساعات التعويض": monthly_hours.get('compensation_hours', 0),
        "صافي الساعات": monthly_hours.get('net_hours', 0),
        "ساعات النقص": monthly_hours.get('deficit_hours', 0),
        "أيام النقص": deficit_days,
        "المعادلة": "كل 8 ساعات نقص = يوم غياب",
        "الراتب اليومي": daily_salary,
        "المبلغ": amount
    }
    
    return await create_deduction_proposal(
        employee_id=employee_id,
        deduction_type=DeductionType.HOURS_DEFICIT,
        amount=round(amount, 2),
        period_start=period_start,
        period_end=period_end,
        month=month,
        reason=f"Hours deficit: {deficit_days:.2f} days",
        reason_ar=f"نقص ساعات: {deficit_days:.2f} يوم",
        explanation=explanation,
        source_records=[],
        calculation_formula="أيام النقص × الراتب اليومي",
        calculation_details={
            "deficit_days": deficit_days,
            "daily_salary": daily_salary,
            "amount": amount
        },
        monthly_hours_id=monthly_hours.get('id')
    )


async def review_proposal(proposal_id: str, approved: bool, reviewer_id: str, note: str = "") -> dict:
    """مراجعة المقترح (سلطان/نايف)"""
    proposal = await db.deduction_proposals.find_one({"id": proposal_id}, {"_id": 0})
    
    if not proposal:
        return {"error": "المقترح غير موجود"}
    
    if proposal['status'] != ProposalStatus.PENDING.value:
        return {"error": "المقترح ليس في حالة انتظار المراجعة"}
    
    now = datetime.now(timezone.utc).isoformat()
    new_status = ProposalStatus.APPROVED.value if approved else ProposalStatus.REJECTED.value
    
    status_entry = {
        "from_status": proposal['status'],
        "to_status": new_status,
        "actor": reviewer_id,
        "timestamp": now,
        "note": note or ("تمت الموافقة" if approved else "تم الرفض")
    }
    
    await db.deduction_proposals.update_one(
        {"id": proposal_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": reviewer_id,
            "reviewed_at": now,
            "review_note": note
        },
        "$push": {"status_history": status_entry}}
    )
    
    proposal['status'] = new_status
    proposal['reviewed_by'] = reviewer_id
    proposal['reviewed_at'] = now
    
    return proposal


async def execute_proposal(proposal_id: str, executor_id: str, note: str = "") -> dict:
    """
    تنفيذ المقترح (STAS فقط)
    هنا يُكتب في finance_ledger
    """
    proposal = await db.deduction_proposals.find_one({"id": proposal_id}, {"_id": 0})
    
    if not proposal:
        return {"error": "المقترح غير موجود"}
    
    if proposal['status'] != ProposalStatus.APPROVED.value:
        return {"error": "المقترح غير موافق عليه"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إنشاء سجل في finance_ledger
    finance_entry = {
        "id": str(uuid.uuid4()),
        "employee_id": proposal['employee_id'],
        "type": "debit",
        "code": "DEDUCTION",
        "amount": proposal['amount'],
        "currency": proposal['currency'],
        "description": proposal['reason'],
        "description_ar": proposal['reason_ar'],
        "source": "deduction_proposal",
        "source_id": proposal_id,
        "deduction_type": proposal['deduction_type'],
        "month": proposal['month'],
        "explanation": proposal['explanation'],
        "executed_by": executor_id,
        "executed_at": now,
        "created_at": now
    }
    
    await db.finance_ledger.insert_one(finance_entry)
    finance_ledger_id = finance_entry['id']
    
    # تحديث المقترح
    status_entry = {
        "from_status": proposal['status'],
        "to_status": ProposalStatus.EXECUTED.value,
        "actor": executor_id,
        "timestamp": now,
        "note": note or "تم التنفيذ"
    }
    
    await db.deduction_proposals.update_one(
        {"id": proposal_id},
        {"$set": {
            "status": ProposalStatus.EXECUTED.value,
            "executed_by": executor_id,
            "executed_at": now,
            "execution_note": note,
            "finance_ledger_id": finance_ledger_id
        },
        "$push": {"status_history": status_entry}}
    )
    
    proposal['status'] = ProposalStatus.EXECUTED.value
    proposal['executed_by'] = executor_id
    proposal['executed_at'] = now
    proposal['finance_ledger_id'] = finance_ledger_id
    
    return proposal


async def get_pending_proposals(reviewer_role: str = None) -> List[dict]:
    """جلب المقترحات المعلقة"""
    query = {"status": ProposalStatus.PENDING.value}
    
    proposals = await db.deduction_proposals.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # إضافة بيانات الموظف
    for p in proposals:
        emp = await db.employees.find_one({"id": p['employee_id']}, {"_id": 0, "full_name": 1, "full_name_ar": 1})
        p['employee_name'] = emp.get('full_name_ar', emp.get('full_name', '')) if emp else ''
    
    return proposals


async def get_approved_proposals() -> List[dict]:
    """جلب المقترحات الموافق عليها (للتنفيذ)"""
    proposals = await db.deduction_proposals.find(
        {"status": ProposalStatus.APPROVED.value}, 
        {"_id": 0}
    ).sort("reviewed_at", -1).to_list(100)
    
    for p in proposals:
        emp = await db.employees.find_one({"id": p['employee_id']}, {"_id": 0, "full_name": 1, "full_name_ar": 1})
        p['employee_name'] = emp.get('full_name_ar', emp.get('full_name', '')) if emp else ''
    
    return proposals
