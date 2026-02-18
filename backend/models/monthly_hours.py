"""
Monthly Hours Model - ملخص الساعات الشهرية
"""
from typing import Optional, List
from pydantic import BaseModel


class MonthlyHoursRecord(BaseModel):
    id: str
    employee_id: str
    month: str  # YYYY-MM
    
    # الساعات الأساسية
    required_hours: float          # عدد أيام العمل × ساعات اليوم
    actual_hours: float            # مجموع ساعات الحضور الفعلية
    
    # الخصومات
    permission_hours: float        # ساعات الاستئذان المنفذة
    late_minutes: int              # دقائق التأخير
    early_leave_minutes: int       # دقائق الخروج المبكر
    
    # التعويض
    compensation_hours: float      # ساعات البقاء الإضافي
    
    # الحساب النهائي
    net_hours: float               # actual + compensation - required
    deficit_hours: float           # ساعات النقص (إذا net < 0)
    deficit_days: float            # أيام الغياب = deficit_hours / 8
    
    # تفاصيل الأيام
    working_days: int              # عدد أيام العمل المطلوبة
    present_days: int              # أيام الحضور
    absent_days: int               # أيام الغياب
    leave_days: int                # أيام الإجازة
    holiday_days: int              # أيام العطل
    mission_days: int              # أيام المهمات
    
    # الحالة
    is_finalized: bool = False     # هل تم إغلاق الشهر
    finalized_at: Optional[str] = None
    finalized_by: Optional[str] = None
    
    # التدقيق
    created_at: str
    updated_at: Optional[str] = None
    
    # تفاصيل الأيام (للمرجعية)
    daily_details: List[dict] = []


class MonthlyHoursSummary(BaseModel):
    """ملخص مختصر للعرض"""
    employee_id: str
    employee_name: str
    month: str
    required_hours: float
    actual_hours: float
    net_hours: float
    deficit_days: float
    status: str  # ok, warning, critical
