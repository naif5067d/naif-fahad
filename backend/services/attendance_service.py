"""
Attendance Service - الحضور والانضباط
============================================================
- تسجيل الغياب تلقائياً نهاية كل يوم
- إذا لا يوجد check-in ولا إجازة معتمدة = absence
- تسجيل: late, early_leave
- التعديل اليدوي مع audit_log

رمضان:
- عدد الساعات = 6 ساعات
- التفعيل عبر زر إداري
"""

from datetime import datetime, timezone, timedelta, time as dt_time
from typing import Optional, Dict, List
from database import db
import uuid


# ============================================================
# WORKING HOURS CONFIGURATION
# ============================================================

DEFAULT_WORKING_HOURS = {
    "standard": {
        "hours_per_day": 8,
        "start_time": "08:00",
        "end_time": "17:00",
        "break_minutes": 60
    },
    "ramadan": {
        "hours_per_day": 6,
        "start_time": None,  # يُحدد يدوياً حسب القسم
        "end_time": None,
        "break_minutes": 0
    }
}


# ============================================================
# RAMADAN MODE MANAGEMENT
# ============================================================

async def get_ramadan_settings() -> Optional[dict]:
    """جلب إعدادات دوام رمضان"""
    settings = await db.settings.find_one(
        {"type": "ramadan_mode"}, 
        {"_id": 0}
    )
    return settings


async def set_ramadan_mode(start_date: str, end_date: str, actor_id: str) -> dict:
    """
    تفعيل دوام رمضان
    
    Args:
        start_date: تاريخ بداية رمضان
        end_date: تاريخ نهاية رمضان
        actor_id: من قام بالتفعيل
        
    Returns:
        dict: الإعدادات المحدثة
    """
    now = datetime.now(timezone.utc).isoformat()
    
    settings = {
        "type": "ramadan_mode",
        "is_active": True,
        "start_date": start_date,
        "end_date": end_date,
        "hours_per_day": 6,
        "activated_by": actor_id,
        "activated_at": now,
        "updated_at": now
    }
    
    await db.settings.update_one(
        {"type": "ramadan_mode"},
        {"$set": settings},
        upsert=True
    )
    
    return settings


async def deactivate_ramadan_mode(actor_id: str) -> dict:
    """إلغاء تفعيل دوام رمضان"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.settings.update_one(
        {"type": "ramadan_mode"},
        {"$set": {
            "is_active": False,
            "deactivated_by": actor_id,
            "deactivated_at": now,
            "updated_at": now
        }}
    )
    
    return await get_ramadan_settings()


async def is_ramadan_active(date: str = None) -> bool:
    """
    التحقق إذا كان دوام رمضان مفعل للتاريخ المحدد
    
    Args:
        date: التاريخ للتحقق (YYYY-MM-DD)
        
    Returns:
        bool
    """
    settings = await get_ramadan_settings()
    
    if not settings or not settings.get('is_active'):
        return False
    
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    start = settings.get('start_date', '')
    end = settings.get('end_date', '')
    
    return start <= date <= end


async def get_working_hours_for_date(date: str = None) -> dict:
    """
    جلب ساعات العمل للتاريخ المحدد
    
    Args:
        date: التاريخ (YYYY-MM-DD)
        
    Returns:
        dict: إعدادات ساعات العمل
    """
    if await is_ramadan_active(date):
        return {
            **DEFAULT_WORKING_HOURS['ramadan'],
            "mode": "ramadan"
        }
    
    return {
        **DEFAULT_WORKING_HOURS['standard'],
        "mode": "standard"
    }


# ============================================================
# ABSENCE CALCULATION
# ============================================================

async def get_approved_leaves_for_date(date: str) -> List[str]:
    """
    جلب قائمة الموظفين الذين لديهم إجازة معتمدة في تاريخ معين
    
    Args:
        date: التاريخ (YYYY-MM-DD)
        
    Returns:
        list: قائمة employee_ids
    """
    leaves = await db.transactions.find({
        "type": "leave_request",
        "status": "executed",
        "data.start_date": {"$lte": date},
        "data.adjusted_end_date": {"$gte": date}
    }, {"employee_id": 1, "_id": 0}).to_list(5000)
    
    return [l['employee_id'] for l in leaves]


async def calculate_daily_attendance(date: str = None) -> dict:
    """
    حساب الحضور اليومي لجميع الموظفين
    - يُشغّل نهاية كل يوم
    - من لم يسجل دخول ولا عنده إجازة = غياب
    
    Args:
        date: التاريخ (YYYY-MM-DD) - إذا None يستخدم اليوم
        
    Returns:
        dict: ملخص الحضور
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. جلب جميع الموظفين النشطين
    employees = await db.employees.find(
        {"is_active": True}, 
        {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1}
    ).to_list(5000)
    
    # 2. جلب الإجازات المعتمدة لهذا اليوم
    on_leave_ids = set(await get_approved_leaves_for_date(date))
    
    # 3. جلب سجلات الحضور لهذا اليوم
    attendance = await db.attendance_ledger.find(
        {"date": date}, 
        {"_id": 0}
    ).to_list(10000)
    
    checked_in_ids = {a['employee_id'] for a in attendance if a['type'] == 'check_in'}
    checked_out_ids = {a['employee_id'] for a in attendance if a['type'] == 'check_out'}
    
    # 4. جلب سجلات الغياب الموجودة لتجنب التكرار
    existing_absences = await db.attendance_ledger.find(
        {"date": date, "type": "absence"},
        {"employee_id": 1, "_id": 0}
    ).to_list(5000)
    existing_absence_ids = {a['employee_id'] for a in existing_absences}
    
    # 5. تحديد الحالات
    results = {
        "date": date,
        "present": [],
        "absent": [],
        "on_leave": [],
        "late": [],
        "early_leave": [],
        "new_absences_recorded": 0
    }
    
    for emp in employees:
        emp_id = emp['id']
        
        if emp_id in on_leave_ids:
            results['on_leave'].append(emp_id)
        elif emp_id in checked_in_ids:
            results['present'].append(emp_id)
        else:
            # غياب
            results['absent'].append(emp_id)
            
            # تسجيل الغياب إذا لم يكن مسجلاً
            if emp_id not in existing_absence_ids:
                await db.attendance_ledger.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": emp_id,
                    "type": "absence",
                    "date": date,
                    "timestamp": now,
                    "auto_generated": True,
                    "reason": "لم يتم تسجيل الدخول",
                    "reason_en": "No check-in recorded",
                    "settled": False,
                    "audit_log": [{
                        "action": "auto_created",
                        "by": "system",
                        "at": now,
                        "note": "غياب تلقائي - لا يوجد تسجيل دخول"
                    }],
                    "created_at": now
                })
                results['new_absences_recorded'] += 1
    
    results['summary'] = {
        "total_employees": len(employees),
        "present_count": len(results['present']),
        "absent_count": len(results['absent']),
        "on_leave_count": len(results['on_leave'])
    }
    
    return results


# ============================================================
# LATE & EARLY LEAVE DETECTION
# ============================================================

async def check_late_arrival(employee_id: str, check_in_time: str, date: str = None, expected_start: str = None) -> Optional[dict]:
    """
    التحقق من التأخير مع دعم دوام رمضان
    
    Args:
        employee_id: معرف الموظف
        check_in_time: وقت الدخول الفعلي (HH:MM)
        date: التاريخ (YYYY-MM-DD) للتحقق من رمضان
        expected_start: وقت الدخول المتوقع (HH:MM) - إذا None يُحسب من الإعدادات
        
    Returns:
        dict أو None إذا لم يكن متأخراً
    """
    # جلب ساعات العمل للتاريخ (عادي أو رمضان)
    working_hours = await get_working_hours_for_date(date)
    
    # استخدام وقت البداية من الإعدادات أو القيمة المُمررة
    if expected_start is None:
        expected_start = working_hours.get('start_time') or "08:00"
    
    actual = datetime.strptime(check_in_time, "%H:%M")
    expected = datetime.strptime(expected_start, "%H:%M")
    
    if actual > expected:
        diff = actual - expected
        minutes_late = diff.seconds // 60
        
        return {
            "is_late": True,
            "expected_time": expected_start,
            "actual_time": check_in_time,
            "minutes_late": minutes_late,
            "hours_late": minutes_late // 60,
            "remaining_minutes": minutes_late % 60,
            "working_mode": working_hours.get('mode', 'standard'),
            "hours_per_day": working_hours.get('hours_per_day', 8)
        }
    
    return None


async def check_early_leave(employee_id: str, check_out_time: str, date: str = None, expected_end: str = None) -> Optional[dict]:
    """
    التحقق من المغادرة المبكرة مع دعم دوام رمضان
    
    Args:
        employee_id: معرف الموظف
        check_out_time: وقت الخروج الفعلي (HH:MM)
        date: التاريخ (YYYY-MM-DD) للتحقق من رمضان
        expected_end: وقت الخروج المتوقع (HH:MM) - إذا None يُحسب من الإعدادات
        
    Returns:
        dict أو None إذا لم يكن مغادرة مبكرة
    """
    # جلب ساعات العمل للتاريخ (عادي أو رمضان)
    working_hours = await get_working_hours_for_date(date)
    
    # استخدام وقت النهاية من الإعدادات أو القيمة المُمررة
    if expected_end is None:
        expected_end = working_hours.get('end_time') or "17:00"
    
    actual = datetime.strptime(check_out_time, "%H:%M")
    expected = datetime.strptime(expected_end, "%H:%M")
    
    if actual < expected:
        diff = expected - actual
        minutes_early = diff.seconds // 60
        
        return {
            "is_early": True,
            "expected_time": expected_end,
            "actual_time": check_out_time,
            "minutes_early": minutes_early,
            "hours_early": minutes_early // 60,
            "remaining_minutes": minutes_early % 60,
            "working_mode": working_hours.get('mode', 'standard'),
            "hours_per_day": working_hours.get('hours_per_day', 8)
        }
    
    return None


async def record_late_arrival(employee_id: str, date: str, minutes_late: int, actor_id: str = "system") -> dict:
    """
    تسجيل التأخير في السجل
    
    Args:
        employee_id: معرف الموظف
        date: التاريخ
        minutes_late: دقائق التأخير
        actor_id: من سجل
        
    Returns:
        dict: السجل المنشأ
    """
    now = datetime.now(timezone.utc).isoformat()
    
    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "type": "late",
        "date": date,
        "timestamp": now,
        "minutes": minutes_late,
        "auto_generated": actor_id == "system",
        "settled": False,
        "audit_log": [{
            "action": "created",
            "by": actor_id,
            "at": now,
            "note": f"تأخير {minutes_late} دقيقة"
        }],
        "created_at": now
    }
    
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    
    return entry


async def record_early_leave(employee_id: str, date: str, minutes_early: int, actor_id: str = "system") -> dict:
    """
    تسجيل المغادرة المبكرة في السجل
    
    Args:
        employee_id: معرف الموظف
        date: التاريخ
        minutes_early: دقائق المغادرة المبكرة
        actor_id: من سجل
        
    Returns:
        dict: السجل المنشأ
    """
    now = datetime.now(timezone.utc).isoformat()
    
    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "type": "early_leave",
        "date": date,
        "timestamp": now,
        "minutes": minutes_early,
        "auto_generated": actor_id == "system",
        "settled": False,
        "audit_log": [{
            "action": "created",
            "by": actor_id,
            "at": now,
            "note": f"مغادرة مبكرة {minutes_early} دقيقة"
        }],
        "created_at": now
    }
    
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    
    return entry


# ============================================================
# MANUAL MODIFICATION WITH AUDIT
# ============================================================

async def modify_attendance_record(
    record_id: str, 
    modification: dict, 
    actor_id: str, 
    reason: str
) -> dict:
    """
    تعديل سجل حضور يدوياً مع تسجيل Audit
    
    Args:
        record_id: معرف السجل
        modification: التعديلات
        actor_id: من قام بالتعديل
        reason: سبب التعديل
        
    Returns:
        dict: السجل المحدث
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # جلب السجل الحالي
    record = await db.attendance_ledger.find_one({"id": record_id}, {"_id": 0})
    if not record:
        return None
    
    # بناء audit entry
    audit_entry = {
        "action": "modified",
        "by": actor_id,
        "at": now,
        "reason": reason,
        "changes": modification,
        "previous_values": {k: record.get(k) for k in modification.keys()}
    }
    
    # تحديث السجل
    update = {
        "$set": {
            **modification,
            "manual_override": True,
            "updated_at": now
        },
        "$push": {
            "audit_log": audit_entry
        }
    }
    
    await db.attendance_ledger.update_one({"id": record_id}, update)
    
    updated = await db.attendance_ledger.find_one({"id": record_id}, {"_id": 0})
    return updated


async def delete_absence_record(record_id: str, actor_id: str, reason: str) -> dict:
    """
    حذف سجل غياب (تحويله لملغي مع الحفاظ على السجل)
    
    Args:
        record_id: معرف السجل
        actor_id: من قام بالحذف
        reason: سبب الحذف
        
    Returns:
        dict: السجل المحدث
    """
    return await modify_attendance_record(
        record_id=record_id,
        modification={"type": "cancelled_absence", "cancelled": True},
        actor_id=actor_id,
        reason=reason
    )


# ============================================================
# ATTENDANCE SUMMARY
# ============================================================

async def get_employee_attendance_summary(employee_id: str, start_date: str = None, end_date: str = None) -> dict:
    """
    ملخص حضور الموظف
    
    Args:
        employee_id: معرف الموظف
        start_date: من تاريخ (YYYY-MM-DD)
        end_date: إلى تاريخ (YYYY-MM-DD)
        
    Returns:
        dict: ملخص الحضور
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    
    query = {
        "employee_id": employee_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }
    
    entries = await db.attendance_ledger.find(query, {"_id": 0}).to_list(5000)
    
    summary = {
        "employee_id": employee_id,
        "period": {"from": start_date, "to": end_date},
        "check_ins": 0,
        "check_outs": 0,
        "absences": 0,
        "late_arrivals": 0,
        "early_leaves": 0,
        "total_late_minutes": 0,
        "total_early_minutes": 0,
        "unsettled_absences": 0
    }
    
    for entry in entries:
        entry_type = entry.get('type')
        
        if entry_type == 'check_in':
            summary['check_ins'] += 1
        elif entry_type == 'check_out':
            summary['check_outs'] += 1
        elif entry_type == 'absence' and not entry.get('cancelled'):
            summary['absences'] += 1
            if not entry.get('settled'):
                summary['unsettled_absences'] += 1
        elif entry_type == 'late':
            summary['late_arrivals'] += 1
            summary['total_late_minutes'] += entry.get('minutes', 0)
        elif entry_type == 'early_leave':
            summary['early_leaves'] += 1
            summary['total_early_minutes'] += entry.get('minutes', 0)
    
    return summary


async def get_unsettled_absences(employee_id: str) -> List[dict]:
    """
    جلب الغياب غير المسوى للموظف
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        list: قائمة سجلات الغياب
    """
    absences = await db.attendance_ledger.find({
        "employee_id": employee_id,
        "type": "absence",
        "settled": {"$ne": True},
        "cancelled": {"$ne": True}
    }, {"_id": 0}).to_list(1000)
    
    return absences


# ============================================================
# ATTENDANCE REQUEST TYPES
# ============================================================

ATTENDANCE_REQUEST_TYPES = {
    "forget_checkin": {
        "name_ar": "نسيان بصمة",
        "name_en": "Forgot Check-in",
        "workflow": ["supervisor", "ops", "stas"]
    },
    "field_work": {
        "name_ar": "مهمة خارجية",
        "name_en": "Field Work",
        "workflow": ["supervisor", "ops", "stas"]
    },
    "early_leave_request": {
        "name_ar": "طلب خروج مبكر",
        "name_en": "Early Leave Request",
        "workflow": ["supervisor", "ops", "stas"]
    },
    "late_excuse": {
        "name_ar": "تبرير تأخير",
        "name_en": "Late Excuse",
        "workflow": ["supervisor", "ops", "stas"]
    }
}
