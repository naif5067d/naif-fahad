from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from routes.transactions import get_next_ref_no
from utils.workflow import WORKFLOW_MAP, should_skip_supervisor_stage, build_workflow_for_transaction
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/finance", tags=["finance"])


class FinanceTransactionRequest(BaseModel):
    employee_id: str
    code: int
    amount: float
    description: str
    tx_type: str = "credit"  # credit or debit


class AddFinanceCodeRequest(BaseModel):
    code: int
    name: str
    name_ar: str
    category: str


@router.get("/codes")
async def list_finance_codes(user=Depends(get_current_user)):
    codes = await db.finance_codes.find({"is_active": True}, {"_id": 0}).sort("code", 1).to_list(100)
    return codes


@router.post("/transaction")
async def create_finance_transaction(req: FinanceTransactionRequest, user=Depends(get_current_user)):
    role = user.get('role')
    if role not in ('sultan', 'naif', 'salah', 'stas'):
        raise HTTPException(status_code=403, detail="Only ops/finance/stas can create finance transactions")

    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    code_doc = await db.finance_codes.find_one({"code": req.code, "is_active": True}, {"_id": 0})
    if not code_doc:
        raise HTTPException(status_code=404, detail="Finance code not found or inactive")

    ref_no = await get_next_ref_no()
    base_workflow = WORKFLOW_MAP["finance_60"][:]
    workflow = skip_supervisor_stage(base_workflow, emp)
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "finance_60",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": req.employee_id,
        "data": {
            "code": req.code,
            "code_name": code_doc['name'],
            "code_name_ar": code_doc.get('name_ar', ''),
            "amount": req.amount,
            "tx_type": req.tx_type,
            "description": req.description,
            "employee_name": emp['full_name'],
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Finance 60: Code {req.code} - {code_doc['name']} - {req.amount} SAR",
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


@router.get("/statement/{employee_id}")
async def get_finance_statement(employee_id: str, user=Depends(get_current_user)):
    entries = await db.finance_ledger.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("date", -1).to_list(500)
    return entries


@router.post("/codes/add")
async def request_add_finance_code(req: AddFinanceCodeRequest, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    if req.code <= 60:
        raise HTTPException(status_code=400, detail="Codes 1-60 are reserved in the official catalog")

    existing = await db.finance_codes.find_one({"code": req.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Code {req.code} already exists")

    ref_no = await get_next_ref_no()
    now = datetime.now(timezone.utc).isoformat()
    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "add_finance_code",
        "status": "pending_ops",
        "created_by": user['user_id'],
        "employee_id": None,
        "data": {
            "code": req.code,
            "name": req.name,
            "name_ar": req.name_ar,
            "category": req.category,
        },
        "current_stage": "ops",
        "workflow": ["ops", "stas"],
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Request to add finance code {req.code}: {req.name}",
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
