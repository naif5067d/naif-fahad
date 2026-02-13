from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from utils.workflow import WORKFLOW_MAP, can_initiate_transaction
from routes.transactions import get_next_ref_no
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/custody", tags=["custody"])


class TangibleCustodyRequest(BaseModel):
    employee_id: str
    item_name: str
    item_name_ar: Optional[str] = ""
    description: Optional[str] = ""
    serial_number: Optional[str] = ""
    estimated_value: Optional[float] = 0


class CustodyReturnRequest(BaseModel):
    custody_id: str  # The active custody record ID
    note: Optional[str] = ""


@router.post("/tangible")
async def create_tangible_custody(req: TangibleCustodyRequest, user=Depends(get_current_user)):
    """Create tangible custody assignment. Sultan or Naif only."""
    role = user.get('role')

    perm = await can_initiate_transaction('tangible_custody', role, user['user_id'])
    if not perm['valid']:
        raise HTTPException(status_code=403, detail=perm['error_detail'])

    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ref_no = await get_next_ref_no()
    workflow = WORKFLOW_MAP["tangible_custody"][:]
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "tangible_custody",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": req.employee_id,
        "data": {
            "item_name": req.item_name,
            "item_name_ar": req.item_name_ar or req.item_name,
            "description": req.description or "",
            "serial_number": req.serial_number or "",
            "estimated_value": req.estimated_value or 0,
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
            "note": f"Tangible custody: {req.item_name} assigned to {emp['full_name']}",
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


@router.post("/tangible/return")
async def create_custody_return(req: CustodyReturnRequest, user=Depends(get_current_user)):
    """Sultan confirms received custody item → goes to STAS for execution."""
    role = user.get('role')

    perm = await can_initiate_transaction('tangible_custody_return', role, user['user_id'])
    if not perm['valid']:
        raise HTTPException(status_code=403, detail=perm['error_detail'])

    # Find the active custody record
    custody = await db.custody_ledger.find_one({"id": req.custody_id, "status": "active"}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="Active custody record not found")

    ref_no = await get_next_ref_no()
    workflow = WORKFLOW_MAP["tangible_custody_return"][:]
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "tangible_custody_return",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": custody['employee_id'],
        "data": {
            "custody_id": req.custody_id,
            "item_name": custody['item_name'],
            "item_name_ar": custody.get('item_name_ar', ''),
            "serial_number": custody.get('serial_number', ''),
            "employee_name": custody.get('employee_name', ''),
            "employee_name_ar": custody.get('employee_name_ar', ''),
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Custody return: {custody['item_name']} - received from employee",
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


@router.get("/employee/{employee_id}")
async def get_employee_custodies(employee_id: str, user=Depends(get_current_user)):
    """Get all active tangible custodies for an employee."""
    custodies = await db.custody_ledger.find(
        {"employee_id": employee_id, "status": "active"}, {"_id": 0}
    ).sort("assigned_at", -1).to_list(100)
    return custodies


@router.get("/all")
async def get_all_custodies(user=Depends(get_current_user)):
    """Get all custody records (for admins)."""
    role = user.get('role')
    if role in ('employee', 'supervisor'):
        # Employees see only their own
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        custodies = await db.custody_ledger.find(
            {"employee_id": emp['id']}, {"_id": 0}
        ).sort("assigned_at", -1).to_list(100)
        return custodies

    custodies = await db.custody_ledger.find({}, {"_id": 0}).sort("assigned_at", -1).to_list(500)
    return custodies


@router.get("/check-clearance/{employee_id}")
async def check_clearance_eligibility(employee_id: str, user=Depends(get_current_user)):
    """Check if employee can have clearance (no active custody)."""
    active_count = await db.custody_ledger.count_documents(
        {"employee_id": employee_id, "status": "active"}
    )
    return {
        "eligible": active_count == 0,
        "active_custody_count": active_count,
        "message": "Employee has unreturned custody items" if active_count > 0 else "No active custody"
    }
