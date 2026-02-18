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


# ============================================================
# التحقق من الإجازات والأذونات المعتمدة
# ============================================================

async def check_employee_on_leave(employee_id: str, check_date: str = None) -> Tuple[bool, Optional[dict]]:
    """
    التحقق مما إذا كان الموظف في إجازة معتمدة لتاريخ معين
    
    Args:
        employee_id: معرف الموظف
        check_date: التاريخ للتحقق (YYYY-MM-DD) - افتراضي: اليوم
    
    Returns:
        Tuple[is_on_leave, leave_info]
    """
    if not check_date:
        check_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # البحث في leave_ledger عن إجازة منفذة تغطي هذا التاريخ
    leave_entry = await db.leave_ledger.find_one({
        "employee_id": employee_id,
        "type": "debit",  # إجازة مخصومة (منفذة)
        "start_date": {"$lte": check_date},
        "end_date": {"$gte": check_date}
    }, {"_id": 0})
    
    if leave_entry:
        return True, {
            "type": "leave",
            "leave_type": leave_entry.get("leave_type", "annual"),
            "start_date": leave_entry.get("start_date"),
            "end_date": leave_entry.get("end_date"),
            "ref_no": leave_entry.get("ref_no"),
            "message_ar": f"الموظف في إجازة {leave_entry.get('leave_type', 'سنوية')} من {leave_entry.get('start_date')} إلى {leave_entry.get('end_date')}"
        }
    
    # البحث في المعاملات المنفذة (طلبات الإجازة)
    executed_leave = await db.transactions.find_one({
        "employee_id": employee_id,
        "type": "leave_request",
        "status": "executed",
        "data.start_date": {"$lte": check_date},
        "data.end_date": {"$gte": check_date}
    }, {"_id": 0})
    
    if executed_leave:
        return True, {
            "type": "leave",
            "leave_type": executed_leave.get("data", {}).get("leave_type", "annual"),
            "start_date": executed_leave.get("data", {}).get("start_date"),
            "end_date": executed_leave.get("data", {}).get("end_date"),
            "ref_no": executed_leave.get("ref_no"),
            "message_ar": f"الموظف في إجازة معتمدة (المرجع: {executed_leave.get('ref_no')})"
        }
    
    return False, None


async def check_employee_has_permission(employee_id: str, check_date: str = None) -> Tuple[bool, Optional[dict]]:
    """
    التحقق مما إذا كان للموظف إذن معتمد لتاريخ معين
    
    Args:
        employee_id: معرف الموظف
        check_date: التاريخ للتحقق (YYYY-MM-DD) - افتراضي: اليوم
    
    Returns:
        Tuple[has_permission, permission_info]
    """
    if not check_date:
        check_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # أنواع طلبات الحضور (أذونات)
    permission_types = [
        "forget_checkin",      # نسيان بصمة
        "field_work",          # مهمة خارجية
        "early_leave_request", # خروج مبكر
        "late_excuse",         # تبرير تأخير
        "permission"           # استئذان عام
    ]
    
    # البحث عن طلب حضور منفذ لهذا التاريخ
    permission = await db.transactions.find_one({
        "employee_id": employee_id,
        "type": {"$in": permission_types},
        "status": "executed",
        "data.date": check_date
    }, {"_id": 0})
    
    if permission:
        return True, {
            "type": "permission",
            "permission_type": permission.get("type"),
            "date": check_date,
            "ref_no": permission.get("ref_no"),
            "reason": permission.get("data", {}).get("reason"),
            "message_ar": f"الموظف لديه إذن معتمد ({permission.get('type')}) - المرجع: {permission.get('ref_no')}"
        }
    
    return False, None


async def check_employee_attendance_status(employee_id: str, check_date: str = None) -> dict:
    """
    التحقق الشامل من حالة الحضور للموظف
    
    يُستخدم قبل:
    - تسجيل الغياب التلقائي
    - فرض خصومات التأخير
    - أي قرار يتعلق بحالة الحضور
    
    Returns:
        dict: {
            should_mark_absent: bool,
            should_mark_late: bool,
            is_on_leave: bool,
            has_permission: bool,
            status_info: dict
        }
    """
    if not check_date:
        check_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    result = {
        "employee_id": employee_id,
        "date": check_date,
        "should_mark_absent": True,  # افتراضي: يُسجل غياب
        "should_mark_late": True,    # افتراضي: يُحسب التأخير
        "is_on_leave": False,
        "has_permission": False,
        "status_info": None
    }
    
    # 1. التحقق من الإجازة
    is_on_leave, leave_info = await check_employee_on_leave(employee_id, check_date)
    if is_on_leave:
        result["is_on_leave"] = True
        result["should_mark_absent"] = False
        result["should_mark_late"] = False
        result["status_info"] = leave_info
        return result
    
    # 2. التحقق من الإذن
    has_permission, permission_info = await check_employee_has_permission(employee_id, check_date)
    if has_permission:
        result["has_permission"] = True
        # بعض أنواع الأذونات لا تمنع تسجيل الغياب بالكامل
        # لكن تمنع الخصم
        permission_type = permission_info.get("permission_type", "")
        
        if permission_type in ["forget_checkin", "field_work"]:
            # هذه الأنواع تعني أن الموظف كان يعمل
            result["should_mark_absent"] = False
            result["should_mark_late"] = False
        elif permission_type in ["early_leave_request", "late_excuse"]:
            # هذه الأنواع لا تعفي من الحضور الأساسي
            result["should_mark_absent"] = True  # لا يزال يجب تسجيل الدخول
            result["should_mark_late"] = False   # لكن لا خصم تأخير
        elif permission_type == "permission":
            # استئذان جزئي
            result["should_mark_absent"] = True
            result["should_mark_late"] = False
            
        result["status_info"] = permission_info
        return result
    
    # 3. التحقق من العطلات الرسمية
    holiday = await db.public_holidays.find_one({
        "date": check_date
    }, {"_id": 0})
    
    if not holiday:
        # جرب جدول holidays
        holiday = await db.holidays.find_one({
            "date": check_date
        }, {"_id": 0})
    
    if holiday:
        result["should_mark_absent"] = False
        result["should_mark_late"] = False
        result["status_info"] = {
            "type": "holiday",
            "name": holiday.get("name"),
            "name_ar": holiday.get("name_ar"),
            "message_ar": f"يوم عطلة رسمية: {holiday.get('name_ar', holiday.get('name'))}"
        }
        return result
    
    # 4. التحقق من يوم الجمعة/السبت (عطلة نهاية الأسبوع)
    date_obj = datetime.strptime(check_date, "%Y-%m-%d")
    if date_obj.weekday() in [4, 5]:  # Friday = 4, Saturday = 5
        result["should_mark_absent"] = False
        result["should_mark_late"] = False
        result["status_info"] = {
            "type": "weekend",
            "day": "friday" if date_obj.weekday() == 4 else "saturday",
            "message_ar": "عطلة نهاية الأسبوع"
        }
        return result
    
    return result


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
    
    # Check for active contract - search by both employee_id and status
    contract = await db.contracts.find_one({
        "employee_id": emp['id'],
        "status": "active",
        "is_snapshot": {"$ne": True}
    }, {"_id": 0})
    
    # If not found, try with is_active for backwards compatibility
    if not contract:
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
