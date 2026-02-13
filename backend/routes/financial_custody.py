"""
Financial Custody (60 Code) System
Pure administrative custody - no employee linkage.

Flow:
1. Create custody (Sultan/Naif/Mohammed) with amount + title
2. Receive custody → balance shows
3. Sultan adds expenses (code + amount) → remaining decreases
4. Sultan sends for audit (تدقيق)
5. Salah audits/edits expenses → approves
6. Mohammed approves
7. STAS executes → if remaining > 0, carries to next custody
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/financial-custody", tags=["financial-custody"])


class CreateCustodyRequest(BaseModel):
    title: str
    title_ar: Optional[str] = ""
    total_amount: float


class ExpenseEntry(BaseModel):
    code: int
    description: str
    amount: float


class EditExpenseEntry(BaseModel):
    expense_id: str
    description: Optional[str] = None
    amount: Optional[float] = None


class AuditAction(BaseModel):
    action: str  # "approve", "reject"
    note: Optional[str] = ""
    edits: Optional[List[EditExpenseEntry]] = None  # Salah can edit during audit


async def _get_next_custody_number():
    last = await db.custody_financial.find_one(sort=[("custody_number_int", -1)])
    if last:
        return last.get("custody_number_int", 0) + 1
    return 1


@router.get("")
async def list_custodies(user=Depends(get_current_user)):
    role = user.get("role")
    if role not in ("sultan", "naif", "salah", "mohammed", "stas"):
        raise HTTPException(status_code=403, detail="Not authorized")
    custodies = await db.custody_financial.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return custodies


@router.get("/{custody_id}")
async def get_custody(custody_id: str, user=Depends(get_current_user)):
    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Custody not found")
    return c


@router.post("")
async def create_custody(req: CreateCustodyRequest, user=Depends(get_current_user)):
    role = user.get("role")
    if role not in ("sultan", "naif", "mohammed", "stas"):
        raise HTTPException(status_code=403, detail="Only Sultan/Naif/Mohammed can create")
    if req.total_amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    num = await _get_next_custody_number()
    now = datetime.now(timezone.utc).isoformat()

    custody = {
        "id": str(uuid.uuid4()),
        "custody_number": f"{num:03d}",
        "custody_number_int": num,
        "title": req.title,
        "title_ar": req.title_ar or req.title,
        "total_amount": req.total_amount,
        "carried_amount": 0,
        "carried_from": None,
        "expenses": [],
        "total_spent": 0,
        "remaining": req.total_amount,
        "status": "created",  # created → active → pending_audit → pending_approval → pending_stas → executed
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name", user["username"]),
        "received_by": None,
        "received_at": None,
        "audit_by": None,
        "audit_at": None,
        "audit_notes": "",
        "approved_by": None,
        "approved_at": None,
        "executed_by": None,
        "executed_at": None,
        "carried_to": None,
        "timeline": [{
            "event": "created",
            "actor": user["user_id"],
            "actor_name": user.get("full_name", user["username"]),
            "timestamp": now,
            "note": f"Custody {num:03d} created - {req.total_amount} SAR"
        }],
        "created_at": now,
        "updated_at": now,
    }
    await db.custody_financial.insert_one(custody)
    custody.pop("_id", None)
    return custody


@router.post("/{custody_id}/receive")
async def receive_custody(custody_id: str, user=Depends(get_current_user)):
    """Receive the custody - even creator must receive it."""
    role = user.get("role")
    if role not in ("sultan", "naif", "mohammed", "stas"):
        raise HTTPException(status_code=403, detail="Not authorized")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    if c["status"] != "created":
        raise HTTPException(status_code=400, detail="Custody already received")

    now = datetime.now(timezone.utc).isoformat()
    await db.custody_financial.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "active",
            "received_by": user["user_id"],
            "received_at": now,
            "updated_at": now
        }, "$push": {"timeline": {
            "event": "received",
            "actor": user["user_id"],
            "actor_name": user.get("full_name", user["username"]),
            "timestamp": now,
            "note": f"Custody received - Balance: {c['total_amount']} SAR"
        }}}
    )
    return {"message": "Custody received", "status": "active"}


@router.post("/{custody_id}/expense")
async def add_expense(custody_id: str, exp: ExpenseEntry, user=Depends(get_current_user)):
    """Sultan adds an expense to the custody."""
    role = user.get("role")
    if role not in ("sultan", "stas"):
        raise HTTPException(status_code=403, detail="Only Sultan can add expenses")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    if c["status"] != "active":
        raise HTTPException(status_code=400, detail="Custody must be active to add expenses")
    if exp.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if exp.amount > c["remaining"]:
        raise HTTPException(status_code=400, detail=f"Amount exceeds remaining balance ({c['remaining']} SAR)")

    # Lookup code name
    code_doc = await db.finance_codes.find_one({"code": exp.code, "is_active": True}, {"_id": 0})
    code_name = code_doc["name"] if code_doc else f"Code {exp.code}"
    code_name_ar = code_doc.get("name_ar", code_name) if code_doc else code_name

    now = datetime.now(timezone.utc).isoformat()
    expense_entry = {
        "id": str(uuid.uuid4()),
        "code": exp.code,
        "code_name": code_name,
        "code_name_ar": code_name_ar,
        "description": exp.description,
        "amount": exp.amount,
        "added_by": user["user_id"],
        "added_by_name": user.get("full_name", user["username"]),
        "added_at": now,
        "edited_by": None,
        "edited_at": None,
    }

    new_spent = c["total_spent"] + exp.amount
    new_remaining = c["total_amount"] + c.get("carried_amount", 0) - new_spent

    await db.custody_financial.update_one(
        {"id": custody_id},
        {
            "$push": {"expenses": expense_entry, "timeline": {
                "event": "expense_added",
                "actor": user["user_id"],
                "actor_name": user.get("full_name", user["username"]),
                "timestamp": now,
                "note": f"Expense: {code_name} - {exp.amount} SAR | Remaining: {new_remaining} SAR"
            }},
            "$set": {
                "total_spent": new_spent,
                "remaining": new_remaining,
                "updated_at": now
            }
        }
    )
    return {"message": "Expense added", "total_spent": new_spent, "remaining": new_remaining}


@router.delete("/{custody_id}/expense/{expense_id}")
async def remove_expense(custody_id: str, expense_id: str, user=Depends(get_current_user)):
    """Remove an expense (Sultan only, while active)."""
    role = user.get("role")
    if role not in ("sultan", "stas"):
        raise HTTPException(status_code=403, detail="Only Sultan can remove expenses")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c or c["status"] != "active":
        raise HTTPException(status_code=400, detail="Cannot modify")

    expense = next((e for e in c["expenses"] if e["id"] == expense_id), None)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    new_spent = c["total_spent"] - expense["amount"]
    new_remaining = c["total_amount"] + c.get("carried_amount", 0) - new_spent
    now = datetime.now(timezone.utc).isoformat()

    await db.custody_financial.update_one(
        {"id": custody_id},
        {
            "$pull": {"expenses": {"id": expense_id}},
            "$set": {"total_spent": new_spent, "remaining": new_remaining, "updated_at": now},
            "$push": {"timeline": {
                "event": "expense_removed",
                "actor": user["user_id"],
                "actor_name": user.get("full_name", user["username"]),
                "timestamp": now,
                "note": f"Removed: {expense['code_name']} - {expense['amount']} SAR"
            }}
        }
    )
    return {"message": "Expense removed", "total_spent": new_spent, "remaining": new_remaining}


@router.post("/{custody_id}/submit-audit")
async def submit_for_audit(custody_id: str, user=Depends(get_current_user)):
    """Sultan sends custody for audit (تدقيق) to Salah."""
    role = user.get("role")
    if role not in ("sultan", "stas"):
        raise HTTPException(status_code=403, detail="Only Sultan can submit for audit")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c or c["status"] != "active":
        raise HTTPException(status_code=400, detail="Custody must be active")
    if not c["expenses"]:
        raise HTTPException(status_code=400, detail="Add expenses before submitting for audit")

    now = datetime.now(timezone.utc).isoformat()
    await db.custody_financial.update_one(
        {"id": custody_id},
        {"$set": {"status": "pending_audit", "updated_at": now},
         "$push": {"timeline": {
             "event": "submitted_audit",
             "actor": user["user_id"],
             "actor_name": user.get("full_name", user["username"]),
             "timestamp": now,
             "note": f"Submitted for audit - Total spent: {c['total_spent']} SAR, Remaining: {c['remaining']} SAR"
         }}}
    )
    return {"message": "Submitted for audit", "status": "pending_audit"}


@router.post("/{custody_id}/audit")
async def audit_custody(custody_id: str, body: AuditAction, user=Depends(get_current_user)):
    """Salah audits: can edit expenses, then approve or reject."""
    role = user.get("role")
    if role not in ("salah", "stas"):
        raise HTTPException(status_code=403, detail="Only Salah (Finance) can audit")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c or c["status"] != "pending_audit":
        raise HTTPException(status_code=400, detail="Custody not pending audit")

    now = datetime.now(timezone.utc).isoformat()
    expenses = c["expenses"]

    # Apply edits if any
    if body.edits:
        for edit in body.edits:
            for exp in expenses:
                if exp["id"] == edit.expense_id:
                    if edit.amount is not None:
                        exp["amount"] = edit.amount
                    if edit.description is not None:
                        exp["description"] = edit.description
                    exp["edited_by"] = user["user_id"]
                    exp["edited_at"] = now

        total_spent = sum(e["amount"] for e in expenses)
        remaining = c["total_amount"] + c.get("carried_amount", 0) - total_spent
    else:
        total_spent = c["total_spent"]
        remaining = c["remaining"]

    if body.action == "reject":
        await db.custody_financial.update_one(
            {"id": custody_id},
            {"$set": {"status": "active", "expenses": expenses, "total_spent": total_spent, "remaining": remaining, "updated_at": now},
             "$push": {"timeline": {
                 "event": "audit_rejected",
                 "actor": user["user_id"],
                 "actor_name": user.get("full_name", user["username"]),
                 "timestamp": now,
                 "note": body.note or "Returned for corrections"
             }}}
        )
        return {"message": "Returned to Sultan for corrections", "status": "active"}

    # Approve → send to Mohammed
    await db.custody_financial.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "pending_approval",
            "expenses": expenses,
            "total_spent": total_spent,
            "remaining": remaining,
            "audit_by": user["user_id"],
            "audit_at": now,
            "audit_notes": body.note or "",
            "updated_at": now
        }, "$push": {"timeline": {
            "event": "audited",
            "actor": user["user_id"],
            "actor_name": user.get("full_name", user["username"]),
            "timestamp": now,
            "note": f"Audited and approved. {body.note or ''}"
        }}}
    )
    return {"message": "Audited. Sent to CEO for approval.", "status": "pending_approval"}


@router.post("/{custody_id}/approve")
async def approve_custody(custody_id: str, body: AuditAction, user=Depends(get_current_user)):
    """Mohammed approves the custody."""
    role = user.get("role")
    if role not in ("mohammed", "stas"):
        raise HTTPException(status_code=403, detail="Only CEO can approve")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c or c["status"] != "pending_approval":
        raise HTTPException(status_code=400, detail="Not pending approval")

    now = datetime.now(timezone.utc).isoformat()

    if body.action == "reject":
        await db.custody_financial.update_one(
            {"id": custody_id},
            {"$set": {"status": "pending_audit", "updated_at": now},
             "$push": {"timeline": {
                 "event": "approval_rejected",
                 "actor": user["user_id"],
                 "actor_name": user.get("full_name", user["username"]),
                 "timestamp": now,
                 "note": body.note or "Returned to audit"
             }}}
        )
        return {"message": "Returned to audit", "status": "pending_audit"}

    await db.custody_financial.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "pending_stas",
            "approved_by": user["user_id"],
            "approved_at": now,
            "updated_at": now
        }, "$push": {"timeline": {
            "event": "approved",
            "actor": user["user_id"],
            "actor_name": user.get("full_name", user["username"]),
            "timestamp": now,
            "note": f"CEO approved. {body.note or ''}"
        }}}
    )
    return {"message": "Approved. Sent to STAS for execution.", "status": "pending_stas"}


@router.post("/{custody_id}/execute")
async def execute_custody(custody_id: str, user=Depends(get_current_user)):
    """STAS executes the custody. If remaining > 0, carries to next custody."""
    role = user.get("role")
    if role != "stas":
        raise HTTPException(status_code=403, detail="Only STAS can execute")

    c = await db.custody_financial.find_one({"id": custody_id}, {"_id": 0})
    if not c or c["status"] != "pending_stas":
        raise HTTPException(status_code=400, detail="Not pending execution")

    now = datetime.now(timezone.utc).isoformat()
    remaining = c["remaining"]
    carried_to_id = None

    # If remaining > 0, create next custody with carried amount
    if remaining > 0:
        next_num = await _get_next_custody_number()
        next_custody = {
            "id": str(uuid.uuid4()),
            "custody_number": f"{next_num:03d}",
            "custody_number_int": next_num,
            "title": c["title"],
            "title_ar": c.get("title_ar", c["title"]),
            "total_amount": 0,
            "carried_amount": remaining,
            "carried_from": custody_id,
            "expenses": [],
            "total_spent": 0,
            "remaining": remaining,
            "status": "created",
            "created_by": "system",
            "created_by_name": "System (Carry Forward)",
            "received_by": None,
            "received_at": None,
            "audit_by": None, "audit_at": None, "audit_notes": "",
            "approved_by": None, "approved_at": None,
            "executed_by": None, "executed_at": None,
            "carried_to": None,
            "timeline": [{
                "event": "created",
                "actor": "system",
                "actor_name": "System",
                "timestamp": now,
                "note": f"Auto-created from custody {c['custody_number']} - Carried: {remaining} SAR"
            }],
            "created_at": now,
            "updated_at": now,
        }
        await db.custody_financial.insert_one(next_custody)
        next_custody.pop("_id", None)
        carried_to_id = next_custody["id"]

    # Execute current custody
    await db.custody_financial.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "executed",
            "executed_by": user["user_id"],
            "executed_at": now,
            "carried_to": carried_to_id,
            "updated_at": now
        }, "$push": {"timeline": {
            "event": "executed",
            "actor": user["user_id"],
            "actor_name": user.get("full_name", user["username"]),
            "timestamp": now,
            "note": f"Executed. Spent: {c['total_spent']} SAR" + (f" | Carried {remaining} SAR to custody {c['custody_number_int']+1:03d}" if remaining > 0 else " | Fully spent")
        }}}
    )

    # Record in finance ledger for each expense
    for exp in c["expenses"]:
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "custody_id": custody_id,
            "custody_number": c["custody_number"],
            "code": exp["code"],
            "code_name": exp["code_name"],
            "amount": exp["amount"],
            "type": "debit",
            "description": exp["description"],
            "date": now,
            "created_at": now
        })

    msg = f"Executed. Total spent: {c['total_spent']} SAR."
    if remaining > 0:
        msg += f" Remaining {remaining} SAR carried to next custody."
    return {"message": msg, "status": "executed", "carried_to": carried_to_id}


@router.get("/summary/totals")
async def get_custody_summary(user=Depends(get_current_user)):
    """Get summary totals across all custodies."""
    role = user.get("role")
    if role not in ("sultan", "naif", "salah", "mohammed", "stas"):
        raise HTTPException(status_code=403, detail="Not authorized")

    all_custodies = await db.custody_financial.find({}, {"_id": 0}).to_list(500)
    total_amount = sum(c.get("total_amount", 0) + c.get("carried_amount", 0) for c in all_custodies)
    total_spent = sum(c.get("total_spent", 0) for c in all_custodies)
    total_remaining = sum(c.get("remaining", 0) for c in all_custodies if c["status"] != "executed")

    return {
        "total_custodies": len(all_custodies),
        "total_amount": total_amount,
        "total_spent": total_spent,
        "total_remaining": total_remaining,
        "active": sum(1 for c in all_custodies if c["status"] in ("active", "created")),
        "pending": sum(1 for c in all_custodies if c["status"].startswith("pending")),
        "executed": sum(1 for c in all_custodies if c["status"] == "executed"),
    }
