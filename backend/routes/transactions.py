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
from services.notification_service import (
    notify_transaction_approved,
    notify_transaction_rejected,
    notify_transaction_executed,
    notify_transaction_submitted,
    create_notification,
    NotificationType,
    NotificationPriority
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
    types: Optional[str] = None,  # دعم أنواع متعددة مفصولة بفاصلة
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
    # دعم أنواع متعددة
    if types:
        type_list = [t.strip() for t in types.split(',')]
        query["type"] = {"$in": type_list}

    txs = await db.transactions.find(query, {"_id": 0, "id": 1, "ref_no": 1, "type": 1, "status": 1, "employee_id": 1, "current_stage": 1, "created_at": 1, "timeline": 1, "data": 1, "employee_name": 1, "workflow": 1, "return_count": 1}).sort("created_at", -1).to_list(500)
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
        "actor_name": user.get('full_name_ar', user.get('full_name', user['username'])),
        "timestamp": now,
        "note": body.note or "",
        "stage": stage
    }

    approval_entry = {
        "stage": stage,
        "approver_id": user['user_id'],
        "approver_name": user.get('full_name_ar', user.get('full_name', user['username'])),
        "approver_name_en": user.get('full_name', user['username']),
        "status": body.action,
        "timestamp": now,
        "note": body.note or ""
    }

    # Handle rejection
    if body.action == 'reject':
        # STAS rejection = Cancel the transaction (يتطلب تعليق)
        if stage == 'stas' and user.get('role') == 'stas':
            # تعليق مطلوب عند الإلغاء
            if not body.note or len(body.note.strip()) < 5:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "COMMENT_REQUIRED",
                        "message_ar": "يجب كتابة سبب الإلغاء (5 أحرف على الأقل)",
                        "message_en": "Cancellation reason is required (at least 5 characters)"
                    }
                )
            
            await db.transactions.update_one(
                {"id": transaction_id},
                {
                    "$set": {
                        "status": "cancelled", 
                        "current_stage": "cancelled", 
                        "updated_at": now,
                        "cancellation_reason": body.note.strip(),
                        "cancelled_by": user['user_id'],
                        "cancelled_by_name": user.get('full_name', user['username']),
                        "cancelled_at": now
                    },
                    "$push": {"timeline": {**timeline_event, "event": "cancelled"}, "approval_chain": approval_entry}
                }
            )
            
            # إرسال إشعار للموظف بالرفض
            emp_id = tx.get('employee_id')
            if emp_id:
                await notify_transaction_rejected(tx, emp_id, "STAS", body.note)
            
            return {"message": "Transaction cancelled by STAS", "status": "cancelled", "reason": body.note}
        
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

    # STAS special actions: return_to_sultan, return_to_ceo
    if body.action == 'return_to_sultan' and user.get('role') == 'stas':
        # When returning, remove rejection markers so the manager can act again
        # We need to check if sultan already acted and remove their entry from approval_chain
        existing_chain = tx.get('approval_chain', [])
        # Keep only non-ops approvals
        filtered_chain = [a for a in existing_chain if a.get('stage') != 'ops']
        
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {
                    "current_stage": "ops",
                    "status": "pending_ops",
                    "updated_at": now,
                    "rejection_source": None,
                    "ceo_rejected": False,
                    "approval_chain": filtered_chain
                },
                "$push": {"timeline": {
                    "event": "returned",
                    "actor": user['user_id'],
                    "actor_name": user.get('full_name_ar', user.get('full_name', user['username'])),
                    "timestamp": now,
                    "note": body.note or "Returned to Sultan by STAS",
                    "stage": "stas"
                }}
            }
        )
        return {"message": "Returned to Sultan", "status": "pending_ops", "current_stage": "ops"}

    if body.action == 'return_to_ceo' and user.get('role') == 'stas':
        # When returning to CEO, remove rejection markers so CEO can act again
        existing_chain = tx.get('approval_chain', [])
        # Keep only non-CEO approvals (allow CEO to re-approve/reject)
        filtered_chain = [a for a in existing_chain if a.get('stage') != 'ceo']
        
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {
                    "current_stage": "ceo",
                    "status": "pending_ceo",
                    "updated_at": now,
                    "rejection_source": None,
                    "ceo_rejected": False,
                    "approval_chain": filtered_chain
                },
                "$push": {"timeline": {
                    "event": "returned",
                    "actor": user['user_id'],
                    "actor_name": user.get('full_name_ar', user.get('full_name', user['username'])),
                    "timestamp": now,
                    "note": body.note or "Returned to CEO by STAS",
                    "stage": "stas"
                }}
            }
        )
        return {"message": "Returned to CEO", "status": "pending_ceo", "current_stage": "ceo"}

    # Approve: move to next stage in workflow
    workflow = tx.get('workflow', [])
    next_stage = get_next_stage(workflow, stage)
    emp_id = tx.get('employee_id')
    approver_name = user.get('full_name_ar', user.get('full_name', user['username']))

    if next_stage:
        # For STAS stage, status is just "stas" not "pending_stas"
        next_status = "stas" if next_stage == "stas" else f"pending_{next_stage}"
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {"current_stage": next_stage, "status": next_status, "updated_at": now},
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        
        # إرسال إشعار للموظف بالموافقة
        if emp_id:
            await notify_transaction_approved(tx, emp_id, approver_name)
        
        return {"message": f"Approved. Moved to {next_stage}", "status": next_status, "current_stage": next_stage}
    else:
        # Final stage is STAS - status is "stas" not "pending_stas"
        await db.transactions.update_one(
            {"id": transaction_id},
            {
                "$set": {"status": "stas", "current_stage": "stas", "updated_at": now},
                "$push": {"timeline": timeline_event, "approval_chain": approval_entry}
            }
        )
        
        # إرسال إشعار للموظف بالموافقة
        if emp_id:
            await notify_transaction_approved(tx, emp_id, approver_name)
        
        return {"message": "Approved. Ready for STAS execution", "status": "stas"}


@router.get("/{transaction_id}/pdf")
async def get_transaction_pdf(transaction_id: str, lang: str = 'ar', user=Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    emp = await db.employees.find_one({"id": tx.get('employee_id')}, {"_id": 0})
    
    # Fetch company branding for PDF
    branding = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    if not branding:
        branding = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_data": None
        }
    
    pdf_bytes, pdf_hash, integrity_id = generate_transaction_pdf(tx, emp, lang, branding)

    await db.transactions.update_one(
        {"id": transaction_id},
        {"$set": {"pdf_hash": pdf_hash, "integrity_id": integrity_id}}
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={tx['ref_no']}.pdf"}
    )


# ==================== STAS DELETE OWN TRANSACTION ====================

@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: str, user=Depends(get_current_user)):
    """
    حذف معاملة - STAS فقط يمكنه حذف معاملاته الخاصة
    
    القواعد:
    - STAS فقط يمكنه الحذف
    - يمكن حذف معاملاته الخاصة فقط (التي أنشأها أو طلبها)
    - لا يمكن حذف معاملات في حالة 'executed'
    """
    role = user.get('role')
    user_id = user.get('user_id')
    employee_id = user.get('employee_id')
    
    # التحقق من أن المستخدم هو STAS
    if role != 'stas':
        raise HTTPException(
            status_code=403,
            detail={
                "error": "NOT_AUTHORIZED",
                "message_en": "Only STAS can delete transactions",
                "message_ar": "فقط STAS يمكنه حذف المعاملات"
            }
        )
    
    # جلب المعاملة
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NOT_FOUND",
                "message_en": "Transaction not found",
                "message_ar": "المعاملة غير موجودة"
            }
        )
    
    # التحقق من ملكية المعاملة (STAS طلب المعاملة أو أنشأها)
    tx_employee_id = tx.get('employee_id')
    tx_created_by = tx.get('created_by')
    tx_requester_id = tx.get('requester_id')
    
    is_own_transaction = (
        tx_employee_id == employee_id or  # المعاملة تخص حساب STAS
        tx_employee_id == 'EMP-STAS' or  # المعاملة لموظف STAS
        tx_created_by == user_id or  # STAS أنشأ المعاملة
        tx_requester_id == user_id  # STAS طلب المعاملة
    )
    
    if not is_own_transaction:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "NOT_YOUR_TRANSACTION",
                "message_en": "You can only delete your own transactions",
                "message_ar": "يمكنك حذف معاملاتك الخاصة فقط"
            }
        )
    
    # تسجيل الحذف في audit log
    await db.deleted_transactions_log.insert_one({
        "id": str(uuid.uuid4()),
        "transaction_id": transaction_id,
        "ref_no": tx.get('ref_no'),
        "type": tx.get('type'),
        "deleted_by": user_id,
        "deleted_by_name": user.get('full_name', user.get('username')),
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "original_transaction": tx
    })
    
    # حذف المعاملة
    await db.transactions.delete_one({"id": transaction_id})
    
    return {
        "success": True,
        "message_ar": f"تم حذف المعاملة {tx.get('ref_no')} بنجاح",
        "message_en": f"Transaction {tx.get('ref_no')} deleted successfully",
        "ref_no": tx.get('ref_no')
    }


__all__ = ['get_next_ref_no', 'WORKFLOW_MAP', 'STAGE_ROLES']


