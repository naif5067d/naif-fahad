# Error Codes System for DAR AL CODE HR OS
# نظام رموز الأخطاء

from datetime import datetime, timezone
import uuid

class ErrorCode:
    """نظام رموز الأخطاء الموحد"""
    
    # Authentication Errors (1xxx)
    AUTH_INVALID_CREDENTIALS = ("E1001", "Invalid username or password", "اسم المستخدم أو كلمة المرور غير صحيحة")
    AUTH_TOKEN_EXPIRED = ("E1002", "Session expired, please login again", "انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى")
    AUTH_TOKEN_INVALID = ("E1003", "Invalid or corrupted token", "رمز الجلسة غير صالح")
    AUTH_ACCOUNT_BLOCKED = ("E1004", "Account is blocked", "الحساب محظور")
    AUTH_ACCOUNT_DISABLED = ("E1005", "Account is disabled", "الحساب معطل")
    AUTH_SESSION_REVOKED = ("E1006", "Session has been revoked", "تم إنهاء الجلسة")
    AUTH_RATE_LIMITED = ("E1007", "Too many login attempts", "عدد محاولات تسجيل الدخول تجاوز الحد المسموح")
    AUTH_DEVICE_CHANGED = ("E1008", "Device changed, previous sessions terminated", "تم تغيير الجهاز، تم إنهاء الجلسات السابقة")
    
    # Contract Errors (2xxx)
    CONTRACT_NOT_FOUND = ("E2001", "No active contract found", "لا يوجد عقد نشط")
    CONTRACT_EXPIRED = ("E2002", "Contract has expired", "العقد منتهي الصلاحية")
    CONTRACT_PENDING = ("E2003", "Contract is pending approval", "العقد في انتظار الموافقة")
    CONTRACT_SANDBOX_MODE = ("E2004", "Contract is in sandbox/trial mode", "العقد في وضع التجربة")
    CONTRACT_NOT_STARTED = ("E2005", "Work start date has not arrived yet", "لم يحن تاريخ مباشرة العمل بعد")
    CONTRACT_DUPLICATE = ("E2006", "Employee already has an active contract", "الموظف لديه عقد نشط بالفعل")
    
    # Attendance Errors (3xxx)
    ATTENDANCE_ALREADY_CHECKED_IN = ("E3001", "Already checked in today", "تم تسجيل الدخول مسبقاً اليوم")
    ATTENDANCE_NOT_CHECKED_IN = ("E3002", "Must check in first", "يجب تسجيل الدخول أولاً")
    ATTENDANCE_OUTSIDE_LOCATION = ("E3003", "Outside allowed work location", "خارج نطاق موقع العمل المسموح")
    ATTENDANCE_OUTSIDE_HOURS = ("E3004", "Outside working hours", "خارج ساعات العمل")
    ATTENDANCE_HOLIDAY = ("E3005", "Today is an official holiday", "اليوم عطلة رسمية")
    ATTENDANCE_WEEKEND = ("E3006", "Today is not a work day", "اليوم ليس يوم عمل")
    ATTENDANCE_ON_LEAVE = ("E3007", "Employee is on approved leave", "الموظف في إجازة معتمدة")
    ATTENDANCE_GPS_REQUIRED = ("E3008", "GPS location is required", "يجب تفعيل تحديد الموقع")
    ATTENDANCE_NO_LOCATION = ("E3009", "No work location assigned", "لا يوجد موقع عمل معين")
    
    # Leave Errors (4xxx)
    LEAVE_INSUFFICIENT_BALANCE = ("E4001", "Insufficient leave balance", "رصيد الإجازات غير كافٍ")
    LEAVE_OVERLAP = ("E4002", "Leave dates overlap with existing request", "تواريخ الإجازة متداخلة مع طلب آخر")
    LEAVE_PAST_DATE = ("E4003", "Cannot request leave for past dates", "لا يمكن طلب إجازة لتواريخ ماضية")
    LEAVE_MIN_DAYS = ("E4004", "Minimum leave days not met", "الحد الأدنى لأيام الإجازة غير مستوفى")
    
    # Transaction Errors (5xxx)
    TRANSACTION_NOT_FOUND = ("E5001", "Transaction not found", "المعاملة غير موجودة")
    TRANSACTION_ALREADY_PROCESSED = ("E5002", "Transaction already processed", "المعاملة تمت معالجتها مسبقاً")
    TRANSACTION_UNAUTHORIZED = ("E5003", "Not authorized to process this transaction", "غير مصرح لك بمعالجة هذه المعاملة")
    
    # General Errors (9xxx)
    GENERAL_NOT_FOUND = ("E9001", "Resource not found", "المورد غير موجود")
    GENERAL_FORBIDDEN = ("E9002", "Access denied", "الوصول مرفوض")
    GENERAL_SERVER_ERROR = ("E9003", "Internal server error", "خطأ في الخادم")
    GENERAL_VALIDATION_ERROR = ("E9004", "Validation error", "خطأ في التحقق من البيانات")


def create_error_response(error_code: tuple, details: str = None, details_ar: str = None):
    """
    إنشاء استجابة خطأ موحدة
    
    Args:
        error_code: tuple من (code, message_en, message_ar)
        details: تفاصيل إضافية بالإنجليزية
        details_ar: تفاصيل إضافية بالعربية
    
    Returns:
        dict: استجابة الخطأ الموحدة
    """
    code, msg_en, msg_ar = error_code
    
    # إنشاء معرف فريد للخطأ
    error_id = f"{code}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    
    return {
        "error": True,
        "error_code": code,
        "error_id": error_id,
        "message": msg_en,
        "message_ar": msg_ar,
        "details": details,
        "details_ar": details_ar,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "support_message": f"If this error persists, contact support with reference: {error_id}",
        "support_message_ar": f"إذا استمر هذا الخطأ، تواصل مع الدعم مع الرقم المرجعي: {error_id}"
    }


def format_error_message(error_code: tuple, details: str = None, details_ar: str = None) -> dict:
    """تنسيق رسالة الخطأ للعرض"""
    response = create_error_response(error_code, details, details_ar)
    return {
        "detail": response
    }
