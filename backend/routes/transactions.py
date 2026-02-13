from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from utils.pdf import generate_transaction_pdf
from datetime import datetime, timezone
import uuid
import io

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

WORKFLOW_MAP = {
    "leave_request": ["supervisor", "ops", "stas"],
    "finance_60": ["supervisor", "ops", "finance", "stas"],
    "settlement": ["ops", "ceo", "stas"],
    "warning": ["ops", "stas"],
    "contract": ["ops", "stas"],
    "asset": ["ops", "stas"],
    "attendance_correction": ["ops", "stas"],
    "add_finance_code": ["ops", "stas"],
}

STAGE_ROLES = {
    "supervisor": ["supervisor"],
    "ops": ["sultan", "naif"],
    "finance": ["salah"],
    "ceo": ["mohammed"],
    "stas": ["stas"],
}


async def get_next_ref_no():
    result = await db.counters.find_one_and_update(
        {"id": "transaction_ref"},
        {"$inc": {"seq": 1}},
        return_document=True
    )
    if not result:
        await db.counters.insert_one({"id": "transaction_ref", "seq": 1})
        seq = 1
    else:
        seq = result['seq']
    year = datetime.now(timezone.utc).year
    return f"TXN-{year}-{seq:04d}"


def skip_supervisor_stage(workflow, employee, requester_user_id=None):
    """
    Skip supervisor stage if:
    1. Employee has no supervisor_id assigned, OR
    2. The requester IS the supervisor (they would be approving their own request)
    """
    if not employee:
        return [s for s in workflow if s != 'supervisor']
    
    # No supervisor assigned
    if not employee.get('supervisor_id'):
        return [s for s in workflow if s != 'supervisor']
    
    # Check if requester is the supervisor - they can't approve their own requests
    if requester_user_id and employee.get('supervisor_id'):
        # If the requester's employee_id matches the supervisor_id, skip supervisor stage
        if employee.get('id') == employee.get('supervisor_id'):
            return [s for s in workflow if s != 'supervisor']
    
    return workflow


async def check_if_requester_is_supervisor(employee, requester_user_id):
    """
    Check if the requester is also the supervisor of this employee.
    This prevents supervisors from having to approve their own requests.
    """
    if not employee or not employee.get('supervisor_id'):
        return True  # No supervisor, skip
    
    supervisor_id = employee.get('supervisor_id')
    
    # Get the supervisor's employee record
    from database import db
    supervisor = await db.employees.find_one({"id": supervisor_id}, {"_id": 0})
    if supervisor and supervisor.get('user_id') == requester_user_id:
        return True  # Requester IS the supervisor, skip
    
    return False


@router.get("")
async def list_transactions(
    status: Optional[str] = None,
    tx_type: Optional[str] = None,
    user=Depends(get_current_user)
):
    role = user.get('role')
    user_id = user.get('user_id')
    query = {}

    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        if emp:
            query["employee_id"] = emp['id']
        else:
            return []
    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        if emp:
            reports = await db.employees.find({"supervisor_id": emp['id']}, {"_id": 0}).to_list(100)
            report_ids = [r['id'] for r in reports] + [emp['id']]
            query["$or"] = [
                {"employee_id": {"$in": report_ids}},
                {"current_stage": "supervisor", "employee_id": {"$in": report_ids}}
            ]
    elif role in ('sultan', 'naif'):
        pass  # see all
    elif role == 'salah':
        query["$or"] = [
            {"current_stage": "finance"},
            {"type": "finance_60"},
            {"approval_chain": {"$elemMatch": {"stage": "finance"}}}
        ]
    elif role == 'mohammed':
        query["$or"] = [
            {"current_stage": "ceo"},
            {"approval_chain": {"$elemMatch": {"stage": "ceo"}}}
        ]
    elif role == 'stas':
        pass  # see all

    if status:
        query["status"] = status
    if tx_type:
        query["type"] = tx_type

    txs = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return txs


@router.get("/{transaction_id}")
async def get_transaction(transaction_id: str, user=Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


class ApprovalAction(BaseModel):
    action: str  # "approve" or "reject"
    note: Optional[str] = ""


@router.post("/{transaction_id}/action")
async def transaction_action(transaction_id: str, body: ApprovalAction, user=Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx['status'] in ('executed', 'rejected'):
        raise HTTPException(status_code=400, detail="Transaction already finalized")

    stage = tx.get('current_stage')
    allowed_roles = STAGE_ROLES.get(stage, [])
    if user.get('role') not in allowed_roles and user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail=f"You cannot act on stage: {stage}")

    now = datetime.now(timezone.utc).isoformat()
    timeline_event = {
        "event": f"{body.action}d" if body.action == 'approve' else 'rejected',
        "actor": user['user_id'],
        "actor_name": user.get('full_name', user['username']),
        "timestamp": now,
        "note": body.note or "",
        "stage": stage
    }

    approval_entry = {
        "stage": stage,
        "approver_id": user['user_id'],
        "approver_name": user.get('full_name', user['username']),
        "status": body.action,
        "timestamp": now,
        "note": body.note or ""
    }

    if body.action == 'reject':
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {"status": "rejected", "updated_at": now},
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        return {"message": "Transaction rejected", "status": "rejected"}

    # Approve: move to next stage
    workflow = tx.get('workflow', [])
    current_idx = workflow.index(stage) if stage in workflow else -1
    if current_idx < len(workflow) - 1:
        next_stage = workflow[current_idx + 1]
        next_status = f"pending_{next_stage}"
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {"current_stage": next_stage, "status": next_status, "updated_at": now},
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        return {"message": f"Approved. Moved to {next_stage}", "status": next_status, "current_stage": next_stage}
    else:
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {"status": "pending_stas", "current_stage": "stas", "updated_at": now},
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        return {"message": "Approved. Ready for STAS execution", "status": "pending_stas"}


@router.get("/{transaction_id}/pdf")
async def get_transaction_pdf(transaction_id: str, user=Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    emp = await db.employees.find_one({"id": tx.get('employee_id')}, {"_id": 0})
    pdf_bytes, pdf_hash, integrity_id = generate_transaction_pdf(tx, emp)

    await db.transactions.update_one(
        {"id": transaction_id},
        {"$set": {"pdf_hash": pdf_hash, "integrity_id": integrity_id}}
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={tx['ref_no']}.pdf"}
    )
