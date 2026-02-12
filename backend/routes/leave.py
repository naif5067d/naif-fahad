from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from utils.auth import get_current_user
from routes.transactions import get_next_ref_no, skip_supervisor_stage, WORKFLOW_MAP
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix="/api/leave", tags=["leave"])


class LeaveRequest(BaseModel):
    leave_type: str  # annual, sick, emergency
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    reason: str


def count_working_days(start_str, end_str, holidays, saturday_working=False):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    holiday_dates = set(holidays)
    count = 0
    current = start
    while current <= end:
        day_of_week = current.weekday()
        date_str = current.strftime("%Y-%m-%d")
        is_friday = day_of_week == 4
        is_saturday = day_of_week == 5
        is_holiday = date_str in holiday_dates
        if not is_friday and not is_holiday:
            if is_saturday and not saturday_working:
                pass
            else:
                count += 1
        current += timedelta(days=1)
    return count


def extend_leave_for_holidays(start_str, end_str, holidays, saturday_working=False):
    requested_working_days = count_working_days(start_str, end_str, holidays, saturday_working)
    start = datetime.strptime(start_str, "%Y-%m-%d")
    holiday_dates = set(holidays)
    actual_end = start
    counted = 0
    current = start
    max_iterations = 365
    i = 0
    while counted < requested_working_days and i < max_iterations:
        day_of_week = current.weekday()
        date_str = current.strftime("%Y-%m-%d")
        is_friday = day_of_week == 4
        is_saturday = day_of_week == 5
        is_holiday = date_str in holiday_dates
        if not is_friday and not is_holiday:
            if is_saturday and not saturday_working:
                pass
            else:
                counted += 1
                actual_end = current
        current += timedelta(days=1)
        i += 1
    return actual_end.strftime("%Y-%m-%d"), requested_working_days


@router.post("/request")
async def create_leave_request(req: LeaveRequest, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="You are not registered as an employee")

    holidays_list = await db.public_holidays.find({}, {"_id": 0}).to_list(100)
    holiday_dates = [h['date'] for h in holidays_list]

    sat_working = emp.get('working_calendar', {}).get('saturday_working', False)
    adjusted_end, working_days = extend_leave_for_holidays(
        req.start_date, req.end_date, holiday_dates, sat_working
    )

    entries = await db.leave_ledger.find(
        {"employee_id": emp['id'], "leave_type": req.leave_type}, {"_id": 0}
    ).to_list(1000)
    current_balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in entries)

    if working_days > current_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient {req.leave_type} leave balance. Available: {current_balance}, Requested: {working_days}"
        )

    ref_no = await get_next_ref_no()
    base_workflow = WORKFLOW_MAP["leave_request"][:]
    workflow = skip_supervisor_stage(base_workflow, emp)
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "leave_request",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": emp['id'],
        "data": {
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "adjusted_end_date": adjusted_end,
            "working_days": working_days,
            "reason": req.reason,
            "employee_name": emp['full_name'],
            "balance_before": current_balance,
            "balance_after": current_balance - working_days,
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Leave request: {req.leave_type}, {working_days} working days",
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


@router.get("/balance")
async def get_my_leave_balance(user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="Not an employee")
    entries = await db.leave_ledger.find({"employee_id": emp['id']}, {"_id": 0}).to_list(1000)
    balance = {}
    for e in entries:
        lt = e['leave_type']
        if lt not in balance:
            balance[lt] = 0
        balance[lt] += e['days'] if e['type'] == 'credit' else -e['days']
    return balance


@router.get("/holidays")
async def get_holidays():
    holidays = await db.public_holidays.find({}, {"_id": 0}).to_list(100)
    return holidays
