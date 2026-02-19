"""
Punch Validator Service - التحقق من البصمة
============================================================
يتحقق من:
1. فترة السماح - رفض التبصيم بعدها
2. دائرة GPS - رفض التبصيم خارجها
3. موقع العمل المُعيّن للموظف

القواعد:
- لا يُقبل تسجيل الدخول بعد (وقت_البداية + فترة_السماح + 30 دقيقة إضافية كحد أقصى)
- لا يُقبل التبصيم إذا كان الموظف خارج دائرة الموقع
- يجب أن يكون الموظف مُعيّن في موقع العمل
- المستخدمين المُعفَين يمكنهم التبصيم في أي وقت
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from database import db
import math

# توقيت الرياض
RIYADH_TZ = ZoneInfo("Asia/Riyadh")

# الحد الأقصى للتأخير المسموح (بعد فترة السماح) - دقائق
MAX_LATE_MINUTES_AFTER_GRACE = 120  # ساعتين كحد أقصى بعد وقت البداية + السماح

# نصف قطر دائرة التبصيم بالكيلومتر
DEFAULT_GEOFENCE_RADIUS_KM = 0.5  # 500 متر

# الحد الأقصى للتبصيم المبكر قبل بداية الدوام (دقائق) - افتراضي 0 = لا تبصيم قبل الدوام
DEFAULT_EARLY_CHECKIN_MINUTES = 0  # لا يُسمح بالتبصيم المبكر افتراضياً
MAX_ALLOWED_EARLY_CHECKIN_MINUTES = 120  # الحد الأقصى ساعتين للمخولين

# المستخدمين المُعفَين من قواعد التبصيم
EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF', 'EMP-SULTAN']


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
    """الحصول على موقع عمل الموظف"""
    # البحث في work_locations عن الموقع المُعيّن للموظف
    location = await db.work_locations.find_one(
        {
            "assigned_employees": employee_id,
            "is_active": True
        },
        {"_id": 0}
    )
    return location


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
        
        # === رفض التبصيم المتأخر جداً ===
        # حد التسجيل = وقت البداية + السماح + الحد الأقصى
        max_checkin_time = work_start + timedelta(minutes=grace_checkin + MAX_LATE_MINUTES_AFTER_GRACE)
        
        if local_time > max_checkin_time:
            return {
                "valid": False,
                "error": {
                    "code": "error.checkin_closed",
                    "message": f"Check-in closed. Maximum allowed time was {max_checkin_time.strftime('%H:%M')}",
                    "message_ar": f"انتهى وقت تسجيل الدخول. الحد الأقصى كان {max_checkin_time.strftime('%H:%M')}",
                    "work_start": work_start_str,
                    "grace_minutes": grace_checkin,
                    "max_late_minutes": MAX_LATE_MINUTES_AFTER_GRACE
                },
                "work_location": work_location
            }
        
        # تحذير إذا متأخر (بعد وقت البداية + السماح)
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
    gps_available: bool = True
) -> dict:
    """
    التحقق من موقع التبصيم (GPS)
    
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
    
    # الحصول على موقع العمل
    work_location = await get_employee_work_location(employee_id)
    
    if not work_location:
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
    
    # الحصول على إحداثيات الموقع
    location_lat = work_location.get('latitude')
    location_lng = work_location.get('longitude')
    # radius_meters أو geofence_radius_km
    radius_meters = work_location.get('radius_meters', 500)
    geofence_radius = radius_meters / 1000  # تحويل إلى كيلومتر
    
    if location_lat is None or location_lng is None:
        # موقع العمل بدون إحداثيات - السماح مع تحذير
        return {
            "valid": True,
            "warning": {
                "code": "warning.no_location_coords",
                "message": "Work location has no GPS coordinates configured",
                "message_ar": "موقع العمل ليس له إحداثيات محددة"
            },
            "gps_valid": True,  # نسمح لأن الموقع غير مُعد
            "distance_km": None,
            "work_location": work_location
        }
    
    # حساب المسافة
    distance = haversine_distance(latitude, longitude, location_lat, location_lng)
    gps_valid = distance <= geofence_radius
    
    if not gps_valid:
        return {
            "valid": False,
            "error": {
                "code": "error.outside_geofence",
                "message": f"You are {distance*1000:.0f}m away from work location. Maximum allowed is {geofence_radius*1000:.0f}m",
                "message_ar": f"أنت على بُعد {distance*1000:.0f} متر من موقع العمل. الحد المسموح {geofence_radius*1000:.0f} متر",
                "distance_meters": round(distance * 1000),
                "allowed_meters": round(geofence_radius * 1000),
                "work_location_name": work_location.get('name_ar', work_location.get('name'))
            },
            "gps_valid": False,
            "distance_km": round(distance, 3),
            "work_location": work_location
        }
    
    return {
        "valid": True,
        "error": None,
        "gps_valid": True,
        "distance_km": round(distance, 3),
        "work_location": work_location
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
    التحقق الكامل من التبصيم
    
    Returns:
        {
            "valid": bool,
            "errors": List[dict],
            "warnings": List[dict],
            "work_location": Optional[dict],
            "gps_valid": bool,
            "distance_km": Optional[float]
        }
    """
    errors = []
    warnings = []
    work_location = None
    gps_valid = False
    distance_km = None
    
    # === فحص الإعفاء - المستخدمين المُعفَين يمكنهم التبصيم في أي وقت ومكان ===
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
            "is_exempt": True
        }
    
    # 1. التحقق من الوقت
    time_result = await validate_punch_time(employee_id, punch_type, current_time)
    work_location = time_result.get('work_location')
    
    if not time_result['valid']:
        errors.append(time_result['error'])
    elif time_result.get('warning'):
        warnings.append(time_result['warning'])
    
    # 2. التحقق من الموقع (GPS) - إذا لم يكن تجاوز
    if not bypass_gps:
        location_result = await validate_punch_location(
            employee_id, latitude, longitude, gps_available
        )
        
        gps_valid = location_result.get('gps_valid', False)
        distance_km = location_result.get('distance_km')
        
        if not location_result['valid']:
            errors.append(location_result['error'])
        elif location_result.get('warning'):
            warnings.append(location_result['warning'])
        
        # تحديث work_location من نتيجة GPS إذا وجد
        if location_result.get('work_location'):
            work_location = location_result['work_location']
    else:
        gps_valid = True  # تم تجاوز GPS
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "work_location": work_location,
        "gps_valid": gps_valid,
        "distance_km": distance_km
    }
