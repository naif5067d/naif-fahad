"""
Notifications Model - نموذج الإشعارات الشامل
جميع الإشعارات في التطبيق تمر من هنا
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class NotificationType(str, Enum):
    """أنواع الإشعارات"""
    # معاملات
    TRANSACTION_SUBMITTED = "transaction_submitted"       # تم تقديم معاملة
    TRANSACTION_APPROVED = "transaction_approved"         # تمت الموافقة
    TRANSACTION_REJECTED = "transaction_rejected"         # تم الرفض
    TRANSACTION_EXECUTED = "transaction_executed"         # تم التنفيذ
    TRANSACTION_PENDING = "transaction_pending"           # معاملة بانتظارك
    TRANSACTION_RETURNED = "transaction_returned"         # تم إرجاع المعاملة
    
    # حضور
    ATTENDANCE_LATE = "attendance_late"                   # تأخير
    ATTENDANCE_ABSENT = "attendance_absent"               # غياب
    ATTENDANCE_EARLY_LEAVE = "attendance_early_leave"     # خروج مبكر
    
    # خصومات
    DEDUCTION_PROPOSED = "deduction_proposed"             # مقترح خصم جديد
    DEDUCTION_APPROVED = "deduction_approved"             # تمت الموافقة على الخصم
    DEDUCTION_EXECUTED = "deduction_executed"             # تم تنفيذ الخصم
    DEDUCTION_REJECTED = "deduction_rejected"             # تم رفض الخصم
    
    # إنذارات
    WARNING_ISSUED = "warning_issued"                     # إنذار جديد
    
    # عقود
    CONTRACT_EXPIRING = "contract_expiring"               # عقد ينتهي قريباً
    CONTRACT_RENEWED = "contract_renewed"                 # تم تجديد العقد
    
    # إجازات
    LEAVE_APPROVED = "leave_approved"                     # تمت الموافقة على الإجازة
    LEAVE_REJECTED = "leave_rejected"                     # تم رفض الإجازة
    LEAVE_BALANCE_LOW = "leave_balance_low"               # رصيد إجازة منخفض
    
    # عام
    ANNOUNCEMENT = "announcement"                         # إعلان
    REMINDER = "reminder"                                 # تذكير
    SYSTEM = "system"                                     # نظام


class NotificationPriority(str, Enum):
    """أولوية الإشعار"""
    CRITICAL = "critical"     # حرج - يظهر بشكل بارز
    HIGH = "high"             # مرتفع
    NORMAL = "normal"         # عادي
    LOW = "low"               # منخفض


# أيقونات الإشعارات
NOTIFICATION_ICONS = {
    NotificationType.TRANSACTION_SUBMITTED: "FileText",
    NotificationType.TRANSACTION_APPROVED: "CheckCircle",
    NotificationType.TRANSACTION_REJECTED: "XCircle",
    NotificationType.TRANSACTION_EXECUTED: "Shield",
    NotificationType.TRANSACTION_PENDING: "Clock",
    NotificationType.TRANSACTION_RETURNED: "RotateCcw",
    NotificationType.ATTENDANCE_LATE: "Clock",
    NotificationType.ATTENDANCE_ABSENT: "UserX",
    NotificationType.ATTENDANCE_EARLY_LEAVE: "LogOut",
    NotificationType.DEDUCTION_PROPOSED: "AlertTriangle",
    NotificationType.DEDUCTION_APPROVED: "CheckCircle",
    NotificationType.DEDUCTION_EXECUTED: "DollarSign",
    NotificationType.DEDUCTION_REJECTED: "XCircle",
    NotificationType.WARNING_ISSUED: "AlertTriangle",
    NotificationType.CONTRACT_EXPIRING: "FileWarning",
    NotificationType.CONTRACT_RENEWED: "FileCheck",
    NotificationType.LEAVE_APPROVED: "CalendarCheck",
    NotificationType.LEAVE_REJECTED: "CalendarX",
    NotificationType.LEAVE_BALANCE_LOW: "CalendarClock",
    NotificationType.ANNOUNCEMENT: "Megaphone",
    NotificationType.REMINDER: "Bell",
    NotificationType.SYSTEM: "Settings",
}

# ألوان الإشعارات
NOTIFICATION_COLORS = {
    NotificationType.TRANSACTION_APPROVED: "#10B981",    # أخضر
    NotificationType.TRANSACTION_REJECTED: "#EF4444",    # أحمر
    NotificationType.TRANSACTION_EXECUTED: "#A78BFA",    # بنفسجي
    NotificationType.TRANSACTION_PENDING: "#F97316",     # برتقالي
    NotificationType.ATTENDANCE_LATE: "#F59E0B",         # أصفر
    NotificationType.ATTENDANCE_ABSENT: "#EF4444",       # أحمر
    NotificationType.DEDUCTION_EXECUTED: "#EF4444",      # أحمر
    NotificationType.WARNING_ISSUED: "#EF4444",          # أحمر
    NotificationType.CONTRACT_EXPIRING: "#F59E0B",       # أصفر
    NotificationType.LEAVE_APPROVED: "#10B981",          # أخضر
}

# ترجمة أنواع الإشعارات
NOTIFICATION_TYPE_AR = {
    NotificationType.TRANSACTION_SUBMITTED: "تم تقديم معاملة",
    NotificationType.TRANSACTION_APPROVED: "تمت الموافقة على معاملتك",
    NotificationType.TRANSACTION_REJECTED: "تم رفض معاملتك",
    NotificationType.TRANSACTION_EXECUTED: "تم تنفيذ معاملتك",
    NotificationType.TRANSACTION_PENDING: "معاملة بانتظار موافقتك",
    NotificationType.TRANSACTION_RETURNED: "تم إرجاع المعاملة",
    NotificationType.ATTENDANCE_LATE: "تم تسجيل تأخير",
    NotificationType.ATTENDANCE_ABSENT: "تم تسجيل غياب",
    NotificationType.ATTENDANCE_EARLY_LEAVE: "تم تسجيل خروج مبكر",
    NotificationType.DEDUCTION_PROPOSED: "مقترح خصم جديد",
    NotificationType.DEDUCTION_APPROVED: "تمت الموافقة على الخصم",
    NotificationType.DEDUCTION_EXECUTED: "تم تنفيذ خصم",
    NotificationType.DEDUCTION_REJECTED: "تم رفض مقترح الخصم",
    NotificationType.WARNING_ISSUED: "إنذار جديد",
    NotificationType.CONTRACT_EXPIRING: "عقد ينتهي قريباً",
    NotificationType.CONTRACT_RENEWED: "تم تجديد العقد",
    NotificationType.LEAVE_APPROVED: "تمت الموافقة على إجازتك",
    NotificationType.LEAVE_REJECTED: "تم رفض طلب الإجازة",
    NotificationType.LEAVE_BALANCE_LOW: "رصيد الإجازة منخفض",
    NotificationType.ANNOUNCEMENT: "إعلان جديد",
    NotificationType.REMINDER: "تذكير",
    NotificationType.SYSTEM: "إشعار نظام",
}


class NotificationCreate(BaseModel):
    """نموذج إنشاء إشعار"""
    recipient_id: str                           # معرف المستلم (user_id)
    recipient_role: Optional[str] = None        # أو الدور (للإشعارات الجماعية)
    notification_type: NotificationType
    title: str
    title_ar: str
    message: str
    message_ar: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    
    # بيانات مرتبطة
    reference_type: Optional[str] = None        # transaction, employee, contract, etc.
    reference_id: Optional[str] = None
    reference_url: Optional[str] = None         # رابط للانتقال
    
    # بيانات إضافية
    metadata: Optional[dict] = None


class NotificationRecord(BaseModel):
    """سجل الإشعار"""
    id: str
    recipient_id: str
    recipient_role: Optional[str] = None
    notification_type: str
    title: str
    title_ar: str
    message: str
    message_ar: str
    priority: str = "normal"
    icon: str = "Bell"
    color: str = "#6B7280"
    
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    reference_url: Optional[str] = None
    metadata: Optional[dict] = None
    
    is_read: bool = False
    read_at: Optional[str] = None
    created_at: str
