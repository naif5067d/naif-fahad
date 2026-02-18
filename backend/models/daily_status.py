"""
Daily Status Model - السجل اليومي النهائي للموظف
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class DailyStatusEnum(str, Enum):
    """الحالات النهائية المسموح بها"""
    PRESENT = "PRESENT"                 # حاضر
    LATE = "LATE"                       # متأخر
    LATE_EXCUSED = "LATE_EXCUSED"       # متأخر معذور
    EARLY_LEAVE = "EARLY_LEAVE"         # خروج مبكر
    EARLY_EXCUSED = "EARLY_EXCUSED"     # خروج مبكر معذور
    PERMISSION = "PERMISSION"           # استئذان
    ON_MISSION = "ON_MISSION"           # مهمة خارجية
    ON_LEAVE = "ON_LEAVE"               # إجازة
    ON_ADMIN_LEAVE = "ON_ADMIN_LEAVE"   # إجازة إدارية
    HOLIDAY = "HOLIDAY"                 # عطلة رسمية
    WEEKEND = "WEEKEND"                 # عطلة نهاية أسبوع
    ABSENT = "ABSENT"                   # غياب


class LockStatus(str, Enum):
    """حالات القفل"""
    OPEN = "open"           # مفتوح - 48 ساعة - سلطان/نايف
    REVIEW = "review"       # مراجعة - 7 أيام - STAS
    LOCKED = "locked"       # مقفل - لا أحد


class DailyStatusCreate(BaseModel):
    employee_id: str
    date: str  # YYYY-MM-DD
    

class DailyStatusRecord(BaseModel):
    id: str
    employee_id: str
    date: str  # YYYY-MM-DD
    
    # الحالة النهائية
    final_status: DailyStatusEnum
    status_ar: str
    
    # تفاصيل القرار
    decision_reason: str
    decision_reason_ar: str
    decision_source: str  # holiday, leave, mission, attendance, etc.
    
    # بيانات الحضور الفعلي (إن وجدت)
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    actual_hours: Optional[float] = None
    required_hours: Optional[float] = None
    
    # التأخير والخروج المبكر
    late_minutes: int = 0
    early_leave_minutes: int = 0
    
    # الاستئذان
    permission_hours: float = 0
    
    # المرجعيات
    leave_id: Optional[str] = None
    mission_id: Optional[str] = None
    permission_id: Optional[str] = None
    holiday_id: Optional[str] = None
    attendance_ids: List[str] = []
    
    # حالة القفل
    lock_status: LockStatus = LockStatus.OPEN
    lock_deadline: Optional[str] = None
    
    # التدقيق
    created_at: str
    created_by: str = "system"
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    corrections: List[dict] = []  # سجل التصحيحات


# قاموس الحالات بالعربي
STATUS_AR = {
    DailyStatusEnum.PRESENT: "حاضر",
    DailyStatusEnum.LATE: "متأخر",
    DailyStatusEnum.LATE_EXCUSED: "متأخر معذور",
    DailyStatusEnum.EARLY_LEAVE: "خروج مبكر",
    DailyStatusEnum.EARLY_EXCUSED: "خروج مبكر معذور",
    DailyStatusEnum.PERMISSION: "استئذان",
    DailyStatusEnum.ON_MISSION: "مهمة خارجية",
    DailyStatusEnum.ON_LEAVE: "إجازة",
    DailyStatusEnum.ON_ADMIN_LEAVE: "إجازة إدارية",
    DailyStatusEnum.HOLIDAY: "عطلة رسمية",
    DailyStatusEnum.WEEKEND: "عطلة نهاية أسبوع",
    DailyStatusEnum.ABSENT: "غياب",
}
