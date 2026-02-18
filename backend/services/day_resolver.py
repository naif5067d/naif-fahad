"""
Day Resolver Service - محرك القرار اليومي
يحدد الحالة النهائية لكل موظف في كل يوم

ترتيب القرار (إجباري):
1. العطل الرسمية
2. عطلة نهاية الأسبوع حسب موقع العمل
3. إجازة منفذة
4. مهمة خارجية منفذة
5. نسيان بصمة منفذ
6. بصمة فعلية وتحليل التأخير والخروج
7. استئذان جزئي منفذ
8. خلاف ذلك = غياب
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from database import db
from models.daily_status import DailyStatusEnum, LockStatus, STATUS_AR


class DayResolver:
    """محرك القرار اليومي"""
    
    def __init__(self, employee_id: str, date: str):
        self.employee_id = employee_id
        self.date = date
        self.employee = None
        self.contract = None
        self.work_location = None
        
    async def resolve(self) -> dict:
        """
        تحليل اليوم وإرجاع القرار النهائي
        """
        # تحميل بيانات الموظف
        await self._load_employee_data()
        
        if not self.employee:
            return self._create_error("الموظف غير موجود")
        
        if not self.contract:
            return self._create_error("لا يوجد عقد نشط")
        
        # تنفيذ سلسلة القرارات بالترتيب
        
        # 1. فحص العطل الرسمية
        result = await self._check_holidays()
        if result:
            return result
        
        # 2. فحص عطلة نهاية الأسبوع
        result = await self._check_weekend()
        if result:
            return result
        
        # 3. فحص الإجازات المنفذة
        result = await self._check_leaves()
        if result:
            return result
        
        # 4. فحص المهمات الخارجية المنفذة
        result = await self._check_missions()
        if result:
            return result
        
        # 5. فحص نسيان البصمة المنفذ
        result = await self._check_forgotten_punch()
        if result:
            return result
        
        # 6. فحص البصمة الفعلية وتحليل التأخير
        result = await self._check_attendance()
        if result:
            return result
        
        # 7. فحص الاستئذان الجزئي المنفذ
        result = await self._check_permissions()
        if result:
            return result
        
        # 8. خلاف ذلك = غياب
        return self._create_absent_result()
    
    async def _load_employee_data(self):
        """تحميل بيانات الموظف والعقد"""
        self.employee = await db.employees.find_one(
            {"id": self.employee_id}, 
            {"_id": 0}
        )
        
        if self.employee:
            # البحث عن العقد النشط
            self.contract = await db.contracts.find_one({
                "employee_id": self.employee_id,
                "$or": [
                    {"status": "active"},
                    {"is_active": True}
                ]
            }, {"_id": 0})
            
            if not self.contract:
                self.contract = await db.contracts_v2.find_one({
                    "employee_id": self.employee_id,
                    "status": "active",
                    "is_active": True
                }, {"_id": 0})
            
            # تحميل موقع العمل
            work_location_id = self.employee.get('work_location_id') or self.contract.get('work_location_id') if self.contract else None
            if work_location_id:
                self.work_location = await db.work_locations.find_one(
                    {"id": work_location_id}, 
                    {"_id": 0}
                )
    
    async def _check_holidays(self) -> Optional[dict]:
        """1. فحص العطل الرسمية"""
        holiday = await db.holidays.find_one({
            "date": self.date,
            "is_active": {"$ne": False}
        }, {"_id": 0})
        
        if holiday:
            return self._create_result(
                status=DailyStatusEnum.HOLIDAY,
                reason="عطلة رسمية",
                reason_ar=f"عطلة رسمية: {holiday.get('name_ar', holiday.get('name', ''))}",
                source="holiday",
                holiday_id=holiday.get('id')
            )
        return None
    
    async def _check_weekend(self) -> Optional[dict]:
        """2. فحص عطلة نهاية الأسبوع"""
        date_obj = datetime.strptime(self.date, "%Y-%m-%d")
        day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
        
        # الحصول على أيام العطلة من موقع العمل أو الافتراضي
        weekend_days = [4, 5]  # الجمعة والسبت افتراضياً
        
        if self.work_location:
            weekend_days = self.work_location.get('weekend_days', [4, 5])
        
        if day_of_week in weekend_days:
            day_names = {0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 
                        3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}
            return self._create_result(
                status=DailyStatusEnum.WEEKEND,
                reason="عطلة نهاية أسبوع",
                reason_ar=f"عطلة نهاية الأسبوع ({day_names.get(day_of_week, '')})",
                source="weekend"
            )
        return None
    
    async def _check_leaves(self) -> Optional[dict]:
        """3. فحص الإجازات المنفذة"""
        leave = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "leave_request",
            "status": "executed",
            "start_date": {"$lte": self.date},
            "end_date": {"$gte": self.date}
        }, {"_id": 0})
        
        if leave:
            leave_type = leave.get('leave_type', 'annual')
            leave_type_ar = {
                'annual': 'سنوية',
                'sick': 'مرضية',
                'emergency': 'اضطرارية',
                'unpaid': 'بدون راتب',
                'admin': 'إدارية'
            }.get(leave_type, leave_type)
            
            status = DailyStatusEnum.ON_ADMIN_LEAVE if leave_type == 'admin' else DailyStatusEnum.ON_LEAVE
            
            return self._create_result(
                status=status,
                reason=f"إجازة {leave_type_ar}",
                reason_ar=f"إجازة {leave_type_ar} منفذة",
                source="leave",
                leave_id=leave.get('id')
            )
        return None
    
    async def _check_missions(self) -> Optional[dict]:
        """4. فحص المهمات الخارجية المنفذة"""
        mission = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "mission",
            "status": "executed",
            "start_date": {"$lte": self.date},
            "end_date": {"$gte": self.date}
        }, {"_id": 0})
        
        if mission:
            return self._create_result(
                status=DailyStatusEnum.ON_MISSION,
                reason="مهمة خارجية",
                reason_ar=f"مهمة خارجية: {mission.get('destination', '')}",
                source="mission",
                mission_id=mission.get('id')
            )
        return None
    
    async def _check_forgotten_punch(self) -> Optional[dict]:
        """5. فحص نسيان البصمة المنفذ"""
        forgotten = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "forgotten_punch",
            "status": "executed",
            "date": self.date
        }, {"_id": 0})
        
        if forgotten:
            # نسيان البصمة يعتبر حضور
            return self._create_result(
                status=DailyStatusEnum.PRESENT,
                reason="نسيان بصمة معتمد",
                reason_ar="نسيان بصمة تم اعتماده",
                source="forgotten_punch",
                check_in_time=forgotten.get('claimed_check_in'),
                check_out_time=forgotten.get('claimed_check_out')
            )
        return None
    
    async def _check_attendance(self) -> Optional[dict]:
        """6. فحص البصمة الفعلية وتحليل التأخير والخروج"""
        # جلب بصمة الدخول
        check_in = await db.attendance_ledger.find_one({
            "employee_id": self.employee_id,
            "date": self.date,
            "type": "check_in"
        }, {"_id": 0})
        
        if not check_in:
            return None  # لا توجد بصمة، ننتقل للخطوة التالية
        
        # جلب بصمة الخروج
        check_out = await db.attendance_ledger.find_one({
            "employee_id": self.employee_id,
            "date": self.date,
            "type": "check_out"
        }, {"_id": 0})
        
        # تحليل الأوقات
        analysis = await self._analyze_attendance(check_in, check_out)
        
        # تحديد الحالة
        status = DailyStatusEnum.PRESENT
        reason_parts = []
        
        if analysis['is_late']:
            # فحص وجود تبرير
            excuse = await db.transactions.find_one({
                "employee_id": self.employee_id,
                "type": "late_excuse",
                "status": "executed",
                "date": self.date
            }, {"_id": 0})
            
            if excuse:
                status = DailyStatusEnum.LATE_EXCUSED
                reason_parts.append("تأخير معذور")
            else:
                status = DailyStatusEnum.LATE
                reason_parts.append(f"تأخير {analysis['late_minutes']} دقيقة")
        
        if analysis['is_early_leave']:
            # فحص وجود تبرير
            excuse = await db.transactions.find_one({
                "employee_id": self.employee_id,
                "type": "early_leave_excuse",
                "status": "executed",
                "date": self.date
            }, {"_id": 0})
            
            if excuse:
                if status == DailyStatusEnum.PRESENT:
                    status = DailyStatusEnum.EARLY_EXCUSED
                reason_parts.append("خروج مبكر معذور")
            else:
                if status == DailyStatusEnum.PRESENT:
                    status = DailyStatusEnum.EARLY_LEAVE
                reason_parts.append(f"خروج مبكر {analysis['early_leave_minutes']} دقيقة")
        
        if not reason_parts:
            reason_parts.append("حضور كامل")
        
        return self._create_result(
            status=status,
            reason=" + ".join(reason_parts),
            reason_ar=" + ".join(reason_parts),
            source="attendance",
            check_in_time=check_in.get('timestamp'),
            check_out_time=check_out.get('timestamp') if check_out else None,
            actual_hours=analysis['actual_hours'],
            required_hours=analysis['required_hours'],
            late_minutes=analysis['late_minutes'],
            early_leave_minutes=analysis['early_leave_minutes'],
            attendance_ids=[check_in.get('id')] + ([check_out.get('id')] if check_out else [])
        )
    
    async def _analyze_attendance(self, check_in: dict, check_out: Optional[dict]) -> dict:
        """تحليل بيانات الحضور"""
        # ساعات العمل الافتراضية
        work_start = "08:00"
        work_end = "17:00"
        required_hours = 8.0
        grace_period_in = 15  # دقائق سماح للدخول
        grace_period_out = 15  # دقائق سماح للخروج
        
        # من موقع العمل - تصحيح أسماء الحقول
        if self.work_location:
            # work_start أو work_start_time
            work_start = self.work_location.get('work_start') or self.work_location.get('work_start_time', '08:00')
            work_end = self.work_location.get('work_end') or self.work_location.get('work_end_time', '17:00')
            required_hours = self.work_location.get('daily_hours', 8.0)
            # grace_checkin_minutes أو grace_period_checkin_minutes
            grace_period_in = self.work_location.get('grace_checkin_minutes') or self.work_location.get('grace_period_checkin_minutes', 15)
            grace_period_out = self.work_location.get('grace_checkout_minutes') or self.work_location.get('grace_period_checkout_minutes', 15)
        
        # تحليل وقت الدخول
        check_in_time = datetime.fromisoformat(check_in['timestamp'].replace('Z', '+00:00'))
        work_start_time = datetime.strptime(f"{self.date} {work_start}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        
        late_minutes = 0
        is_late = False
        allowed_late = work_start_time + timedelta(minutes=grace_period_in)
        
        if check_in_time > allowed_late:
            late_minutes = int((check_in_time - work_start_time).total_seconds() / 60)
            is_late = True
        
        # تحليل وقت الخروج
        early_leave_minutes = 0
        is_early_leave = False
        actual_hours = 0.0
        
        if check_out:
            check_out_time = datetime.fromisoformat(check_out['timestamp'].replace('Z', '+00:00'))
            work_end_time = datetime.strptime(f"{self.date} {work_end}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            allowed_early = work_end_time - timedelta(minutes=grace_period_out)
            
            if check_out_time < allowed_early:
                early_leave_minutes = int((work_end_time - check_out_time).total_seconds() / 60)
                is_early_leave = True
            
            actual_hours = (check_out_time - check_in_time).total_seconds() / 3600
        
        return {
            'is_late': is_late,
            'late_minutes': late_minutes,
            'is_early_leave': is_early_leave,
            'early_leave_minutes': early_leave_minutes,
            'actual_hours': round(actual_hours, 2),
            'required_hours': required_hours,
            'work_start_used': work_start,
            'work_end_used': work_end,
            'grace_in_used': grace_period_in,
            'grace_out_used': grace_period_out
        }
    
    async def _check_permissions(self) -> Optional[dict]:
        """7. فحص الاستئذان الجزئي المنفذ"""
        permission = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "permission",
            "status": "executed",
            "date": self.date
        }, {"_id": 0})
        
        if permission:
            hours = permission.get('hours', 0)
            return self._create_result(
                status=DailyStatusEnum.PERMISSION,
                reason=f"استئذان {hours} ساعات",
                reason_ar=f"استئذان {hours} ساعات",
                source="permission",
                permission_id=permission.get('id'),
                permission_hours=hours
            )
        return None
    
    def _create_absent_result(self) -> dict:
        """8. إنشاء نتيجة الغياب"""
        return self._create_result(
            status=DailyStatusEnum.ABSENT,
            reason="غياب بدون عذر",
            reason_ar="غياب - لا توجد إجازة أو مهمة أو بصمة أو عطلة",
            source="absent"
        )
    
    def _create_result(self, status: DailyStatusEnum, reason: str, reason_ar: str, 
                       source: str, **kwargs) -> dict:
        """إنشاء نتيجة القرار"""
        now = datetime.now(timezone.utc)
        lock_deadline = (now + timedelta(hours=48)).isoformat()
        
        return {
            "id": str(uuid.uuid4()),
            "employee_id": self.employee_id,
            "date": self.date,
            "final_status": status.value,
            "status_ar": STATUS_AR.get(status, status.value),
            "decision_reason": reason,
            "decision_reason_ar": reason_ar,
            "decision_source": source,
            "check_in_time": kwargs.get('check_in_time'),
            "check_out_time": kwargs.get('check_out_time'),
            "actual_hours": kwargs.get('actual_hours'),
            "required_hours": kwargs.get('required_hours'),
            "late_minutes": kwargs.get('late_minutes', 0),
            "early_leave_minutes": kwargs.get('early_leave_minutes', 0),
            "permission_hours": kwargs.get('permission_hours', 0),
            "leave_id": kwargs.get('leave_id'),
            "mission_id": kwargs.get('mission_id'),
            "permission_id": kwargs.get('permission_id'),
            "holiday_id": kwargs.get('holiday_id'),
            "attendance_ids": kwargs.get('attendance_ids', []),
            "lock_status": LockStatus.OPEN.value,
            "lock_deadline": lock_deadline,
            "created_at": now.isoformat(),
            "created_by": "system",
            "corrections": []
        }
    
    def _create_error(self, message: str) -> dict:
        """إنشاء نتيجة خطأ"""
        return {
            "error": True,
            "message": message,
            "employee_id": self.employee_id,
            "date": self.date
        }


async def resolve_day(employee_id: str, date: str) -> dict:
    """دالة مساعدة لتنفيذ القرار"""
    resolver = DayResolver(employee_id, date)
    return await resolver.resolve()


async def resolve_and_save(employee_id: str, date: str) -> dict:
    """تنفيذ القرار وحفظه في قاعدة البيانات"""
    result = await resolve_day(employee_id, date)
    
    if result.get('error'):
        return result
    
    # حذف السجل القديم إن وجد
    await db.daily_status.delete_one({
        "employee_id": employee_id,
        "date": date
    })
    
    # حفظ السجل الجديد
    await db.daily_status.insert_one(result)
    result.pop('_id', None)
    
    return result
