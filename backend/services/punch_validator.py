"""
Punch Validator Service - التحقق من البصمة
============================================================
يتحقق من:
1. هل الموظف في وضع التجربة (sandbox)؟
2. هل اليوم يوم عمل للموظف (من work_locations.work_days)؟
3. هل اليوم عطلة رسمية؟
4. هل الموظف في إجازة معتمدة؟
5. فترة السماح - رفض التبصيم قبل الوقت المسموح
6. دائرة GPS - رفض التبصيم خارجها
7. موقع العمل المُعيّن للموظف

القواعد:
- لا يُقبل التبصيم إذا الموظف في وضع التجربة (sandbox_mode)
- لا يُقبل التبصيم في أيام العطلة حسب work_days
- لا يُقبل التبصيم في العطلات الرسمية
- لا يُقبل التبصيم إذا الموظف في إجازة معتمدة
- لا يُقبل التبصيم إذا كان الموظف خارج دائرة الموقع
- المستخدمين المُعفَين يمكنهم التبصيم في أي وقت
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from database import db
import math

# توقيت الرياض
RIYADH_TZ = ZoneInfo("Asia/Riyadh")

# أسماء الأيام بالإنجليزية (لمطابقة work_days)
WEEKDAY_NAMES = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

# الحد الأقصى للتأخير المسموح (بعد فترة السماح) - دقائق
MAX_LATE_MINUTES_AFTER_GRACE = 120  # ساعتين كحد أقصى بعد وقت البداية + السماح

# نصف قطر دائرة التبصيم بالكيلومتر
DEFAULT_GEOFENCE_RADIUS_KM = 0.5  # 500 متر

# الحد الأقصى للتبصيم المبكر قبل بداية الدوام (دقائق) - افتراضي 0 = لا تبصيم قبل الدوام
DEFAULT_EARLY_CHECKIN_MINUTES = 0  # لا يُسمح بالتبصيم المبكر افتراضياً
MAX_ALLOWED_EARLY_CHECKIN_MINUTES = 120  # الحد الأقصى ساعتين للمخولين

# المستخدمين المُعفَين من قواعد التبصيم
# المدراء التنفيذيين ومسؤول النظام - ليسوا موظفين عاديين
# سلطان موظف ومدير عمليات - يُطبق عليه النظام
EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF']

# الأدوار المُعفاة من قواعد الحضور
# محمد (التنفيذي) + صلاح (المحاسب) + نايف (الاستراتيجي) + stas (النظام)
EXEMPT_ROLES = ['stas', 'mohammed', 'salah', 'naif']


# ============================================================
# فحوصات ما قبل التبصيم الجديدة
# ============================================================

async def check_employee_sandbox_mode(employee_id: str) -> dict:
    """
    التحقق إذا كان الموظف في وضع التجربة (sandbox)
    
    وضع التجربة يعني:
    - الموظف يمكنه دخول النظام
    - يمكنه إصدار طلبات تجريبية
    - لكن لا يُحتسب له حضور أو غياب
    - لا تصل طلباته للإدارة
    
    Returns:
        {
            "is_sandbox": bool,
            "work_start_date": str or None,
            "message_ar": str
        }
    """
    # البحث في العقد النشط للموظف
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0, "sandbox_mode": 1, "work_start_date": 1, "start_date": 1})
    
    if not contract:
        # لا يوجد عقد نشط - ربما في وضع التجربة
        return {
            "is_sandbox": True,
            "work_start_date": None,
            "reason": "no_active_contract",
            "message_ar": "لا يوجد عقد نشط - النظام في وضع التجربة"
        }
    
    # فحص وضع التجربة الصريح
    if contract.get("sandbox_mode", False):
        work_start = contract.get("work_start_date")
        return {
            "is_sandbox": True,
            "work_start_date": work_start,
            "reason": "sandbox_mode_active",
            "message_ar": f"النظام في وضع التجربة. تاريخ المباشرة: {work_start or 'غير محدد'}"
        }
    
    # فحص تاريخ المباشرة
    work_start_date = contract.get("work_start_date") or contract.get("start_date")
    if work_start_date:
        today = datetime.now(RIYADH_TZ).strftime("%Y-%m-%d")
        if work_start_date > today:
            return {
                "is_sandbox": True,
                "work_start_date": work_start_date,
                "reason": "work_not_started",
                "message_ar": f"لم يحن تاريخ المباشرة بعد ({work_start_date})"
            }
    
    return {
        "is_sandbox": False,
        "work_start_date": work_start_date,
        "message_ar": "الموظف في وضع العمل الرسمي"
    }


async def check_work_day(employee_id: str, check_date: datetime = None) -> dict:
    """
    التحقق إذا كان اليوم يوم عمل للموظف
    
    يستعلم من: work_locations.work_days
    
    Returns:
        {
            "is_work_day": bool,
            "day_name": str,
            "day_name_ar": str,
            "error": Optional[dict]
        }
    """
    if check_date is None:
        check_date = datetime.now(RIYADH_TZ)
    
    # اسم اليوم بالإنجليزية
    day_index = check_date.weekday()  # 0=Monday, 6=Sunday
    day_name = WEEKDAY_NAMES[day_index]
    
    # أسماء الأيام بالعربية
    day_names_ar = {
        'monday': 'الاثنين',
        'tuesday': 'الثلاثاء',
        'wednesday': 'الأربعاء',
        'thursday': 'الخميس',
        'friday': 'الجمعة',
        'saturday': 'السبت',
        'sunday': 'الأحد'
    }
    day_name_ar = day_names_ar.get(day_name, day_name)
    
    # جلب موقع العمل للموظف
    work_location = await get_employee_work_location(employee_id)
    
    if not work_location:
        # لا يوجد موقع عمل - نسمح بالتبصيم مع تحذير
        return {
            "is_work_day": True,
            "day_name": day_name,
            "day_name_ar": day_name_ar,
            "warning": {
                "code": "warning.no_work_location",
                "message_ar": "لم يتم تعيين موقع عمل للموظف"
            }
        }
    
    # فحص أيام العمل
    work_days = work_location.get("work_days", {})
    
    if not work_days:
        # لا توجد أيام عمل محددة - نسمح بالتبصيم
        return {
            "is_work_day": True,
            "day_name": day_name,
            "day_name_ar": day_name_ar,
            "work_location": work_location
        }
    
    # التحقق من يوم العمل
    is_work_day = work_days.get(day_name, True)  # افتراضي: يوم عمل
    
    if not is_work_day:
        return {
            "is_work_day": False,
            "day_name": day_name,
            "day_name_ar": day_name_ar,
            "work_location": work_location,
            "error": {
                "code": "error.not_work_day",
                "message": f"Today ({day_name}) is not a work day",
                "message_ar": f"اليوم ({day_name_ar}) ليس يوم عمل في موقعك",
                "work_location_name": work_location.get("name_ar", "")
            }
        }
    
    return {
        "is_work_day": True,
        "day_name": day_name,
        "day_name_ar": day_name_ar,
        "work_location": work_location
    }


async def check_public_holiday(check_date: str = None) -> dict:
    """
    التحقق إذا كان اليوم عطلة رسمية
    
    يستعلم من: public_holidays + holidays
    
    Returns:
        {
            "is_holiday": bool,
            "holiday_name": str or None,
            "holiday_name_ar": str or None
        }
    """
    if check_date is None:
        check_date = datetime.now(RIYADH_TZ).strftime("%Y-%m-%d")
    
    # البحث في public_holidays
    holiday = await db.public_holidays.find_one({"date": check_date}, {"_id": 0})
    
    if not holiday:
        # البحث في holidays
        holiday = await db.holidays.find_one({"date": check_date}, {"_id": 0})
    
    if holiday:
        return {
            "is_holiday": True,
            "holiday_name": holiday.get("name"),
            "holiday_name_ar": holiday.get("name_ar") or holiday.get("name"),
            "error": {
                "code": "error.public_holiday",
                "message": f"Today is a public holiday: {holiday.get('name')}",
                "message_ar": f"اليوم عطلة رسمية: {holiday.get('name_ar') or holiday.get('name')}"
            }
        }
    
    return {
        "is_holiday": False,
        "holiday_name": None,
        "holiday_name_ar": None
    }


async def check_employee_on_leave_for_punch(employee_id: str, check_date: str = None) -> dict:
    """
    التحقق إذا كان الموظف في إجازة معتمدة
    
    يستعلم من: transactions + leave_ledger
    
    Returns:
        {
            "is_on_leave": bool,
            "leave_type": str or None,
            "end_date": str or None,
            "error": Optional[dict]
        }
    """
    if check_date is None:
        check_date = datetime.now(RIYADH_TZ).strftime("%Y-%m-%d")
    
    # البحث في المعاملات المنفذة
    leave = await db.transactions.find_one({
        "employee_id": employee_id,
        "type": "leave_request",
        "status": "executed",
        "data.start_date": {"$lte": check_date},
        "data.end_date": {"$gte": check_date}
    }, {"_id": 0, "data": 1, "ref_no": 1})
    
    if leave:
        leave_data = leave.get("data", {})
        leave_type = leave_data.get("leave_type", "annual")
        leave_types_ar = {
            "annual": "سنوية",
            "sick": "مرضية",
            "emergency": "اضطرارية",
            "unpaid": "بدون راتب",
            "maternity": "أمومة",
            "paternity": "أبوة",
            "hajj": "حج",
            "marriage": "زواج",
            "death": "وفاة"
        }
        leave_type_ar = leave_types_ar.get(leave_type, leave_type)
        
        return {
            "is_on_leave": True,
            "leave_type": leave_type,
            "leave_type_ar": leave_type_ar,
            "end_date": leave_data.get("end_date") or leave_data.get("adjusted_end_date"),
            "ref_no": leave.get("ref_no"),
            "error": {
                "code": "error.employee_on_leave",
                "message": f"You are on {leave_type} leave until {leave_data.get('end_date')}",
                "message_ar": f"أنت في إجازة {leave_type_ar} حتى {leave_data.get('end_date')}"
            }
        }
    
    # البحث في leave_ledger
    leave_entry = await db.leave_ledger.find_one({
        "employee_id": employee_id,
        "type": "debit",
        "start_date": {"$lte": check_date},
        "end_date": {"$gte": check_date}
    }, {"_id": 0})
    
    if leave_entry:
        leave_type = leave_entry.get("leave_type", "annual")
        return {
            "is_on_leave": True,
            "leave_type": leave_type,
            "end_date": leave_entry.get("end_date"),
            "error": {
                "code": "error.employee_on_leave",
                "message": f"You are on leave until {leave_entry.get('end_date')}",
                "message_ar": f"أنت في إجازة حتى {leave_entry.get('end_date')}"
            }
        }
    
    return {
        "is_on_leave": False,
        "leave_type": None,
        "end_date": None
    }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """حساب المسافة بالكيلومتر بين نقطتين"""
    R = 6371  # نصف قطر الأرض بالكيلومتر
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


async def get_employee_work_location(employee_id: str) -> Optional[dict]:
    """الحصول على موقع عمل الموظف - يرجع الموقع الأول"""
    location = await db.work_locations.find_one(
        {
            "assigned_employees": employee_id,
            "is_active": True
        },
        {"_id": 0}
    )
    return location


async def get_all_employee_work_locations(employee_id: str) -> list:
    """الحصول على جميع مواقع العمل المعينة للموظف"""
    locations = await db.work_locations.find(
        {
            "assigned_employees": employee_id,
            "is_active": True
        },
        {"_id": 0}
    ).to_list(100)
    return locations


async def validate_punch_time(
    employee_id: str,
    punch_type: str,  # 'checkin' أو 'checkout'
    current_time: datetime = None
) -> dict:
    """
    التحقق من وقت التبصيم
    
    Returns:
        {
            "valid": bool,
            "error": Optional[dict],
            "warning": Optional[dict],
            "work_location": Optional[dict]
        }
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # تحويل إلى توقيت الرياض
    local_time = current_time.astimezone(RIYADH_TZ)
    today = local_time.strftime("%Y-%m-%d")
    
    # الحصول على موقع العمل
    work_location = await get_employee_work_location(employee_id)
    
    if not work_location:
        # لا يوجد موقع مُعيّن - استخدام الافتراضي
        work_location = {
            "name_ar": "افتراضي",
            "work_start": "08:00",
            "work_end": "17:00",
            "grace_checkin_minutes": 15,
            "grace_checkout_minutes": 15,
            "daily_hours": 8
        }
    
    # قراءة أوقات العمل
    work_start_str = work_location.get('work_start', '08:00')
    work_end_str = work_location.get('work_end', '17:00')
    grace_checkin = work_location.get('grace_checkin_minutes', 15)
    grace_checkout = work_location.get('grace_checkout_minutes', 15)
    
    # تحويل أوقات العمل
    work_start = datetime.strptime(f"{today} {work_start_str}", "%Y-%m-%d %H:%M")
    work_start = work_start.replace(tzinfo=RIYADH_TZ)
    
    work_end = datetime.strptime(f"{today} {work_end_str}", "%Y-%m-%d %H:%M")
    work_end = work_end.replace(tzinfo=RIYADH_TZ)
    
    if punch_type == 'checkin':
        # === قراءة إعداد السماح بالتبصيم المبكر من موقع العمل ===
        # افتراضي = 0 (لا تبصيم قبل الدوام)
        # المخولين يمكنهم تفعيله حتى 120 دقيقة (ساعتين)
        allow_early_minutes = work_location.get('allow_early_checkin_minutes', DEFAULT_EARLY_CHECKIN_MINUTES)
        
        # التأكد من عدم تجاوز الحد الأقصى
        allow_early_minutes = min(allow_early_minutes, MAX_ALLOWED_EARLY_CHECKIN_MINUTES)
        
        # === قاعدة: رفض التبصيم قبل الوقت المسموح ===
        min_checkin_time = work_start - timedelta(minutes=allow_early_minutes)
        
        if local_time < min_checkin_time:
            if allow_early_minutes == 0:
                # لا يوجد سماح - يجب التبصيم في وقت الدوام فقط
                return {
                    "valid": False,
                    "error": {
                        "code": "error.checkin_too_early",
                        "message": f"Check-in opens at work start time: {work_start_str}",
                        "message_ar": f"التبصيم يفتح مع بداية الدوام الساعة {work_start_str}",
                        "work_start": work_start_str,
                        "current_time": local_time.strftime('%H:%M')
                    },
                    "work_location": work_location
                }
            else:
                # يوجد سماح لكن الموظف أبكر منه
                return {
                    "valid": False,
                    "error": {
                        "code": "error.checkin_too_early",
                        "message": f"Check-in opens at {min_checkin_time.strftime('%H:%M')}",
                        "message_ar": f"التبصيم يفتح الساعة {min_checkin_time.strftime('%H:%M')}",
                        "work_start": work_start_str,
                        "opens_at": min_checkin_time.strftime('%H:%M'),
                        "early_allowed_minutes": allow_early_minutes,
                        "current_time": local_time.strftime('%H:%M')
                    },
                    "work_location": work_location
                }
        
        # === تسجيل التأخير بدون رفض ===
        # الموظف يستطيع التبصيم في أي وقت لكن يُسجل التأخير
        grace_deadline = work_start + timedelta(minutes=grace_checkin)
        
        if local_time > grace_deadline:
            late_minutes = int((local_time - work_start).total_seconds() / 60)
            return {
                "valid": True,
                "warning": {
                    "code": "warning.late_checkin",
                    "message": f"You are {late_minutes} minutes late",
                    "message_ar": f"أنت متأخر {late_minutes} دقيقة",
                    "late_minutes": late_minutes
                },
                "work_location": work_location
            }
    
    elif punch_type == 'checkout':
        # حد التسجيل للخروج المبكر = وقت البداية + ساعة واحدة على الأقل
        min_checkout_time = work_start + timedelta(hours=1)
        
        if local_time < min_checkout_time:
            return {
                "valid": False,
                "error": {
                    "code": "error.checkout_too_early",
                    "message": f"Cannot checkout before {min_checkout_time.strftime('%H:%M')}",
                    "message_ar": f"لا يمكن تسجيل الخروج قبل {min_checkout_time.strftime('%H:%M')}",
                    "min_checkout_time": min_checkout_time.strftime('%H:%M')
                },
                "work_location": work_location
            }
        
        # تحذير إذا خروج مبكر
        early_deadline = work_end - timedelta(minutes=grace_checkout)
        if local_time < early_deadline:
            early_minutes = int((work_end - local_time).total_seconds() / 60)
            return {
                "valid": True,
                "warning": {
                    "code": "warning.early_checkout",
                    "message": f"Early checkout by {early_minutes} minutes",
                    "message_ar": f"خروج مبكر بـ {early_minutes} دقيقة",
                    "early_minutes": early_minutes
                },
                "work_location": work_location
            }
    
    return {
        "valid": True,
        "error": None,
        "warning": None,
        "work_location": work_location
    }


async def validate_punch_location(
    employee_id: str,
    latitude: float,
    longitude: float,
    gps_available: bool = True,
    selected_location_id: str = None
) -> dict:
    """
    التحقق من موقع التبصيم (GPS)
    يدعم الموظفين المعينين في مواقع متعددة
    
    Returns:
        {
            "valid": bool,
            "error": Optional[dict],
            "distance_km": float,
            "gps_valid": bool,
            "work_location": Optional[dict]
        }
    """
    if not gps_available or latitude is None or longitude is None:
        return {
            "valid": False,
            "error": {
                "code": "error.gps_required",
                "message": "GPS location is required for check-in",
                "message_ar": "يجب تفعيل الموقع للتبصيم"
            },
            "gps_valid": False,
            "distance_km": None,
            "work_location": None
        }
    
    # الحصول على جميع مواقع العمل للموظف
    all_locations = await get_all_employee_work_locations(employee_id)
    
    if not all_locations:
        return {
            "valid": False,
            "error": {
                "code": "error.no_work_location",
                "message": "Employee not assigned to any work location",
                "message_ar": "الموظف غير مُعيّن في أي موقع عمل"
            },
            "gps_valid": False,
            "distance_km": None,
            "work_location": None
        }
    
    # إذا تم تحديد موقع معين - نتحقق منه فقط
    if selected_location_id:
        selected_loc = next((loc for loc in all_locations if loc.get('id') == selected_location_id), None)
        if selected_loc:
            all_locations = [selected_loc]
    
    # البحث في جميع المواقع عن موقع صالح
    best_location = None
    best_distance = float('inf')
    
    for work_location in all_locations:
        location_lat = work_location.get('latitude')
        location_lng = work_location.get('longitude')
        radius_meters = work_location.get('radius_meters', 500)
        geofence_radius = radius_meters / 1000  # تحويل إلى كيلومتر
        
        if location_lat is None or location_lng is None:
            # موقع العمل بدون إحداثيات - نسمح به مع تحذير
            return {
                "valid": True,
                "warning": {
                    "code": "warning.no_location_coords",
                    "message": "Work location has no GPS coordinates configured",
                    "message_ar": "موقع العمل ليس له إحداثيات محددة"
                },
                "gps_valid": True,
                "distance_km": None,
                "work_location": work_location
            }
        
        # حساب المسافة
        distance = haversine_distance(latitude, longitude, location_lat, location_lng)
        
        # إذا كان ضمن النطاق - نجحت
        if distance <= geofence_radius:
            return {
                "valid": True,
                "error": None,
                "gps_valid": True,
                "distance_km": round(distance, 3),
                "work_location": work_location
            }
        
        # حفظ أقرب موقع للرسالة الخطأ
        if distance < best_distance:
            best_distance = distance
            best_location = work_location
    
    # لم يُعثر على موقع صالح - نرجع أقرب موقع
    if best_location:
        radius_meters = best_location.get('radius_meters', 500)
        return {
            "valid": False,
            "error": {
                "code": "error.outside_geofence",
                "message": f"You are {best_distance*1000:.0f}m away from work location. Maximum allowed is {radius_meters}m",
                "message_ar": f"أنت على بُعد {best_distance*1000:.0f} متر من موقع العمل. الحد المسموح {radius_meters} متر",
                "distance_meters": round(best_distance * 1000),
                "allowed_meters": radius_meters,
                "work_location_name": best_location.get('name_ar', best_location.get('name')),
                "all_locations_count": len(all_locations)
            },
            "gps_valid": False,
            "distance_km": round(best_distance, 3),
            "work_location": best_location
        }
    
    return {
        "valid": False,
        "error": {
            "code": "error.no_valid_location",
            "message": "Could not validate location",
            "message_ar": "تعذر التحقق من الموقع"
        },
        "gps_valid": False,
        "distance_km": None,
        "work_location": None
    }


async def validate_full_punch(
    employee_id: str,
    punch_type: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    gps_available: bool = False,
    current_time: datetime = None,
    bypass_gps: bool = False  # للمدراء - تجاوز GPS
) -> dict:
    """
    التحقق الكامل من التبصيم - النسخة المحسنة
    
    ترتيب الفحوصات:
    1. هل الموظف معفى (إداري)؟
    2. هل الموظف في وضع التجربة (sandbox)؟
    3. هل اليوم يوم عمل (من work_locations.work_days)؟
    4. هل اليوم عطلة رسمية؟
    5. هل الموظف في إجازة معتمدة؟
    6. هل الوقت ضمن ساعات العمل؟
    7. هل الموقع صحيح (GPS)؟
    
    ملاحظة مهمة للخروج (checkout):
    - إذا سجل الموظف دخوله بـ GPS صالح، يُسمح له بالخروج حتى بدون GPS
    
    Returns:
        {
            "valid": bool,
            "errors": List[dict],
            "warnings": List[dict],
            "work_location": Optional[dict],
            "gps_valid": bool,
            "distance_km": Optional[float],
            "is_sandbox": bool
        }
    """
    errors = []
    warnings = []
    work_location = None
    gps_valid = False
    distance_km = None
    
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    local_time = current_time.astimezone(RIYADH_TZ)
    today_str = local_time.strftime("%Y-%m-%d")
    
    # ============================================================
    # فحص 1: الإعفاء - المستخدمين المُعفَين يمكنهم التبصيم في أي وقت
    # ============================================================
    # فحص بواسطة employee_id
    if employee_id in EXEMPT_EMPLOYEE_IDS:
        return {
            "valid": True,
            "errors": [],
            "warnings": [{
                "code": "info.exempt_employee",
                "message": "Admin user - exempt from attendance rules",
                "message_ar": "مستخدم إداري - مُعفى من قواعد الحضور"
            }],
            "work_location": None,
            "gps_valid": True,
            "distance_km": None,
            "is_exempt": True,
            "is_sandbox": False
        }
    
    # فحص بواسطة الدور - جلب دور المستخدم من الموظف
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "user_id": 1})
    if employee:
        user = await db.users.find_one({"id": employee.get("user_id")}, {"_id": 0, "role": 1})
        if user and user.get("role") in EXEMPT_ROLES:
            return {
                "valid": True,
                "errors": [],
                "warnings": [{
                    "code": "info.exempt_employee",
                    "message": "Admin user - exempt from attendance rules",
                    "message_ar": "مستخدم إداري - مُعفى من قواعد الحضور"
                }],
                "work_location": None,
                "gps_valid": True,
                "distance_km": None,
                "is_exempt": True,
                "is_sandbox": False
            }
    
    # ============================================================
    # فحص 2: وضع التجربة (Sandbox) - للموظفين الجدد قبل المباشرة
    # ============================================================
    sandbox_check = await check_employee_sandbox_mode(employee_id)
    if sandbox_check.get("is_sandbox"):
        return {
            "valid": False,
            "errors": [{
                "code": "error.sandbox_mode",
                "message": sandbox_check.get("message_ar"),
                "message_ar": sandbox_check.get("message_ar"),
                "work_start_date": sandbox_check.get("work_start_date"),
                "reason": sandbox_check.get("reason")
            }],
            "warnings": [],
            "work_location": None,
            "gps_valid": False,
            "distance_km": None,
            "is_sandbox": True
        }
    
    # ============================================================
    # فحص 3: هل اليوم يوم عمل؟ (من work_locations.work_days)
    # ============================================================
    work_day_check = await check_work_day(employee_id, local_time)
    work_location = work_day_check.get("work_location")
    
    if not work_day_check.get("is_work_day"):
        return {
            "valid": False,
            "errors": [work_day_check.get("error")],
            "warnings": [],
            "work_location": work_location,
            "gps_valid": False,
            "distance_km": None,
            "is_sandbox": False,
            "day_info": {
                "day_name": work_day_check.get("day_name"),
                "day_name_ar": work_day_check.get("day_name_ar")
            }
        }
    
    if work_day_check.get("warning"):
        warnings.append(work_day_check["warning"])
    
    # ============================================================
    # فحص 4: هل اليوم عطلة رسمية؟
    # ============================================================
    holiday_check = await check_public_holiday(today_str)
    if holiday_check.get("is_holiday"):
        return {
            "valid": False,
            "errors": [holiday_check.get("error")],
            "warnings": [],
            "work_location": work_location,
            "gps_valid": False,
            "distance_km": None,
            "is_sandbox": False,
            "holiday_info": {
                "name": holiday_check.get("holiday_name"),
                "name_ar": holiday_check.get("holiday_name_ar")
            }
        }
    
    # ============================================================
    # فحص 5: هل الموظف في إجازة معتمدة؟
    # ============================================================
    leave_check = await check_employee_on_leave_for_punch(employee_id, today_str)
    if leave_check.get("is_on_leave"):
        return {
            "valid": False,
            "errors": [leave_check.get("error")],
            "warnings": [],
            "work_location": work_location,
            "gps_valid": False,
            "distance_km": None,
            "is_sandbox": False,
            "leave_info": {
                "type": leave_check.get("leave_type"),
                "type_ar": leave_check.get("leave_type_ar"),
                "end_date": leave_check.get("end_date")
            }
        }
    
    # ============================================================
    # للخروج: التحقق إذا كان الدخول تم بـ GPS صالح
    # ============================================================
    checkout_bypass_gps = False
    if punch_type == 'checkout' and not bypass_gps:
        checkin_record = await db.attendance_ledger.find_one({
            "employee_id": employee_id,
            "date": today_str,
            "type": "check_in"
        }, {"_id": 0, "gps_valid": 1, "work_location": 1, "work_location_id": 1})
        
        if checkin_record:
            if checkin_record.get('gps_valid') or checkin_record.get('work_location_id'):
                checkout_bypass_gps = True
                if checkin_record.get('work_location_id'):
                    work_location = await db.work_locations.find_one(
                        {"id": checkin_record['work_location_id']},
                        {"_id": 0}
                    )
    
    # ============================================================
    # فحص 6: التحقق من الوقت
    # ============================================================
    time_result = await validate_punch_time(employee_id, punch_type, current_time)
    if not work_location:
        work_location = time_result.get('work_location')
    
    if not time_result['valid']:
        errors.append(time_result['error'])
    elif time_result.get('warning'):
        warnings.append(time_result['warning'])
    
    # ============================================================
    # فحص 7: التحقق من الموقع (GPS)
    # ============================================================
    should_bypass_gps = bypass_gps or checkout_bypass_gps
    
    if not should_bypass_gps:
        location_result = await validate_punch_location(
            employee_id, latitude, longitude, gps_available
        )
        
        gps_valid = location_result.get('gps_valid', False)
        distance_km = location_result.get('distance_km')
        
        if not location_result['valid']:
            errors.append(location_result['error'])
        elif location_result.get('warning'):
            warnings.append(location_result['warning'])
        
        if location_result.get('work_location'):
            work_location = location_result['work_location']
    else:
        gps_valid = True
        if checkout_bypass_gps and not gps_available:
            warnings.append({
                "code": "info.checkout_gps_bypassed",
                "message": "GPS check bypassed for checkout (check-in was GPS validated)",
                "message_ar": "تم تجاوز فحص GPS للخروج (الدخول كان مُصدّقاً)"
            })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "work_location": work_location,
        "gps_valid": gps_valid,
        "distance_km": distance_km,
        "is_sandbox": False
    }
