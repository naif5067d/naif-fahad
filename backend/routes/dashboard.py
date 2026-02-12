from fastapi import APIRouter, Depends
from database import db
from utils.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    role = user.get('role')
    user_id = user.get('user_id')
    stats = {}

    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        emp_id = emp['id'] if emp else None
        stats['pending_transactions'] = await db.transactions.count_documents(
            {"employee_id": emp_id, "status": {"$nin": ["executed", "rejected"]}}
        )
        leave_entries = await db.leave_ledger.find({"employee_id": emp_id, "leave_type": "annual"}, {"_id": 0}).to_list(1000)
        balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in leave_entries)
        stats['leave_balance'] = balance
        stats['recent_attendance'] = await db.attendance_ledger.count_documents({"employee_id": emp_id})

    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        emp_id = emp['id'] if emp else None
        direct_reports = await db.employees.find({"supervisor_id": emp_id}, {"_id": 0}).to_list(100)
        dr_ids = [d['id'] for d in direct_reports]
        stats['team_size'] = len(direct_reports)
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "supervisor", "employee_id": {"$in": dr_ids}, "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['team_on_leave'] = 0

    elif role in ('sultan', 'naif'):
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "ops", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})
        stats['total_transactions'] = await db.transactions.count_documents({})

    elif role == 'salah':
        stats['pending_finance'] = await db.transactions.count_documents(
            {"current_stage": "finance", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['total_finance_entries'] = await db.finance_ledger.count_documents({})
        stats['pending_approvals'] = stats['pending_finance']

    elif role == 'mohammed':
        stats['pending_ceo'] = await db.transactions.count_documents(
            {"current_stage": "ceo", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})
        stats['pending_approvals'] = stats['pending_ceo']

    elif role == 'stas':
        stats['pending_execution'] = await db.transactions.count_documents(
            {"current_stage": "stas", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['total_transactions'] = await db.transactions.count_documents({})
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})

    return stats
