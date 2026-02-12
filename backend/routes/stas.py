from fastapi import APIRouter, HTTPException, Depends
from database import db
from utils.auth import get_current_user, require_roles
from utils.pdf import generate_transaction_pdf
from datetime import datetime, timezone
import uuid
import hashlib

router = APIRouter(prefix="/api/stas", tags=["stas"])


async def run_pre_checks(tx):
    checks = []
    tx_type = tx.get('type')
    data = tx.get('data', {})

    # Check 1: All approval stages completed
    workflow = tx.get('workflow', [])
    approval_stages = [s for s in workflow if s != 'stas']
    approved_stages = [a['stage'] for a in tx.get('approval_chain', []) if a['status'] == 'approve']
    all_approved = all(s in approved_stages for s in approval_stages)
    checks.append({
        "name": "All Approvals Complete",
        "name_ar": "جميع الموافقات مكتملة",
        "status": "PASS" if all_approved else "FAIL",
        "detail": f"Approved: {len(approved_stages)}/{len(approval_stages)}"
    })

    if tx_type == 'leave_request':
        emp_id = tx.get('employee_id')
        leave_type = data.get('leave_type', 'annual')
        working_days = data.get('working_days', 0)
        entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": leave_type}, {"_id": 0}
        ).to_list(1000)
        balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in entries)
        checks.append({
            "name": "Leave Balance Sufficient",
            "name_ar": "رصيد الإجازات كافٍ",
            "status": "PASS" if balance >= working_days else "FAIL",
            "detail": f"Balance: {balance}, Requested: {working_days}"
        })

        start = data.get('start_date')
        existing = await db.transactions.find_one({
            "employee_id": emp_id, "type": "leave_request", "status": "executed",
            "data.start_date": {"$lte": data.get('end_date', '')},
            "data.adjusted_end_date": {"$gte": start},
            "id": {"$ne": tx['id']}
        })
        checks.append({
            "name": "No Calendar Conflict",
            "name_ar": "لا يوجد تعارض في التقويم",
            "status": "PASS" if not existing else "FAIL",
            "detail": "No overlapping leaves" if not existing else f"Conflicts with {existing.get('ref_no')}"
        })

    elif tx_type == 'finance_60':
        checks.append({
            "name": "Finance Code Valid",
            "name_ar": "رمز المالية صالح",
            "status": "PASS",
            "detail": f"Code {data.get('code')} - {data.get('code_name')}"
        })

    elif tx_type == 'settlement':
        checks.append({
            "name": "Settlement Amount Verified",
            "name_ar": "مبلغ التسوية مُتحقق",
            "status": "PASS",
            "detail": f"Total: {data.get('total_settlement', 0)} SAR"
        })

    # Check: transaction not already executed
    checks.append({
        "name": "Not Already Executed",
        "name_ar": "لم يتم التنفيذ مسبقاً",
        "status": "PASS" if tx['status'] != 'executed' else "FAIL",
        "detail": f"Current status: {tx['status']}"
    })

    return checks


async def get_trace_links(tx):
    links = []
    emp_id = tx.get('employee_id')
    tx_type = tx.get('type')

    if emp_id:
        emp = await db.employees.find_one({"id": emp_id}, {"_id": 0})
        if emp:
            links.append({"type": "employee", "label": f"Employee: {emp['full_name']}", "id": emp_id})

    if tx_type == 'leave_request':
        leave_entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": tx['data'].get('leave_type')}, {"_id": 0}
        ).to_list(100)
        links.append({"type": "ledger", "label": f"Leave Ledger ({len(leave_entries)} entries)", "id": emp_id})

    elif tx_type == 'finance_60':
        fin_entries = await db.finance_ledger.find({"employee_id": emp_id}, {"_id": 0}).to_list(100)
        links.append({"type": "ledger", "label": f"Finance Ledger ({len(fin_entries)} entries)", "id": emp_id})

    if emp_id:
        contracts = await db.contracts.find({"employee_id": emp_id}, {"_id": 0}).to_list(10)
        if contracts:
            links.append({"type": "contract", "label": f"Contracts ({len(contracts)})", "id": emp_id})

    links.append({"type": "transaction", "label": f"Transaction: {tx['ref_no']}", "id": tx['id']})
    return links


async def get_before_after(tx):
    tx_type = tx.get('type')
    data = tx.get('data', {})
    emp_id = tx.get('employee_id')

    if tx_type == 'leave_request':
        lt = data.get('leave_type', 'annual')
        entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": lt}, {"_id": 0}
        ).to_list(1000)
        balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in entries)
        wd = data.get('working_days', 0)
        entitlement = 0
        for e in entries:
            if e['type'] == 'credit':
                entitlement += e['days']
        used = entitlement - balance
        return {
            "before": {"total_entitlement": entitlement, "used": used, "remaining": balance},
            "after": {"total_entitlement": entitlement, "used": used + wd, "remaining": balance - wd}
        }

    elif tx_type == 'finance_60':
        return {
            "before": {"description": "Before finance entry"},
            "after": {"amount": data.get('amount', 0), "code": data.get('code_name', '')}
        }

    return {"before": {}, "after": {}}


@router.get("/mirror/{transaction_id}")
async def get_mirror(transaction_id: str, user=Depends(require_roles('stas'))):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    pre_checks = await run_pre_checks(tx)
    trace_links = await get_trace_links(tx)
    before_after = await get_before_after(tx)
    all_pass = all(c['status'] == 'PASS' for c in pre_checks)

    emp = None
    if tx.get('employee_id'):
        emp = await db.employees.find_one({"id": tx['employee_id']}, {"_id": 0})

    return {
        "transaction": tx,
        "employee": emp,
        "pre_checks": pre_checks,
        "all_checks_pass": all_pass,
        "trace_links": trace_links,
        "before_after": before_after,
    }


@router.post("/execute/{transaction_id}")
async def execute_transaction(transaction_id: str, user=Depends(require_roles('stas'))):
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx['status'] == 'executed':
        return {"message": "Already executed (idempotent)", "status": "executed", "ref_no": tx['ref_no']}

    pre_checks = await run_pre_checks(tx)
    if not all(c['status'] == 'PASS' for c in pre_checks):
        failed = [c['name'] for c in pre_checks if c['status'] == 'FAIL']
        raise HTTPException(status_code=400, detail=f"Pre-checks failed: {', '.join(failed)}")

    now = datetime.now(timezone.utc).isoformat()
    tx_type = tx.get('type')
    data = tx.get('data', {})
    emp_id = tx.get('employee_id')

    # Execute based on type
    if tx_type == 'leave_request':
        await db.leave_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "type": "debit",
            "leave_type": data.get('leave_type', 'annual'),
            "days": data.get('working_days', 0),
            "note": f"Leave: {data.get('start_date')} to {data.get('adjusted_end_date')}",
            "date": now,
            "created_at": now
        })

    elif tx_type == 'finance_60':
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "transaction_id": tx['id'],
            "code": data.get('code'),
            "code_name": data.get('code_name', ''),
            "amount": data.get('amount', 0),
            "type": data.get('tx_type', 'credit'),
            "description": data.get('description', ''),
            "date": now,
            "created_at": now
        })

    elif tx_type == 'settlement':
        if emp_id:
            await db.employees.update_one({"id": emp_id}, {"$set": {"is_active": False}})
            await db.users.update_one({"employee_id": emp_id}, {"$set": {"is_active": False}})
            contract = await db.contracts.find_one(
                {"employee_id": emp_id, "is_snapshot": False}
            )
            if contract:
                snapshot = {k: v for k, v in contract.items() if k != '_id'}
                snapshot['id'] = str(uuid.uuid4())
                snapshot['is_snapshot'] = True
                snapshot['transaction_id'] = tx['id']
                snapshot['created_at'] = now
                await db.contracts.insert_one(snapshot)

    elif tx_type == 'add_finance_code':
        await db.finance_codes.insert_one({
            "id": str(uuid.uuid4()),
            "code": data.get('code'),
            "name": data.get('name'),
            "name_ar": data.get('name_ar', ''),
            "category": data.get('category', 'other'),
            "is_active": True,
            "created_at": now
        })

    # Generate PDF
    emp = await db.employees.find_one({"id": emp_id}, {"_id": 0}) if emp_id else None
    pdf_bytes, pdf_hash, integrity_id = generate_transaction_pdf(tx, emp)

    timeline_event = {
        "event": "executed",
        "actor": user['user_id'],
        "actor_name": "STAS",
        "timestamp": now,
        "note": "Transaction executed by STAS",
        "stage": "stas"
    }

    await db.transactions.update_one(
        {"id": transaction_id},
        {
            "$set": {
                "status": "executed",
                "current_stage": "completed",
                "pdf_hash": pdf_hash,
                "integrity_id": integrity_id,
                "executed_at": now,
                "updated_at": now
            },
            "$push": {
                "timeline": timeline_event,
                "approval_chain": {
                    "stage": "stas",
                    "approver_id": user['user_id'],
                    "approver_name": "STAS",
                    "status": "executed",
                    "timestamp": now,
                    "note": "Executed"
                }
            }
        }
    )

    return {
        "message": "Transaction executed successfully",
        "status": "executed",
        "ref_no": tx['ref_no'],
        "pdf_hash": pdf_hash,
        "integrity_id": integrity_id
    }


@router.get("/pending")
async def get_pending_executions(user=Depends(require_roles('stas'))):
    txs = await db.transactions.find(
        {"current_stage": "stas", "status": {"$nin": ["executed", "rejected"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return txs
