from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from routes.transactions import get_next_ref_no
from utils.workflow import WORKFLOW_MAP
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


class ContractCreate(BaseModel):
    employee_id: str
    contract_type: str
    start_date: str
    end_date: Optional[str] = None
    salary: float
    housing_allowance: float = 0
    transport_allowance: float = 0
    other_allowances: float = 0
    probation_months: int = 3
    notice_period_days: int = 30
    notes: str = ""


class ContractUpdate(BaseModel):
    salary: Optional[float] = None
    housing_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    other_allowances: Optional[float] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None


class SettlementRequest(BaseModel):
    employee_id: str
    reason: str
    settlement_text: str
    final_salary: float
    leave_encashment: float = 0
    eos_amount: float = 0
    other_payments: float = 0
    deductions: float = 0


@router.get("")
async def list_contracts(user=Depends(get_current_user)):
    role = user.get('role')
    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        return await db.contracts.find({"employee_id": emp['id']}, {"_id": 0}).sort("version", -1).to_list(50)
    return await db.contracts.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.get("/{employee_id}")
async def get_employee_contracts(employee_id: str, user=Depends(get_current_user)):
    return await db.contracts.find({"employee_id": employee_id}, {"_id": 0}).sort("version", -1).to_list(50)


@router.post("")
async def create_contract(req: ContractCreate, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    existing = await db.contracts.find({"employee_id": req.employee_id}).sort("version", -1).to_list(1)
    version = (existing[0]['version'] + 1) if existing else 1

    now = datetime.now(timezone.utc).isoformat()
    contract = {
        "id": str(uuid.uuid4()),
        "employee_id": req.employee_id,
        "contract_type": req.contract_type,
        "version": version,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "salary": req.salary,
        "housing_allowance": req.housing_allowance,
        "transport_allowance": req.transport_allowance,
        "other_allowances": req.other_allowances,
        "probation_months": req.probation_months,
        "notice_period_days": req.notice_period_days,
        "notes": req.notes,
        "status": "active",
        "is_active": True,
        "is_snapshot": False,
        "transaction_id": None,
        "created_by": user['user_id'],
        "created_at": now,
    }
    await db.contracts.insert_one(contract)
    contract.pop('_id', None)
    return contract


@router.patch("/{contract_id}")
async def update_contract(contract_id: str, req: ContractUpdate, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    contract = await db.contracts.find_one({"id": contract_id})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    if contract.get('is_snapshot'):
        raise HTTPException(status_code=400, detail="لا يمكن تعديل عقد سابق")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد تحديثات")
    await db.contracts.update_one({"id": contract_id}, {"$set": updates})
    updated = await db.contracts.find_one({"id": contract_id}, {"_id": 0})
    return updated


@router.get("/settlement/calculate/{employee_id}")
async def calculate_settlement_data(employee_id: str, user=Depends(require_roles('sultan', 'naif', 'stas'))):
    """
    حساب بيانات المخالصة تلقائياً:
    - الراتب الأساسي
    - رصيد الإجازات
    - مكافأة نهاية الخدمة
    - الخصومات المنفذة من finance_ledger
    """
    from services.leave_service import get_employee_leave_summary
    
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # الراتب الأساسي
    basic_salary = emp.get('basic_salary', 0)
    
    # حساب رصيد الإجازات
    leave_summary = await get_employee_leave_summary(employee_id)
    annual_balance = leave_summary.get('annual', {}).get('remaining', 0)
    daily_rate = basic_salary / 30 if basic_salary else 0
    leave_encashment = round(annual_balance * daily_rate, 2)
    
    # حساب مكافأة نهاية الخدمة (مبسط)
    join_date = emp.get('join_date', '')
    years_of_service = 0
    if join_date:
        try:
            from datetime import datetime
            join_dt = datetime.strptime(join_date[:10], "%Y-%m-%d")
            now_dt = datetime.now()
            years_of_service = (now_dt - join_dt).days / 365
        except:
            pass
    
    # مكافأة نهاية الخدمة حسب نظام العمل السعودي
    if years_of_service <= 5:
        eos_amount = round((basic_salary / 2) * years_of_service, 2)
    else:
        eos_amount = round((basic_salary / 2) * 5 + basic_salary * (years_of_service - 5), 2)
    
    # الخصومات المنفذة من finance_ledger (كل الخصومات غير المُسددة)
    total_deductions = 0
    deduction_details = []
    ledger_entries = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit"
    }, {"_id": 0}).to_list(100)
    
    for entry in ledger_entries:
        amount = entry.get('amount', 0)
        total_deductions += amount
        deduction_details.append({
            "date": entry.get('created_at', '')[:10] if entry.get('created_at') else '',
            "amount": amount,
            "reason": entry.get('note', entry.get('description', ''))
        })
    
    return {
        "employee_id": employee_id,
        "employee_name": emp.get('full_name', ''),
        "employee_name_ar": emp.get('full_name_ar', ''),
        "basic_salary": basic_salary,
        "years_of_service": round(years_of_service, 1),
        "leave_balance_days": annual_balance,
        "leave_encashment": leave_encashment,
        "eos_amount": eos_amount,
        "total_deductions": round(total_deductions, 2),
        "deduction_details": deduction_details,
        "net_settlement": round(basic_salary + leave_encashment + eos_amount - total_deductions, 2)
    }


@router.post("/settlement")
async def create_settlement(req: SettlementRequest, user=Depends(require_roles('sultan', 'naif'))):
    """
    Settlement workflow:
    - Only Sultan (Ops Admin) can initiate
    - Mohammed (CEO) must approve
    - STAS executes and locks the account
    """
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # Check employee is active
    if not emp.get('is_active', True):
        raise HTTPException(status_code=400, detail="الموظف غير نشط بالفعل")
    
    # Check for existing pending settlement
    existing = await db.transactions.find_one({
        "employee_id": req.employee_id,
        "type": "settlement",
        "status": {"$nin": ["executed", "rejected"]}
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Pending settlement exists: {existing['ref_no']}"
        )

    ref_no = await get_next_ref_no()
    now = datetime.now(timezone.utc).isoformat()
    total = req.final_salary + req.leave_encashment + req.eos_amount + req.other_payments - req.deductions

    # Settlement workflow: Sultan → Mohammed (CEO) → STAS
    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "settlement",
        "status": "pending_ceo",
        "created_by": user['user_id'],
        "employee_id": req.employee_id,
        "data": {
            "employee_name": emp.get('full_name', ''),
            "employee_name_ar": emp.get('full_name_ar', ''),
            "reason": req.reason,
            "settlement_text": req.settlement_text,
            "final_salary": req.final_salary,
            "leave_encashment": req.leave_encashment,
            "eos_amount": req.eos_amount,
            "other_payments": req.other_payments,
            "deductions": req.deductions,
            "total_settlement": total,
        },
        "current_stage": "ceo",
        "workflow": ["ceo", "stas"],  # Sultan initiates, then CEO, then STAS
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Settlement initiated for {emp.get('full_name', '')} - Total: {total} SAR",
            "stage": "created"
        }],
        "approval_chain": [{
            "stage": "ops",
            "approver_id": user['user_id'],
            "approver_name": user.get('full_name', ''),
            "status": "initiated",
            "timestamp": now,
            "note": "Settlement initiated by Operations"
        }],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx
