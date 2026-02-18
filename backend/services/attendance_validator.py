"""
Attendance Validation Service - خدمة التحقق من البصمة

قواعد البصمة:
- البصمة مفتوحة من وقت البداية حتى نهاية فترة السماح
- بعد انتهاء فترة السماح: لا تُقبل بصمة الدخول
- بصمة الخروج مفتوحة حتى نهاية الدوام + فترة السماح
- بعدها تغلق البصمة تماماً
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from database import db


class AttendanceValidator:
    """التحقق من صلاحية البصمة"""
    
    def __init__(self, employee_id: str, work_location_id: str = None):
        self.employee_id = employee_id
        self.work_location_id = work_location_id
        self.work_location = None
    
    async def load_work_location(self):
        """تحميل إعدادات موقع العمل"""
        if self.work_location_id:
            self.work_location = await db.work_locations.find_one(
                {"id": self.work_location_id}, {"_id": 0}
            )
        
        if not self.work_location:
            # إعدادات افتراضية
            self.work_location = {
                "work_start_time": "08:00",
                "work_end_time": "17:00",
                "grace_period_checkin_minutes": 15,
                "grace_period_checkout_minutes": 15
            }
    
    def parse_time(self, time_str: str) -> Tuple[int, int]:
        """تحويل النص إلى ساعة ودقيقة"""
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])
    
    async def validate_checkin(self, current_time: datetime = None) -> Dict:
        """
        التحقق من صلاحية بصمة الدخول
        
        Returns:
            {
                "allowed": bool,
                "reason_ar": str,
                "is_late": bool,
                "late_minutes": int
            }
        """
        await self.load_work_location()
        
        if not current_time:
            current_time = datetime.now(timezone.utc)
        
        # وقت البداية وفترة السماح
        start_hour, start_minute = self.parse_time(self.work_location.get("work_start_time", "08:00"))
        grace_minutes = self.work_location.get("grace_period_checkin_minutes", 15)
        
        # إنشاء وقت البداية لليوم الحالي
        work_start = current_time.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        # آخر وقت مسموح للبصمة (بداية + فترة السماح)
        # بعد هذا الوقت لا تُقبل البصمة
        late_deadline = work_start + timedelta(minutes=grace_minutes)
        
        # الوقت الأقصى المسموح (مثلاً ساعة بعد البداية)
        max_checkin_time = work_start + timedelta(hours=2)
        
        # التحقق
        if current_time > max_checkin_time:
            return {
                "allowed": False,
                "reason_ar": f"انتهى وقت تسجيل الدخول. آخر موعد كان {max_checkin_time.strftime('%H:%M')}",
                "is_late": True,
                "late_minutes": 0
            }
        
        if current_time <= work_start:
            return {
                "allowed": True,
                "reason_ar": "في الوقت المحدد",
                "is_late": False,
                "late_minutes": 0
            }
        
        if current_time <= late_deadline:
            return {
                "allowed": True,
                "reason_ar": "ضمن فترة السماح",
                "is_late": False,
                "late_minutes": 0
            }
        
        # بعد فترة السماح - متأخر
        late_minutes = int((current_time - work_start).total_seconds() / 60)
        return {
            "allowed": True,  # نسمح بالبصمة لكن نسجل التأخير
            "reason_ar": f"تأخير {late_minutes} دقيقة",
            "is_late": True,
            "late_minutes": late_minutes
        }
    
    async def validate_checkout(self, current_time: datetime = None) -> Dict:
        """
        التحقق من صلاحية بصمة الخروج
        
        Returns:
            {
                "allowed": bool,
                "reason_ar": str,
                "is_early": bool,
                "early_minutes": int
            }
        """
        await self.load_work_location()
        
        if not current_time:
            current_time = datetime.now(timezone.utc)
        
        # وقت النهاية وفترة السماح
        end_hour, end_minute = self.parse_time(self.work_location.get("work_end_time", "17:00"))
        grace_minutes = self.work_location.get("grace_period_checkout_minutes", 15)
        
        # إنشاء وقت النهاية لليوم الحالي
        work_end = current_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        # الوقت المسموح للخروج المبكر (نهاية - فترة السماح)
        early_deadline = work_end - timedelta(minutes=grace_minutes)
        
        # آخر وقت مسموح للبصمة (نهاية + فترة السماح)
        late_checkout = work_end + timedelta(minutes=grace_minutes)
        
        # الوقت الأقصى للبصمة (ساعتين بعد النهاية)
        max_checkout_time = work_end + timedelta(hours=2)
        
        if current_time > max_checkout_time:
            return {
                "allowed": False,
                "reason_ar": f"انتهى وقت تسجيل الخروج. آخر موعد كان {max_checkout_time.strftime('%H:%M')}",
                "is_early": False,
                "early_minutes": 0
            }
        
        if current_time >= work_end:
            return {
                "allowed": True,
                "reason_ar": "في الوقت المحدد أو بعده",
                "is_early": False,
                "early_minutes": 0
            }
        
        if current_time >= early_deadline:
            return {
                "allowed": True,
                "reason_ar": "ضمن فترة السماح",
                "is_early": False,
                "early_minutes": 0
            }
        
        # خروج مبكر
        early_minutes = int((work_end - current_time).total_seconds() / 60)
        return {
            "allowed": True,  # نسمح بالبصمة لكن نسجل الخروج المبكر
            "reason_ar": f"خروج مبكر {early_minutes} دقيقة",
            "is_early": True,
            "early_minutes": early_minutes
        }
    
    async def get_attendance_window(self) -> Dict:
        """
        الحصول على نافذة البصمة المسموحة
        
        Returns:
            {
                "checkin_start": str,
                "checkin_end": str,
                "checkout_start": str,
                "checkout_end": str,
                "is_checkin_open": bool,
                "is_checkout_open": bool
            }
        """
        await self.load_work_location()
        
        now = datetime.now(timezone.utc)
        
        # وقت البداية والنهاية
        start_hour, start_minute = self.parse_time(self.work_location.get("work_start_time", "08:00"))
        end_hour, end_minute = self.parse_time(self.work_location.get("work_end_time", "17:00"))
        grace_in = self.work_location.get("grace_period_checkin_minutes", 15)
        grace_out = self.work_location.get("grace_period_checkout_minutes", 15)
        
        work_start = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        work_end = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        
        # نوافذ البصمة
        checkin_start = work_start - timedelta(hours=1)  # ساعة قبل البداية
        checkin_end = work_start + timedelta(hours=2)    # ساعتين بعد البداية
        
        checkout_start = work_end - timedelta(hours=1)   # ساعة قبل النهاية
        checkout_end = work_end + timedelta(hours=2)     # ساعتين بعد النهاية
        
        return {
            "checkin_start": checkin_start.strftime("%H:%M"),
            "checkin_end": checkin_end.strftime("%H:%M"),
            "checkout_start": checkout_start.strftime("%H:%M"),
            "checkout_end": checkout_end.strftime("%H:%M"),
            "is_checkin_open": checkin_start <= now <= checkin_end,
            "is_checkout_open": checkout_start <= now <= checkout_end,
            "work_start": self.work_location.get("work_start_time", "08:00"),
            "work_end": self.work_location.get("work_end_time", "17:00"),
            "grace_checkin": grace_in,
            "grace_checkout": grace_out
        }


async def validate_attendance(employee_id: str, attendance_type: str, work_location_id: str = None) -> Dict:
    """
    دالة مساعدة للتحقق من صلاحية البصمة
    
    Args:
        employee_id: معرف الموظف
        attendance_type: 'check_in' or 'check_out'
        work_location_id: معرف موقع العمل (اختياري)
    """
    validator = AttendanceValidator(employee_id, work_location_id)
    
    if attendance_type == 'check_in':
        return await validator.validate_checkin()
    elif attendance_type == 'check_out':
        return await validator.validate_checkout()
    else:
        return {
            "allowed": False,
            "reason_ar": "نوع البصمة غير صالح"
        }


async def get_attendance_window(employee_id: str, work_location_id: str = None) -> Dict:
    """الحصول على نافذة البصمة المسموحة"""
    validator = AttendanceValidator(employee_id, work_location_id)
    return await validator.get_attendance_window()
