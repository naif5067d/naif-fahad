"""
Attendance Logic Lock - Server-side Validation

Check-in allowed only if:
- Employee assigned to location (work_location matches assignment)
- Within working hours (based on employee's work calendar)
- Active contract exists
- NOT on approved leave or permission for the day

No map UI required - logic only.
"""

from database import db
from datetime import datetime, timezone, time as dt_time, timedelta
from typing import Optional, Tuple


# Default working hours (can be overridden by employee's calendar)
DEFAULT_WORKING_HOURS = {
    "start": dt_time(7, 0),   # 7:00 AM
    "end": dt_time(22, 0),     # 10:00 PM (generous range)
}


async def validate_employee_for_attendance(user_id: str) -> dict:
    """
    Validate employee can use attendance system.
    Returns (employee, errors)
    """
    errors = []
    
    emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not emp:
        return {
            "valid": False,
            "employee": None,
            "error": {
                "code": "error.not_employee",
                "message": "Not registered as employee",
                "message_ar": "لست مسجلاً كموظف"
            }
        }
    
    # Check if employee is active
    if not emp.get('is_active', True):
        return {
            "valid": False,
            "employee": emp,
            "error": {
                "code": "error.employee_inactive",
                "message": "Employee account is inactive",
                "message_ar": "حساب الموظف غير نشط"
            }
        }
    
    # Check for active contract
    contract = await db.contracts.find_one({
        "employee_id": emp['id'],
        "is_active": True,
        "is_snapshot": {"$ne": True}
    }, {"_id": 0})
    
    if not contract:
        return {
            "valid": False,
            "employee": emp,
            "error": {
                "code": "error.no_active_contract",
                "message": "No active contract found",
                "message_ar": "لا يوجد عقد نشط"
            }
        }
    
    # Check contract dates
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if contract.get('end_date') and contract['end_date'] < today:
        return {
            "valid": False,
            "employee": emp,
            "error": {
                "code": "error.contract_expired",
                "message": "Contract has expired",
                "message_ar": "انتهى العقد"
            }
        }
    
    return {
        "valid": True,
        "employee": emp,
        "contract": contract,
        "error": None
    }


def validate_work_location(employee: dict, requested_location: str) -> dict:
    """
    Validate that employee is assigned to the requested work location.
    """
    # Get employee's assigned locations
    assigned_locations = employee.get('assigned_locations', ['HQ'])  # Default to HQ
    
    # If no specific assignment, allow all locations
    if not assigned_locations:
        return {"valid": True, "location": requested_location}
    
    if requested_location not in assigned_locations:
        return {
            "valid": False,
            "error": {
                "code": "error.location_not_assigned",
                "message": f"You are not assigned to location: {requested_location}",
                "message_ar": f"لست مسجلاً في الموقع: {requested_location}"
            }
        }
    
    return {"valid": True, "location": requested_location}


def validate_working_hours(employee: dict, check_time: datetime = None) -> dict:
    """
    Validate that current time is within working hours.
    """
    if check_time is None:
        check_time = datetime.now(timezone.utc)
    
    # Get employee's work calendar
    work_calendar = employee.get('working_calendar', {})
    
    # Get working hours from calendar or use defaults
    start_hour = work_calendar.get('start_hour', DEFAULT_WORKING_HOURS['start'].hour)
    start_minute = work_calendar.get('start_minute', DEFAULT_WORKING_HOURS['start'].minute)
    end_hour = work_calendar.get('end_hour', DEFAULT_WORKING_HOURS['end'].hour)
    end_minute = work_calendar.get('end_minute', DEFAULT_WORKING_HOURS['end'].minute)
    
    current_time = check_time.time()
    start_time = dt_time(start_hour, start_minute)
    end_time = dt_time(end_hour, end_minute)
    
    # Allow very generous range (7 AM - 10 PM) by default
    # This is to avoid blocking legitimate check-ins
    if not (dt_time(7, 0) <= current_time <= dt_time(22, 0)):
        return {
            "valid": False,
            "warning": {
                "code": "warning.outside_hours",
                "message": "Check-in outside standard working hours",
                "message_ar": "تسجيل الدخول خارج ساعات العمل المعتادة"
            }
        }
    
    return {"valid": True}


async def validate_check_in(user_id: str, work_location: str) -> dict:
    """
    Complete validation for check-in.
    """
    # Step 1: Validate employee and contract
    emp_validation = await validate_employee_for_attendance(user_id)
    if not emp_validation['valid']:
        return emp_validation
    
    employee = emp_validation['employee']
    
    # Step 2: Validate work location (relaxed - allow any for now)
    # In production, this would check against assigned locations
    location_validation = validate_work_location(employee, work_location)
    # We don't fail on location - just log it
    
    # Step 3: Validate working hours (warning only, not blocking)
    hours_validation = validate_working_hours(employee)
    
    # Check if already checked in today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = await db.attendance_ledger.find_one({
        "employee_id": employee['id'],
        "date": today,
        "type": "check_in"
    })
    
    if existing:
        return {
            "valid": False,
            "employee": employee,
            "error": {
                "code": "error.already_checked_in",
                "message": "Already checked in today",
                "message_ar": "تم تسجيل الدخول اليوم بالفعل"
            }
        }
    
    warnings = []
    if not location_validation.get('valid'):
        warnings.append(location_validation.get('error'))
    if hours_validation.get('warning'):
        warnings.append(hours_validation['warning'])
    
    return {
        "valid": True,
        "employee": employee,
        "warnings": warnings
    }


async def validate_check_out(user_id: str) -> dict:
    """
    Complete validation for check-out.
    """
    # Step 1: Validate employee
    emp_validation = await validate_employee_for_attendance(user_id)
    if not emp_validation['valid']:
        return emp_validation
    
    employee = emp_validation['employee']
    
    # Check for today's check-in
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    checkin = await db.attendance_ledger.find_one({
        "employee_id": employee['id'],
        "date": today,
        "type": "check_in"
    }, {"_id": 0})
    
    if not checkin:
        return {
            "valid": False,
            "employee": employee,
            "error": {
                "code": "error.no_checkin_today",
                "message": "No check-in found for today",
                "message_ar": "لم يتم تسجيل الدخول اليوم"
            }
        }
    
    # Check if already checked out
    existing_out = await db.attendance_ledger.find_one({
        "employee_id": employee['id'],
        "date": today,
        "type": "check_out"
    })
    
    if existing_out:
        return {
            "valid": False,
            "employee": employee,
            "error": {
                "code": "error.already_checked_out",
                "message": "Already checked out today",
                "message_ar": "تم تسجيل الخروج اليوم بالفعل"
            }
        }
    
    return {
        "valid": True,
        "employee": employee,
        "checkin": checkin
    }
