from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from routes.transactions import get_next_ref_no, WORKFLOW_MAP
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


@router.get("/")
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


@router.post("/")
async def create_contract(req: ContractCreate, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

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
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.get('is_snapshot'):
        raise HTTPException(status_code=400, detail="Cannot edit a snapshot contract")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates")
    await db.contracts.update_one({"id": contract_id}, {"$set": updates})
    updated = await db.contracts.find_one({"id": contract_id}, {"_id": 0})
    return updated


@router.post("/settlement")
async def create_settlement(req: SettlementRequest, user=Depends(require_roles('sultan', 'naif'))):
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ref_no = await get_next_ref_no()
    now = datetime.now(timezone.utc).isoformat()
    total = req.final_salary + req.leave_encashment + req.eos_amount + req.other_payments - req.deductions

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "settlement",
        "status": "pending_ceo",
        "created_by": user['user_id'],
        "employee_id": req.employee_id,
        "data": {
            "employee_name": emp['full_name'],
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
        "workflow": ["ceo", "stas"],
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Settlement for {emp['full_name']} - Total: {total} SAR",
            "stage": "created"
        }],
        "approval_chain": [],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx
