"""
Penalty Service - نظام العقوبات
يحسب العقوبات بناءً على قواعد الحضور والانصراف

قواعد الغياب:
- يوم غياب بدون عذر → خصم أجر يوم كامل
- 3 أيام غياب متصلة → إنذار أول
- 5 أيام متصلة → إنذار ثاني
- 10 أيام متصلة → إنذار نهائي
- 15 يوم غياب متصل → فصل
- 10 أيام متفرقة خلال السنة → إنذار أول
- 20 يوم متفرقة → إنذار نهائي
- 30 يوم متفرقة → فصل

قواعد التأخير والخروج المبكر:
- يحسب بالدقائق (وليس يوم)
- تجمع شهرياً
- كل 8 ساعات نقص = خصم يوم

الاستئذان:
- لا يعتبر غياب
- لا خصم إذا ضمن الرصيد أو بموافقة
- بدون موافقة → يتحول نقص ساعات

الإجازة المنفذة:
- لا تعتبر غياب إطلاقاً
- لا يوجد أي عقوبة

نسيان البصمة:
- بعد الموافقة يعتبر حضور
- بدون موافقة يعامل كتأخير/خروج مبكر حسب الحالة

الموظفون المستثنون:
- ستاس، محمد، صلاح، نايف - ليسوا موظفين، لا عقوبات عليهم
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from database import db


# الموظفون المستثنون من العقوبات (ليسوا موظفين)
EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-CEO', 'EMP-004', 'EMP-OPS2']  # stas, mohammed, salah, naif

# ثوابت العقوبات
ABSENCE_RULES = {
    "consecutive": {
        3: {"warning": "FIRST_WARNING", "name_ar": "إنذار أول"},
        5: {"warning": "SECOND_WARNING", "name_ar": "إنذار ثاني"},
        10: {"warning": "FINAL_WARNING", "name_ar": "إنذار نهائي"},
        15: {"warning": "TERMINATION", "name_ar": "فصل"}
    },
    "scattered_yearly": {
        10: {"warning": "FIRST_WARNING", "name_ar": "إنذار أول (غياب متفرق)"},
        20: {"warning": "FINAL_WARNING", "name_ar": "إنذار نهائي (غياب متفرق)"},
        30: {"warning": "TERMINATION", "name_ar": "فصل (غياب متفرق)"}
    }
}

# كل 8 ساعات نقص = خصم يوم
DEFICIT_HOURS_PER_DAY = 8


class PenaltyCalculator:
    """محرك حساب العقوبات"""
    
    def __init__(self, employee_id: str):
        self.employee_id = employee_id
        self.employee = None
        self.contract = None
    
    async def load_employee(self):
        """تحميل بيانات الموظف"""
        self.employee = await db.employees.find_one({"id": self.employee_id}, {"_id": 0})
        if self.employee:
            self.contract = await db.contracts_v2.find_one({
                "employee_id": self.employee_id,
                "status": "active",
                "is_active": True
            }, {"_id": 0})
    
    async def calculate_monthly_penalties(self, year: int, month: int) -> Dict:
        """
        حساب العقوبات الشهرية
        """
        await self.load_employee()
        
        if not self.employee:
            return {"error": "الموظف غير موجود"}
        
        # تحديد الفترة
        month_start = f"{year}-{month:02d}-01"
        if month == 12:
            month_end = f"{year + 1}-01-01"
        else:
            month_end = f"{year}-{month + 1:02d}-01"
        
        # جلب سجلات الحضور للشهر
        daily_records = await db.daily_status.find({
            "employee_id": self.employee_id,
            "date": {"$gte": month_start, "$lt": month_end}
        }, {"_id": 0}).sort("date", 1).to_list(100)
        
        # حساب الغيابات
        absence_result = self._calculate_absence_penalties(daily_records)
        
        # حساب نقص الساعات (تأخير + خروج مبكر)
        deficit_result = self._calculate_deficit_penalties(daily_records)
        
        # الراتب اليومي
        daily_salary = 0
        if self.contract:
            monthly_salary = self.contract.get("basic_salary", 0)
            daily_salary = monthly_salary / 30  # افتراضي 30 يوم
        
        # إجمالي الخصم
        total_days_deduction = absence_result["deduction_days"] + deficit_result["deduction_days"]
        total_deduction_amount = total_days_deduction * daily_salary
        
        return {
            "employee_id": self.employee_id,
            "employee_name_ar": self.employee.get("full_name_ar", ""),
            "period": f"{year}-{month:02d}",
            "daily_salary": daily_salary,
            
            # الغياب
            "absence": {
                "total_days": absence_result["total_days"],
                "consecutive_streaks": absence_result["streaks"],
                "deduction_days": absence_result["deduction_days"],
                "warnings": absence_result["warnings"]
            },
            
            # النقص (تأخير + خروج مبكر)
            "deficit": {
                "total_late_minutes": deficit_result["total_late_minutes"],
                "total_early_leave_minutes": deficit_result["total_early_leave_minutes"],
                "total_deficit_minutes": deficit_result["total_deficit_minutes"],
                "total_deficit_hours": deficit_result["total_deficit_hours"],
                "deduction_days": deficit_result["deduction_days"]
            },
            
            # الإجمالي
            "total_deduction_days": total_days_deduction,
            "total_deduction_amount": round(total_deduction_amount, 2),
            
            # تفاصيل يومية
            "daily_details": [
                {
                    "date": r["date"],
                    "status": r.get("final_status"),
                    "status_ar": r.get("status_ar"),
                    "late_minutes": r.get("late_minutes", 0),
                    "early_leave_minutes": r.get("early_leave_minutes", 0)
                }
                for r in daily_records
            ]
        }
    
    def _calculate_absence_penalties(self, records: List[Dict]) -> Dict:
        """
        حساب عقوبات الغياب
        """
        absent_days = []
        total_absent = 0
        
        for r in records:
            status = r.get("final_status")
            if status == "ABSENT":
                absent_days.append(r["date"])
                total_absent += 1
        
        # تحليل الغيابات المتصلة
        streaks = self._find_consecutive_streaks(absent_days)
        
        # تحديد الإنذارات
        warnings = []
        
        for streak in streaks:
            days = streak["days"]
            for threshold, warning_data in sorted(ABSENCE_RULES["consecutive"].items(), reverse=True):
                if days >= threshold:
                    warnings.append({
                        "type": warning_data["warning"],
                        "name_ar": warning_data["name_ar"],
                        "reason": f"غياب {days} أيام متصلة",
                        "start_date": streak["start"],
                        "end_date": streak["end"],
                        "days": days
                    })
                    break
        
        return {
            "total_days": total_absent,
            "streaks": streaks,
            "deduction_days": total_absent,  # كل يوم غياب = خصم يوم
            "warnings": warnings
        }
    
    def _find_consecutive_streaks(self, dates: List[str]) -> List[Dict]:
        """
        إيجاد الغيابات المتصلة
        """
        if not dates:
            return []
        
        # ترتيب التواريخ
        sorted_dates = sorted(dates)
        streaks = []
        current_streak = [sorted_dates[0]]
        
        for i in range(1, len(sorted_dates)):
            prev_date = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d")
            curr_date = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
            
            # فحص إذا كان اليوم التالي
            if (curr_date - prev_date).days == 1:
                current_streak.append(sorted_dates[i])
            else:
                # حفظ السلسلة الحالية وبدء جديدة
                if len(current_streak) >= 1:
                    streaks.append({
                        "start": current_streak[0],
                        "end": current_streak[-1],
                        "days": len(current_streak)
                    })
                current_streak = [sorted_dates[i]]
        
        # إضافة آخر سلسلة
        if len(current_streak) >= 1:
            streaks.append({
                "start": current_streak[0],
                "end": current_streak[-1],
                "days": len(current_streak)
            })
        
        return streaks
    
    def _calculate_deficit_penalties(self, records: List[Dict]) -> Dict:
        """
        حساب عقوبات نقص الساعات (التأخير والخروج المبكر)
        """
        total_late_minutes = 0
        total_early_leave_minutes = 0
        
        for r in records:
            status = r.get("final_status")
            
            # لا نحسب نقص للإجازات والعطل
            if status in ["ON_LEAVE", "ON_ADMIN_LEAVE", "HOLIDAY", "WEEKEND", "ON_MISSION"]:
                continue
            
            # الاستئذان المعتمد لا يحسب
            if status == "PERMISSION":
                continue
            
            total_late_minutes += r.get("late_minutes", 0)
            total_early_leave_minutes += r.get("early_leave_minutes", 0)
        
        total_deficit_minutes = total_late_minutes + total_early_leave_minutes
        total_deficit_hours = total_deficit_minutes / 60
        
        # كل 8 ساعات = يوم خصم
        deduction_days = total_deficit_hours / DEFICIT_HOURS_PER_DAY
        
        return {
            "total_late_minutes": total_late_minutes,
            "total_early_leave_minutes": total_early_leave_minutes,
            "total_deficit_minutes": total_deficit_minutes,
            "total_deficit_hours": round(total_deficit_hours, 2),
            "deduction_days": round(deduction_days, 2)
        }
    
    async def calculate_yearly_absence(self, year: int) -> Dict:
        """
        حساب الغيابات السنوية المتفرقة
        """
        await self.load_employee()
        
        if not self.employee:
            return {"error": "الموظف غير موجود"}
        
        year_start = f"{year}-01-01"
        year_end = f"{year + 1}-01-01"
        
        # جلب جميع سجلات الغياب للسنة
        absent_records = await db.daily_status.find({
            "employee_id": self.employee_id,
            "date": {"$gte": year_start, "$lt": year_end},
            "final_status": "ABSENT"
        }, {"_id": 0}).to_list(1000)
        
        total_absent = len(absent_records)
        
        # تحديد الإنذارات للغياب المتفرق
        warnings = []
        for threshold, warning_data in sorted(ABSENCE_RULES["scattered_yearly"].items(), reverse=True):
            if total_absent >= threshold:
                warnings.append({
                    "type": warning_data["warning"],
                    "name_ar": warning_data["name_ar"],
                    "reason": f"غياب {total_absent} يوم متفرق خلال السنة",
                    "year": year,
                    "days": total_absent
                })
                break
        
        return {
            "employee_id": self.employee_id,
            "employee_name_ar": self.employee.get("full_name_ar", ""),
            "year": year,
            "total_scattered_absence": total_absent,
            "warnings": warnings,
            "absence_dates": [r["date"] for r in absent_records]
        }


async def calculate_monthly_penalties(employee_id: str, year: int, month: int) -> Dict:
    """دالة مساعدة لحساب العقوبات الشهرية"""
    calculator = PenaltyCalculator(employee_id)
    return await calculator.calculate_monthly_penalties(year, month)


async def calculate_yearly_absence(employee_id: str, year: int) -> Dict:
    """دالة مساعدة لحساب الغيابات السنوية"""
    calculator = PenaltyCalculator(employee_id)
    return await calculator.calculate_yearly_absence(year)


async def create_monthly_penalty_report(year: int, month: int) -> List[Dict]:
    """
    إنشاء تقرير العقوبات الشهري لجميع الموظفين
    """
    employees = await db.employees.find({"is_active": {"$ne": False}}, {"_id": 0, "id": 1}).to_list(1000)
    
    reports = []
    for emp in employees:
        report = await calculate_monthly_penalties(emp["id"], year, month)
        if not report.get("error"):
            reports.append(report)
    
    return reports


async def create_warning_if_needed(employee_id: str, warning_type: str, reason: str, details: Dict) -> Optional[Dict]:
    """
    إنشاء إنذار إذا لم يكن موجوداً مسبقاً
    """
    # فحص إذا كان هناك إنذار مشابه
    existing = await db.warnings.find_one({
        "employee_id": employee_id,
        "warning_type": warning_type,
        "period": details.get("period") or details.get("year"),
        "status": {"$ne": "cancelled"}
    })
    
    if existing:
        return None  # الإنذار موجود مسبقاً
    
    warning = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "warning_type": warning_type,
        "reason": reason,
        "details": details,
        "period": details.get("period") or str(details.get("year")),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "system"
    }
    
    await db.warnings.insert_one(warning)
    warning.pop("_id", None)
    
    return warning
