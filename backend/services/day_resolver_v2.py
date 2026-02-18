"""
Day Resolver V2 - محرك القرار اليومي مع العروق (Trace Evidence)

ترتيب الفحص الإجباري (نظام العمل السعودي):
1. holiday    → عطلة رسمية
2. weekend    → عطلة نهاية أسبوع
3. leave      → إجازة منفذة
4. mission    → مهمة خارجية منفذة
5. forget     → نسيان بصمة منفذ
6. attendance → بصمة فعلية
7. permission → استئذان جزئي
8. excuses    → تبريرات (تأخير/خروج)
9. ABSENT     → غياب بدون عذر

كل فحص يسجل في trace_log سواء نجح أو فشل.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List
from zoneinfo import ZoneInfo
from database import db
from models.daily_status import DailyStatusEnum, LockStatus, STATUS_AR

# توقيت الرياض
RIYADH_TZ = ZoneInfo("Asia/Riyadh")


class TraceStep:
    """خطوة واحدة في سلسلة الفحص"""
    def __init__(self, step_name: str, step_name_ar: str, order: int):
        self.step_name = step_name
        self.step_name_ar = step_name_ar
        self.order = order
        self.checked = False
        self.found = False
        self.result = None
        self.details = {}
        self.timestamp = None
        
    def to_dict(self) -> dict:
        return {
            "order": self.order,
            "step": self.step_name,
            "step_ar": self.step_name_ar,
            "checked": self.checked,
            "found": self.found,
            "result": self.result,
            "details": self.details,
            "timestamp": self.timestamp
        }


class DayResolverV2:
    """
    محرك القرار اليومي V2 مع العروق (Trace Evidence)
    
    يحفظ سجل كامل لكل ما تم فحصه قبل الوصول للنتيجة النهائية.
    هذا السجل (trace_log) يظهر في مرآة STAS لتبرير القرار.
    """
    
    STEPS = [
        ("holiday", "العطل الرسمية", 1),
        ("weekend", "عطلة نهاية الأسبوع", 2),
        ("leave", "الإجازات المنفذة", 3),
        ("mission", "المهمات الخارجية", 4),
        ("forget_checkin", "نسيان البصمة", 5),
        ("attendance", "البصمة الفعلية", 6),
        ("permission", "الاستئذان الجزئي", 7),
        ("excuses", "التبريرات", 8),
    ]
    
    def __init__(self, employee_id: str, date: str):
        self.employee_id = employee_id
        self.date = date
        self.employee = None
        self.contract = None
        self.work_location = None
        
        # Initialize trace log
        self.trace_log: List[TraceStep] = []
        for step_name, step_name_ar, order in self.STEPS:
            self.trace_log.append(TraceStep(step_name, step_name_ar, order))
        
        # Final decision
        self.final_status = None
        self.final_source = None
        
    def _get_step(self, step_name: str) -> TraceStep:
        """Get trace step by name"""
        for step in self.trace_log:
            if step.step_name == step_name:
                return step
        return None
        
    async def resolve(self) -> dict:
        """
        تحليل اليوم وإرجاع القرار النهائي مع العروق
        """
        start_time = datetime.now(timezone.utc)
        
        # تحميل بيانات الموظف
        await self._load_employee_data()
        
        if not self.employee:
            return self._create_error("الموظف غير موجود")
        
        if not self.contract:
            return self._create_error("لا يوجد عقد نشط")
        
        # تنفيذ سلسلة الفحوصات بالترتيب
        result = None
        
        # 1. فحص العطل الرسمية
        result = await self._check_holidays()
        if result:
            return self._finalize_result(result, start_time)
        
        # 2. فحص عطلة نهاية الأسبوع
        result = await self._check_weekend()
        if result:
            return self._finalize_result(result, start_time)
        
        # 3. فحص الإجازات المنفذة
        result = await self._check_leaves()
        if result:
            return self._finalize_result(result, start_time)
        
        # 4. فحص المهمات الخارجية
        result = await self._check_missions()
        if result:
            return self._finalize_result(result, start_time)
        
        # 5. فحص نسيان البصمة
        result = await self._check_forgotten_punch()
        if result:
            return self._finalize_result(result, start_time)
        
        # 6. فحص البصمة الفعلية
        result = await self._check_attendance()
        if result:
            return self._finalize_result(result, start_time)
        
        # 7. فحص الاستئذان الجزئي
        result = await self._check_permissions()
        if result:
            return self._finalize_result(result, start_time)
        
        # 8. فحص التبريرات (تأخير/خروج مبكر)
        await self._check_excuses()
        
        # 9. خلاف ذلك = غياب
        result = self._create_absent_result()
        return self._finalize_result(result, start_time)
    
    def _finalize_result(self, result: dict, start_time: datetime) -> dict:
        """إضافة العروق للنتيجة النهائية"""
        end_time = datetime.now(timezone.utc)
        
        result["trace_log"] = [step.to_dict() for step in self.trace_log]
        result["trace_summary"] = self._generate_trace_summary()
        result["resolution_time_ms"] = int((end_time - start_time).total_seconds() * 1000)
        
        return result
    
    def _generate_trace_summary(self) -> dict:
        """إنشاء ملخص العروق للعرض في STAS Mirror"""
        checked_steps = [s for s in self.trace_log if s.checked]
        found_steps = [s for s in self.trace_log if s.found]
        
        summary_ar = []
        for step in self.trace_log:
            if step.checked:
                if step.found:
                    summary_ar.append(f"✅ {step.step_name_ar}: تم العثور عليه")
                else:
                    summary_ar.append(f"❌ {step.step_name_ar}: لا يوجد")
        
        return {
            "total_steps": len(self.STEPS),
            "steps_checked": len(checked_steps),
            "steps_found": len(found_steps),
            "deciding_step": found_steps[-1].step_name if found_steps else "absent",
            "deciding_step_ar": found_steps[-1].step_name_ar if found_steps else "غياب",
            "summary_ar": summary_ar,
            "conclusion_ar": self._get_conclusion_ar()
        }
    
    def _get_conclusion_ar(self) -> str:
        """إنشاء خلاصة القرار بالعربي"""
        found_steps = [s for s in self.trace_log if s.found]
        
        if not found_steps:
            return "لم يتم العثور على أي عطلة أو إجازة أو مهمة أو بصمة - يُعتبر غائباً"
        
        last_found = found_steps[-1]
        return f"تم اتخاذ القرار بناءً على: {last_found.step_name_ar}"
    
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
            work_location_id = self.employee.get('work_location_id') or (self.contract.get('work_location_id') if self.contract else None)
            if work_location_id:
                self.work_location = await db.work_locations.find_one(
                    {"id": work_location_id}, 
                    {"_id": 0}
                )
    
    async def _check_holidays(self) -> Optional[dict]:
        """1. فحص العطل الرسمية"""
        step = self._get_step("holiday")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        holiday = await db.holidays.find_one({
            "date": self.date,
            "is_active": {"$ne": False}
        }, {"_id": 0})
        
        if holiday:
            step.found = True
            step.result = "found"
            step.details = {
                "holiday_id": holiday.get('id'),
                "holiday_name": holiday.get('name_ar', holiday.get('name', '')),
                "holiday_date": self.date
            }
            
            return self._create_result(
                status=DailyStatusEnum.HOLIDAY,
                reason="عطلة رسمية",
                reason_ar=f"عطلة رسمية: {holiday.get('name_ar', holiday.get('name', ''))}",
                source="holiday",
                holiday_id=holiday.get('id')
            )
        
        step.result = "not_found"
        step.details = {"searched_date": self.date, "holidays_checked": 1}
        return None
    
    async def _check_weekend(self) -> Optional[dict]:
        """2. فحص عطلة نهاية الأسبوع"""
        step = self._get_step("weekend")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        date_obj = datetime.strptime(self.date, "%Y-%m-%d")
        day_of_week = date_obj.weekday()
        
        # تحويل اسم اليوم
        day_names_en = {0: "monday", 1: "tuesday", 2: "wednesday", 
                       3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
        day_names = {0: "الإثنين", 1: "الثلاثاء", 2: "الأربعاء", 
                    3: "الخميس", 4: "الجمعة", 5: "السبت", 6: "الأحد"}
        
        day_name_en = day_names_en.get(day_of_week)
        is_weekend = False
        
        if self.work_location:
            # فحص work_days - إذا اليوم = false فهو عطلة
            work_days = self.work_location.get('work_days', {})
            if work_days and day_name_en in work_days:
                is_weekend = not work_days.get(day_name_en, True)
            else:
                # الافتراضي: الجمعة والسبت عطلة
                is_weekend = day_of_week in [4, 5]
        else:
            # الافتراضي: الجمعة والسبت عطلة
            is_weekend = day_of_week in [4, 5]
        
        step.details = {
            "date": self.date,
            "day_of_week": day_of_week,
            "day_name_ar": day_names.get(day_of_week, ''),
            "work_days_config": self.work_location.get('work_days', {}) if self.work_location else {},
            "work_location": self.work_location.get('name_ar', self.work_location.get('name')) if self.work_location else "افتراضي",
            "is_weekend": is_weekend
        }
        
        if is_weekend:
            step.found = True
            step.result = "is_weekend"
            
            return self._create_result(
                status=DailyStatusEnum.WEEKEND,
                reason="عطلة نهاية أسبوع",
                reason_ar=f"عطلة نهاية الأسبوع ({day_names.get(day_of_week, '')})",
                source="weekend"
            )
        
        step.result = "not_weekend"
        return None
    
    async def _check_leaves(self) -> Optional[dict]:
        """3. فحص الإجازات المنفذة"""
        step = self._get_step("leave")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        # فحص في transactions
        leave = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "leave_request",
            "status": "executed",
            "data.start_date": {"$lte": self.date},
            "data.end_date": {"$gte": self.date}
        }, {"_id": 0})
        
        step.details = {
            "searched_employee": self.employee_id,
            "searched_date": self.date,
            "searched_status": "executed"
        }
        
        if leave:
            step.found = True
            step.result = "found"
            leave_type = leave.get('data', {}).get('leave_type', 'annual')
            leave_type_ar = {
                'annual': 'سنوية',
                'sick': 'مرضية',
                'emergency': 'اضطرارية',
                'unpaid': 'بدون راتب',
                'admin': 'إدارية',
                'bereavement': 'وفاة',
                'marriage': 'زواج',
                'maternity': 'أمومة',
                'paternity': 'أبوة'
            }.get(leave_type, leave_type)
            
            step.details.update({
                "leave_id": leave.get('id'),
                "leave_ref": leave.get('ref_no'),
                "leave_type": leave_type,
                "leave_type_ar": leave_type_ar,
                "start_date": leave.get('data', {}).get('start_date'),
                "end_date": leave.get('data', {}).get('end_date')
            })
            
            status = DailyStatusEnum.ON_ADMIN_LEAVE if leave_type == 'admin' else DailyStatusEnum.ON_LEAVE
            
            return self._create_result(
                status=status,
                reason=f"إجازة {leave_type_ar}",
                reason_ar=f"إجازة {leave_type_ar} منفذة (رقم: {leave.get('ref_no', '')})",
                source="leave",
                leave_id=leave.get('id')
            )
        
        step.result = "not_found"
        return None
    
    async def _check_missions(self) -> Optional[dict]:
        """4. فحص المهمات الخارجية المنفذة"""
        step = self._get_step("mission")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        mission = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "mission",
            "status": "executed",
            "data.start_date": {"$lte": self.date},
            "data.end_date": {"$gte": self.date}
        }, {"_id": 0})
        
        step.details = {
            "searched_employee": self.employee_id,
            "searched_date": self.date
        }
        
        if mission:
            step.found = True
            step.result = "found"
            step.details.update({
                "mission_id": mission.get('id'),
                "mission_ref": mission.get('ref_no'),
                "destination": mission.get('data', {}).get('destination', '')
            })
            
            return self._create_result(
                status=DailyStatusEnum.ON_MISSION,
                reason="مهمة خارجية",
                reason_ar=f"مهمة خارجية: {mission.get('data', {}).get('destination', '')}",
                source="mission",
                mission_id=mission.get('id')
            )
        
        step.result = "not_found"
        return None
    
    async def _check_forgotten_punch(self) -> Optional[dict]:
        """5. فحص نسيان البصمة المنفذ"""
        step = self._get_step("forget_checkin")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        forgotten = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "forgotten_punch",
            "status": "executed",
            "data.date": self.date
        }, {"_id": 0})
        
        step.details = {"searched_employee": self.employee_id, "searched_date": self.date}
        
        if forgotten:
            step.found = True
            step.result = "found"
            step.details.update({
                "forgotten_id": forgotten.get('id'),
                "forgotten_ref": forgotten.get('ref_no'),
                "claimed_check_in": forgotten.get('data', {}).get('claimed_check_in'),
                "claimed_check_out": forgotten.get('data', {}).get('claimed_check_out')
            })
            
            return self._create_result(
                status=DailyStatusEnum.PRESENT,
                reason="نسيان بصمة معتمد",
                reason_ar="نسيان بصمة تم اعتماده",
                source="forgotten_punch",
                check_in_time=forgotten.get('data', {}).get('claimed_check_in'),
                check_out_time=forgotten.get('data', {}).get('claimed_check_out')
            )
        
        step.result = "not_found"
        return None
    
    async def _check_attendance(self) -> Optional[dict]:
        """6. فحص البصمة الفعلية وتحليل التأخير والخروج"""
        step = self._get_step("attendance")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        # جلب بصمة الدخول
        check_in = await db.attendance_ledger.find_one({
            "employee_id": self.employee_id,
            "date": self.date,
            "type": "check_in"
        }, {"_id": 0})
        
        step.details = {
            "searched_employee": self.employee_id,
            "searched_date": self.date,
            "check_in_found": check_in is not None
        }
        
        if not check_in:
            step.result = "no_check_in"
            return None
        
        step.found = True
        
        # جلب بصمة الخروج
        check_out = await db.attendance_ledger.find_one({
            "employee_id": self.employee_id,
            "date": self.date,
            "type": "check_out"
        }, {"_id": 0})
        
        step.details["check_out_found"] = check_out is not None
        step.details["check_in_time"] = check_in.get('timestamp')
        if check_out:
            step.details["check_out_time"] = check_out.get('timestamp')
        
        # تحليل الأوقات
        analysis = await self._analyze_attendance(check_in, check_out)
        step.details["analysis"] = analysis
        step.result = "found_and_analyzed"
        
        # تحديد الحالة
        status = DailyStatusEnum.PRESENT
        reason_parts = []
        
        if analysis['is_late']:
            status = DailyStatusEnum.LATE
            reason_parts.append(f"تأخير {analysis['late_minutes']} دقيقة")
        
        if analysis['is_early_leave']:
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
        work_start = "08:00"
        work_end = "17:00"
        required_hours = 8.0
        grace_period_in = 15
        grace_period_out = 15
        
        if self.work_location:
            work_start = self.work_location.get('work_start_time', '08:00')
            work_end = self.work_location.get('work_end_time', '17:00')
            required_hours = self.work_location.get('daily_hours', 8.0)
            grace_period_in = self.work_location.get('grace_period_checkin_minutes', 15)
            grace_period_out = self.work_location.get('grace_period_checkout_minutes', 15)
        
        check_in_time = datetime.fromisoformat(check_in['timestamp'].replace('Z', '+00:00'))
        work_start_time = datetime.strptime(f"{self.date} {work_start}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        
        late_minutes = 0
        is_late = False
        allowed_late = work_start_time + timedelta(minutes=grace_period_in)
        
        if check_in_time > allowed_late:
            late_minutes = int((check_in_time - work_start_time).total_seconds() / 60)
            is_late = True
        
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
            'work_start': work_start,
            'work_end': work_end,
            'grace_period_in': grace_period_in,
            'grace_period_out': grace_period_out
        }
    
    async def _check_permissions(self) -> Optional[dict]:
        """7. فحص الاستئذان الجزئي المنفذ"""
        step = self._get_step("permission")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        permission = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "permission",
            "status": "executed",
            "data.date": self.date
        }, {"_id": 0})
        
        step.details = {"searched_employee": self.employee_id, "searched_date": self.date}
        
        if permission:
            step.found = True
            step.result = "found"
            hours = permission.get('data', {}).get('hours', 0)
            step.details.update({
                "permission_id": permission.get('id'),
                "permission_ref": permission.get('ref_no'),
                "hours": hours
            })
            
            return self._create_result(
                status=DailyStatusEnum.PERMISSION,
                reason=f"استئذان {hours} ساعات",
                reason_ar=f"استئذان {hours} ساعات",
                source="permission",
                permission_id=permission.get('id'),
                permission_hours=hours
            )
        
        step.result = "not_found"
        return None
    
    async def _check_excuses(self):
        """8. فحص التبريرات (تأخير/خروج مبكر)"""
        step = self._get_step("excuses")
        step.checked = True
        step.timestamp = datetime.now(timezone.utc).isoformat()
        
        # فحص تبرير التأخير
        late_excuse = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "late_excuse",
            "status": "executed",
            "data.date": self.date
        }, {"_id": 0})
        
        # فحص تبرير الخروج المبكر
        early_excuse = await db.transactions.find_one({
            "employee_id": self.employee_id,
            "type": "early_leave_excuse",
            "status": "executed",
            "data.date": self.date
        }, {"_id": 0})
        
        step.details = {
            "late_excuse_found": late_excuse is not None,
            "early_excuse_found": early_excuse is not None
        }
        
        if late_excuse or early_excuse:
            step.found = True
            step.result = "excuses_found"
            if late_excuse:
                step.details["late_excuse_id"] = late_excuse.get('id')
            if early_excuse:
                step.details["early_excuse_id"] = early_excuse.get('id')
        else:
            step.result = "no_excuses"
    
    def _create_absent_result(self) -> dict:
        """9. إنشاء نتيجة الغياب"""
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
        
        self.final_status = status
        self.final_source = source
        
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
            "date": self.date,
            "trace_log": [step.to_dict() for step in self.trace_log]
        }


async def resolve_day_v2(employee_id: str, date: str) -> dict:
    """دالة مساعدة لتنفيذ القرار V2"""
    resolver = DayResolverV2(employee_id, date)
    return await resolver.resolve()


async def resolve_and_save_v2(employee_id: str, date: str) -> dict:
    """تنفيذ القرار V2 وحفظه في قاعدة البيانات"""
    result = await resolve_day_v2(employee_id, date)
    
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
