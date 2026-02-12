from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/employees", tags=["employees"])


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    full_name_ar: Optional[str] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None
    position: Optional[str] = None


@router.get("/")
async def list_employees(user=Depends(get_current_user)):
    role = user.get('role')
    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        return [emp] if emp else []
    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        reports = await db.employees.find(
            {"$or": [{"id": emp['id']}, {"supervisor_id": emp['id']}]}, {"_id": 0}
        ).to_list(100)
        return reports
    else:
        return await db.employees.find({}, {"_id": 0}).to_list(500)


@router.get("/{employee_id}")
async def get_employee(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    role = user.get('role')
    if role == 'employee':
        own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not own or own['id'] != employee_id:
            raise HTTPException(status_code=403, detail="Access denied")
    return emp


@router.patch("/{employee_id}")
async def update_employee(employee_id: str, update: EmployeeUpdate, user=Depends(require_roles('stas'))):
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    await db.employees.update_one({"id": employee_id}, {"$set": updates})
    if 'full_name' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name": updates['full_name']}})
    if 'full_name_ar' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name_ar": updates['full_name_ar']}})
    if 'is_active' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"is_active": updates['is_active']}})
    updated = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    return updated


@router.get("/{employee_id}/profile360")
async def get_profile_360(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    role = user.get('role')
    if role == 'employee':
        own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not own or own['id'] != employee_id:
            raise HTTPException(status_code=403, detail="Access denied")

    leave_entries = await db.leave_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    leave_balance = {}
    for e in leave_entries:
        lt = e['leave_type']
        if lt not in leave_balance:
            leave_balance[lt] = 0
        leave_balance[lt] += e['days'] if e['type'] == 'credit' else -e['days']

    finance_entries = await db.finance_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    attendance_entries = await db.attendance_ledger.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("timestamp", -1).to_list(50)
    warning_entries = await db.warning_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    asset_entries = await db.asset_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    transactions = await db.transactions.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    return {
        "employee": emp,
        "leave_balance": leave_balance,
        "leave_ledger": leave_entries[-20:],
        "finance_ledger": finance_entries[-20:],
        "attendance_ledger": attendance_entries,
        "warning_ledger": warning_entries,
        "asset_ledger": asset_entries,
        "transactions": transactions
    }


@router.get("/{employee_id}/leave-balance")
async def get_leave_balance(employee_id: str, user=Depends(get_current_user)):
    entries = await db.leave_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    balance = {}
    for e in entries:
        lt = e['leave_type']
        if lt not in balance:
            balance[lt] = 0
        balance[lt] += e['days'] if e['type'] == 'credit' else -e['days']
    return balance
