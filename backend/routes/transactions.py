from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from utils.pdf import generate_transaction_pdf
from utils.workflow import (
    WORKFLOW_MAP, STAGE_ROLES,
    validate_stage_actor, get_next_stage,
    validate_only_stas_can_execute, can_initiate_transaction,
    should_skip_supervisor_stage, build_workflow_for_transaction,
    get_employee_by_user_id
)
from datetime import datetime, timezone
import uuid
import io

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


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
            query["$or"] = [
                {"employee_id": emp['id']},
                {"current_stage": "employee_accept", "employee_id": emp['id']}
            ]
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
        # Mohammed sees ONLY escalated transactions and finance_60/settlement requiring his approval
        query["$or"] = [
            {"current_stage": "ceo"},
            {"escalated": True},
            {"approval_chain": {"$elemMatch": {"stage": "ceo"}}},
            {"type": {"$in": ["finance_60", "settlement"]}, "workflow": "ceo"}
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
    action: str  # "approve", "reject", "escalate"
    note: Optional[str] = ""
    edit_data: Optional[dict] = None  # For Salah editing finance_60 data


@router.post("/{transaction_id}/action")
async def transaction_action(transaction_id: str, body: ApprovalAction, user=Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    stage = tx.get('current_stage')
    now = datetime.now(timezone.utc).isoformat()

    # Handle escalation from ops to CEO
    if body.action == 'escalate':
        if user.get('role') not in ('sultan', 'naif'):
            raise HTTPException(status_code=403, detail="Only Operations can escalate to CEO")
        if stage != 'ops':
            raise HTTPException(status_code=400, detail="Can only escalate from ops stage")

        # Insert CEO stage into workflow before STAS
        workflow = tx.get('workflow', [])
        if 'ceo' not in workflow:
            stas_idx = workflow.index('stas') if 'stas' in workflow else len(workflow)
            workflow.insert(stas_idx, 'ceo')

        timeline_event = {
            "event": "escalated",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', user['username']),
            "timestamp": now,
            "note": body.note or "Escalated to CEO",
            "stage": stage
        }

        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {
                    "current_stage": "ceo",
                    "status": "pending_ceo",
                    "escalated": True,
                    "escalated_by": user['user_id'],
                    "escalated_at": now,
                    "workflow": workflow,
                    "updated_at": now
                },
                "$push": {"timeline": timeline_event}
            }
        )
        return {"message": "Escalated to CEO", "status": "pending_ceo", "current_stage": "ceo"}

    # Validate stage actor
    validation = await validate_stage_actor(tx, user['user_id'], user.get('role'))
    if not validation['valid']:
        raise HTTPException(status_code=403, detail=validation['error_detail'])

    timeline_event = {
        "event": f"{body.action}d" if body.action == 'approve' else ('rejected' if body.action == 'reject' else body.action),
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

    # Handle rejection
    if body.action == 'reject':
        # CEO rejection → goes to STAS for final decision (execute rejection or return)
        if stage == 'ceo':
            await db.transactions.update_one(
                {"id": transaction_id},
                {
                    "$set": {
                        "current_stage": "stas",
                        "status": "stas",
                        "ceo_rejected": True,
                        "rejection_source": "ceo",
                        "updated_at": now
                    },
                    "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
                }
            )
            return {"message": "CEO rejected. Sent to STAS for final decision.", "status": "stas", "current_stage": "stas"}

        # Employee rejection on tangible custody → cancel immediately
        if stage == 'employee_accept':
            await db.transactions.update_one(
                {"id": transaction_id},
                {
                    "$set": {"status": "cancelled", "current_stage": "cancelled", "updated_at": now},
                    "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
                }
            )
            return {"message": "Custody rejected by employee. Cancelled.", "status": "cancelled"}

        # Other rejections → go to STAS for final decision
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {
                    "current_stage": "stas",
                    "status": "stas",
                    "rejection_source": stage,
                    "updated_at": now
                },
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        return {"message": "Rejected. Sent to STAS for final decision.", "status": "stas", "current_stage": "stas"}

    # Handle finance stage editing (Salah can edit finance_60 data)
    if stage == 'finance' and body.edit_data and tx.get('type') == 'finance_60':
        update_data = {}
        if 'amount' in body.edit_data:
            update_data['data.amount'] = body.edit_data['amount']
        if 'description' in body.edit_data:
            update_data['data.description'] = body.edit_data['description']
        if update_data:
            await db.transactions.update_one({"id": transaction_id}, {"$set": update_data})
            timeline_event['note'] = f"Edited and approved. {body.note or ''}"

    # Approve: move to next stage in workflow
    workflow = tx.get('workflow', [])
    next_stage = get_next_stage(workflow, stage)

    if next_stage:
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


__all__ = ['get_next_ref_no', 'WORKFLOW_MAP', 'STAGE_ROLES']
