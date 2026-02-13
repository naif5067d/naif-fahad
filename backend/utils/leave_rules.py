"""
Leave Rule Engine - Pre-Validation
All validation happens BEFORE transaction creation.

Reject if:
- leave_days_requested > leave_balance
- overlapping dates exist with any pending or executed leave
- employee is inactive or has no active contract

Auto adjustments:
- If official holiday inside leave → extend leave (already implemented)
- If sick leave exceeds tier → convert to next tier automatically
"""

from database import db
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional


# Sick leave tier configuration
SICK_LEAVE_TIERS = [
    {"days": 30, "pay": 100, "name": "full_pay"},
    {"days": 60, "pay": 75, "name": "three_quarter_pay"},
    {"days": 30, "pay": 50, "name": "half_pay"},
    {"days": float('inf'), "pay": 0, "name": "unpaid"}
]


async def get_employee_with_contract(user_id: str) -> Tuple[Optional[dict], Optional[dict], list]:
    """
    Get employee record with active contract validation.
    Returns (employee, contract, errors)
    """
    errors = []
    
    emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not emp:
        errors.append({
            "code": "error.not_employee",
            "message": "You are not registered as an employee",
            "message_ar": "لست مسجلاً كموظف"
        })
        return None, None, errors
    
    # Check if employee is active
    if not emp.get('is_active', True):
        errors.append({
            "code": "error.employee_inactive",
            "message": "Employee account is inactive",
            "message_ar": "حساب الموظف غير نشط"
        })
        return emp, None, errors
    
    # Check for active contract
    contract = await db.contracts.find_one({
        "employee_id": emp['id'],
        "is_active": True,
        "is_snapshot": {"$ne": True}
    }, {"_id": 0})
    
    if not contract:
        errors.append({
            "code": "error.no_active_contract",
            "message": "No active contract found. Leave cannot be requested.",
            "message_ar": "لا يوجد عقد نشط. لا يمكن طلب إجازة."
        })
        return emp, None, errors
    
    # Check contract dates
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if contract.get('end_date') and contract['end_date'] < today:
        errors.append({
            "code": "error.contract_expired",
            "message": "Contract has expired. Please contact HR.",
            "message_ar": "انتهت صلاحية العقد. يرجى التواصل مع الموارد البشرية."
        })
        return emp, contract, errors
    
    return emp, contract, errors


async def get_leave_balance(employee_id: str, leave_type: str) -> int:
    """Calculate current leave balance for an employee"""
    entries = await db.leave_ledger.find(
        {"employee_id": employee_id, "leave_type": leave_type}, {"_id": 0}
    ).to_list(1000)
    
    balance = 0
    for entry in entries:
        if entry.get('type') == 'credit':
            balance += entry.get('days', 0)
        else:  # debit
            balance -= entry.get('days', 0)
    
    return balance


async def check_date_overlap(employee_id: str, start_date: str, end_date: str, exclude_tx_id: str = None) -> Optional[dict]:
    """
    Check if the requested leave dates overlap with any existing leave.
    Checks both pending and executed transactions.
    """
    query = {
        "employee_id": employee_id,
        "type": "leave_request",
        "status": {"$nin": ["rejected"]},  # Check pending AND executed
        "$or": [
            # Case 1: Existing leave starts during requested period
            {"data.start_date": {"$gte": start_date, "$lte": end_date}},
            # Case 2: Existing leave ends during requested period
            {"data.adjusted_end_date": {"$gte": start_date, "$lte": end_date}},
            # Case 3: Existing leave completely contains requested period
            {"$and": [
                {"data.start_date": {"$lte": start_date}},
                {"data.adjusted_end_date": {"$gte": end_date}}
            ]}
        ]
    }
    
    if exclude_tx_id:
        query["id"] = {"$ne": exclude_tx_id}
    
    overlapping = await db.transactions.find_one(query, {"_id": 0})
    return overlapping


async def get_all_holidays() -> list:
    """Get all holidays (system + manual)"""
    system_holidays = await db.public_holidays.find({}, {"_id": 0}).to_list(500)
    manual_holidays = await db.holidays.find({}, {"_id": 0}).to_list(500)
    
    return [h['date'] for h in system_holidays] + [h['date'] for h in manual_holidays]


def count_working_days(start_str: str, end_str: str, holidays: list, saturday_working: bool = False) -> int:
    """Count working days between two dates, excluding weekends and holidays"""
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    holiday_set = set(holidays)
    
    count = 0
    current = start
    while current <= end:
        day_of_week = current.weekday()
        date_str = current.strftime("%Y-%m-%d")
        
        is_friday = day_of_week == 4
        is_saturday = day_of_week == 5
        is_holiday = date_str in holiday_set
        
        if not is_friday and not is_holiday:
            if is_saturday and not saturday_working:
                pass  # Skip Saturday if not a working day
            else:
                count += 1
        
        current += timedelta(days=1)
    
    return count


def extend_leave_for_holidays(start_str: str, working_days_needed: int, holidays: list, saturday_working: bool = False) -> str:
    """
    Calculate the actual end date to cover the requested working days.
    If holidays fall within the leave period, extend the end date.
    """
    start = datetime.strptime(start_str, "%Y-%m-%d")
    holiday_set = set(holidays)
    
    counted = 0
    current = start
    max_iterations = 365  # Safety limit
    
    while counted < working_days_needed and max_iterations > 0:
        day_of_week = current.weekday()
        date_str = current.strftime("%Y-%m-%d")
        
        is_friday = day_of_week == 4
        is_saturday = day_of_week == 5
        is_holiday = date_str in holiday_set
        
        if not is_friday and not is_holiday:
            if is_saturday and not saturday_working:
                pass
            else:
                counted += 1
        
        if counted < working_days_needed:
            current += timedelta(days=1)
        max_iterations -= 1
    
    return current.strftime("%Y-%m-%d")


async def get_sick_leave_usage(employee_id: str, year: int = None) -> dict:
    """
    Get sick leave usage breakdown by tier for the year.
    Used to determine next tier for auto-conversion.
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    
    # Get all sick leave debits for the year
    entries = await db.leave_ledger.find({
        "employee_id": employee_id,
        "leave_type": "sick",
        "type": "debit",
        "date": {"$gte": year_start, "$lte": year_end}
    }, {"_id": 0}).to_list(1000)
    
    total_used = sum(e.get('days', 0) for e in entries)
    
    # Determine current tier
    remaining = total_used
    usage_by_tier = {}
    current_tier = 0
    
    for i, tier in enumerate(SICK_LEAVE_TIERS):
        tier_limit = tier['days']
        if remaining > 0:
            used_in_tier = min(remaining, tier_limit) if tier_limit != float('inf') else remaining
            usage_by_tier[tier['name']] = used_in_tier
            remaining -= used_in_tier
            if remaining > 0:
                current_tier = i + 1
    
    return {
        "total_used": total_used,
        "usage_by_tier": usage_by_tier,
        "current_tier_index": current_tier,
        "current_tier_name": SICK_LEAVE_TIERS[min(current_tier, len(SICK_LEAVE_TIERS) - 1)]['name']
    }


async def validate_leave_request(
    employee: dict,
    leave_type: str,
    start_date: str,
    end_date: str,
    exclude_tx_id: str = None
) -> dict:
    """
    Complete validation of a leave request.
    Returns validation result with errors or adjusted values.
    """
    errors = []
    warnings = []
    
    employee_id = employee['id']
    saturday_working = employee.get('working_calendar', {}).get('saturday_working', False)
    
    # Get holidays
    holidays = await get_all_holidays()
    
    # Calculate working days
    working_days = count_working_days(start_date, end_date, holidays, saturday_working)
    
    if working_days <= 0:
        errors.append({
            "code": "error.no_working_days",
            "message": "No working days in the selected period",
            "message_ar": "لا توجد أيام عمل في الفترة المحددة"
        })
        return {"valid": False, "errors": errors}
    
    # Check balance
    balance = await get_leave_balance(employee_id, leave_type)
    
    if working_days > balance:
        errors.append({
            "code": "error.insufficient_balance",
            "message": f"Insufficient {leave_type} leave balance. Available: {balance}, Requested: {working_days}",
            "message_ar": f"رصيد إجازات {leave_type} غير كافٍ. المتاح: {balance}، المطلوب: {working_days}"
        })
        return {"valid": False, "errors": errors}
    
    # Check date overlap
    overlapping = await check_date_overlap(employee_id, start_date, end_date, exclude_tx_id)
    
    if overlapping:
        errors.append({
            "code": "error.date_overlap",
            "message": f"Leave dates overlap with existing request {overlapping['ref_no']}",
            "message_ar": f"تتعارض تواريخ الإجازة مع الطلب {overlapping['ref_no']}"
        })
        return {"valid": False, "errors": errors}
    
    # Calculate adjusted end date (extending for holidays within period)
    adjusted_end_date = extend_leave_for_holidays(start_date, working_days, holidays, saturday_working)
    
    # Special handling for sick leave tiers
    sick_tier_info = None
    if leave_type == 'sick':
        sick_usage = await get_sick_leave_usage(employee_id)
        sick_tier_info = sick_usage
        
        # Add warning if moving to lower pay tier
        if sick_usage['current_tier_index'] > 0:
            current_tier = SICK_LEAVE_TIERS[sick_usage['current_tier_index']]
            warnings.append({
                "code": "warning.sick_tier",
                "message": f"Sick leave at {current_tier['pay']}% pay tier ({current_tier['name']})",
                "message_ar": f"الإجازة المرضية بنسبة {current_tier['pay']}% من الراتب"
            })
    
    return {
        "valid": True,
        "working_days": working_days,
        "adjusted_end_date": adjusted_end_date,
        "balance_before": balance,
        "balance_after": balance - working_days,
        "warnings": warnings,
        "sick_tier_info": sick_tier_info
    }
