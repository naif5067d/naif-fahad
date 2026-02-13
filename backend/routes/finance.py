from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from routes.transactions import get_next_ref_no
from utils.workflow import WORKFLOW_MAP, can_initiate_transaction
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/finance", tags=["finance"])


class FinanceTransactionRequest(BaseModel):
    employee_id: str
    code: int
    amount: float
    description: str
    tx_type: str = "credit"  # credit or debit
    code_name: Optional[str] = None  # For new codes: user provides name
    code_name_ar: Optional[str] = None
    code_category: Optional[str] = None


@router.get("/codes")
async def list_finance_codes(user=Depends(get_current_user)):
    codes = await db.finance_codes.find({"is_active": True}, {"_id": 0}).sort("code", 1).to_list(200)
    return codes


@router.get("/codes/lookup/{code}")
async def lookup_finance_code(code: int, user=Depends(get_current_user)):
    """Lookup a finance code by number. Returns the code definition if found."""
    code_doc = await db.finance_codes.find_one({"code": code, "is_active": True}, {"_id": 0})
    if code_doc:
        return {"found": True, "code": code_doc}
    return {"found": False, "code": None}


@router.post("/transaction")
async def create_finance_transaction(req: FinanceTransactionRequest, user=Depends(get_current_user)):
    """Create a financial custody (60 Code) transaction. Sultan only."""
    role = user.get('role')

    # Validate initiation permission - Sultan only
    perm = await can_initiate_transaction('finance_60', role, user['user_id'])
    if not perm['valid']:
        raise HTTPException(status_code=403, detail=perm['error_detail'])

    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Lookup finance code - auto-create if not found
    code_doc = await db.finance_codes.find_one({"code": req.code, "is_active": True}, {"_id": 0})

    if not code_doc:
        # Code doesn't exist - require name and create it
        if not req.code_name:
            raise HTTPException(status_code=400, detail="Code not found. Provide code_name to define it.")

        code_doc = {
            "id": str(uuid.uuid4()),
            "code": req.code,
            "name": req.code_name,
            "name_ar": req.code_name_ar or req.code_name,
            "category": req.code_category or "other",
            "is_active": True,
            "created_by": user['user_id'],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.finance_codes.insert_one(code_doc)
        code_doc.pop('_id', None)

    ref_no = await get_next_ref_no()
    # Finance 60 workflow: finance (Salah) → ceo (Mohammed) → stas
    workflow = WORKFLOW_MAP["finance_60"][:]
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
            "employee_name_ar": emp.get('full_name_ar', ''),
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Financial Custody: Code {req.code} - {code_doc['name']} - {req.amount} SAR",
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
async def request_add_finance_code(req: dict, user=Depends(get_current_user)):
    role = user.get('role')
    if role not in ('stas', 'sultan', 'naif', 'salah'):
        raise HTTPException(status_code=403, detail="Not authorized")
    code = req.get('code')
    name = req.get('name')
    name_ar = req.get('name_ar', '')
    category = req.get('category', 'other')

    if not code or not name:
        raise HTTPException(status_code=400, detail="code and name are required")

    existing = await db.finance_codes.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Code {code} already exists")

    code_doc = {
        "id": str(uuid.uuid4()),
        "code": code,
        "name": name,
        "name_ar": name_ar or name,
        "category": category,
        "is_active": True,
        "created_by": user['user_id'],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.finance_codes.insert_one(code_doc)
    code_doc.pop('_id', None)
    return code_doc


@router.put("/codes/{code_id}")
async def update_finance_code(code_id: str, req: dict, user=Depends(get_current_user)):
    """Edit a finance code - Sultan, Naif, Salah, STAS can edit."""
    role = user.get('role')
    if role not in ('stas', 'sultan', 'naif', 'salah'):
        raise HTTPException(status_code=403, detail="Not authorized to edit codes")

    code_doc = await db.finance_codes.find_one({"id": code_id})
    if not code_doc:
        raise HTTPException(status_code=404, detail="Code not found")

    update = {}
    if 'name' in req:
        update['name'] = req['name']
    if 'name_ar' in req:
        update['name_ar'] = req['name_ar']
    if 'code' in req:
        # Check for duplicate
        dup = await db.finance_codes.find_one({"code": req['code'], "id": {"$ne": code_id}})
        if dup:
            raise HTTPException(status_code=400, detail=f"Code {req['code']} already exists")
        update['code'] = req['code']
    if 'category' in req:
        update['category'] = req['category']

    if update:
        update['updated_at'] = datetime.now(timezone.utc).isoformat()
        update['updated_by'] = user['user_id']
        await db.finance_codes.update_one({"id": code_id}, {"$set": update})

    result = await db.finance_codes.find_one({"id": code_id}, {"_id": 0})
    return result
