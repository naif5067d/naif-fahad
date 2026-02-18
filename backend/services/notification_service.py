"""
Notification Service - خدمة الإشعارات الشاملة
إنشاء وإرسال وإدارة جميع الإشعارات في النظام
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from database import db
from models.notifications import (
    NotificationType, 
    NotificationPriority,
    NotificationCreate,
    NOTIFICATION_ICONS,
    NOTIFICATION_COLORS,
    NOTIFICATION_TYPE_AR
)


async def create_notification(
    recipient_id: str,
    notification_type: NotificationType,
    title: str,
    title_ar: str,
    message: str,
    message_ar: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    recipient_role: str = None,
    reference_type: str = None,
    reference_id: str = None,
    reference_url: str = None,
    metadata: dict = None
) -> dict:
    """إنشاء إشعار جديد"""
    now = datetime.now(timezone.utc).isoformat()
    
    notification = {
        "id": str(uuid.uuid4()),
        "recipient_id": recipient_id,
        "recipient_role": recipient_role,
        "notification_type": notification_type.value,
        "title": title,
        "title_ar": title_ar,
        "message": message,
        "message_ar": message_ar,
        "priority": priority.value,
        "icon": NOTIFICATION_ICONS.get(notification_type, "Bell"),
        "color": NOTIFICATION_COLORS.get(notification_type, "#6B7280"),
        "reference_type": reference_type,
        "reference_id": reference_id,
        "reference_url": reference_url,
        "metadata": metadata or {},
        "is_read": False,
        "read_at": None,
        "created_at": now
    }
    
    await db.notifications.insert_one(notification)
    notification.pop('_id', None)
    
    return notification


async def notify_transaction_submitted(transaction: dict, submitter_name: str):
    """إشعار بتقديم معاملة جديدة - للمرحلة التالية"""
    current_stage = transaction.get('current_stage')
    
    # تحديد المستلم حسب المرحلة
    stage_to_role = {
        'supervisor': 'supervisor',
        'ops': 'sultan',
        'ceo': 'mohammed',
        'finance': 'salah',
        'stas': 'stas'
    }
    
    recipient_role = stage_to_role.get(current_stage)
    if not recipient_role:
        return
    
    # جلب المستخدمين بهذا الدور
    users = await db.users.find({"role": recipient_role, "is_active": True}, {"_id": 0}).to_list(10)
    
    tx_type_ar = {
        'leave_request': 'طلب إجازة',
        'finance_60': 'قيد مالي',
        'settlement': 'مخالصة',
        'forget_checkin': 'نسيان بصمة',
        'mission': 'مهمة خارجية',
    }.get(transaction.get('type'), transaction.get('type'))
    
    for user in users:
        await create_notification(
            recipient_id=user['id'],
            notification_type=NotificationType.TRANSACTION_PENDING,
            title="New transaction pending your approval",
            title_ar="معاملة جديدة بانتظار موافقتك",
            message=f"{tx_type_ar} from {submitter_name} - Ref: {transaction.get('ref_no')}",
            message_ar=f"{tx_type_ar} من {submitter_name} - المرجع: {transaction.get('ref_no')}",
            priority=NotificationPriority.HIGH,
            recipient_role=recipient_role,
            reference_type="transaction",
            reference_id=transaction.get('id'),
            reference_url=f"/transactions/{transaction.get('id')}",
            metadata={"ref_no": transaction.get('ref_no'), "type": transaction.get('type')}
        )


async def notify_transaction_approved(transaction: dict, employee_id: str, approver_name: str):
    """إشعار بالموافقة على المعاملة - للموظف"""
    # جلب المستخدم المرتبط بالموظف
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    tx_type_ar = {
        'leave_request': 'طلب إجازة',
        'finance_60': 'قيد مالي',
        'forget_checkin': 'نسيان بصمة',
    }.get(transaction.get('type'), 'معاملة')
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=NotificationType.TRANSACTION_APPROVED,
        title="Your request has been approved",
        title_ar="تمت الموافقة على طلبك",
        message=f"{tx_type_ar} ({transaction.get('ref_no')}) approved by {approver_name}",
        message_ar=f"{tx_type_ar} ({transaction.get('ref_no')}) تمت الموافقة عليه من {approver_name}",
        priority=NotificationPriority.NORMAL,
        reference_type="transaction",
        reference_id=transaction.get('id'),
        reference_url=f"/transactions/{transaction.get('id')}",
        metadata={"ref_no": transaction.get('ref_no'), "approver": approver_name}
    )


async def notify_transaction_rejected(transaction: dict, employee_id: str, rejector_name: str, reason: str = ""):
    """إشعار برفض المعاملة - للموظف"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    tx_type_ar = {
        'leave_request': 'طلب إجازة',
        'finance_60': 'قيد مالي',
    }.get(transaction.get('type'), 'معاملة')
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=NotificationType.TRANSACTION_REJECTED,
        title="Your request has been rejected",
        title_ar="تم رفض طلبك",
        message=f"{tx_type_ar} ({transaction.get('ref_no')}) rejected. {reason}",
        message_ar=f"{tx_type_ar} ({transaction.get('ref_no')}) تم رفضه. {reason}",
        priority=NotificationPriority.HIGH,
        reference_type="transaction",
        reference_id=transaction.get('id'),
        reference_url=f"/transactions/{transaction.get('id')}",
        metadata={"ref_no": transaction.get('ref_no'), "reason": reason}
    )


async def notify_transaction_executed(transaction: dict, employee_id: str):
    """إشعار بتنفيذ المعاملة - للموظف"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    tx_type_ar = {
        'leave_request': 'طلب إجازة',
        'finance_60': 'قيد مالي',
        'settlement': 'مخالصة',
    }.get(transaction.get('type'), 'معاملة')
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=NotificationType.TRANSACTION_EXECUTED,
        title="Your request has been executed",
        title_ar="تم تنفيذ طلبك",
        message=f"{tx_type_ar} ({transaction.get('ref_no')}) has been executed by STAS",
        message_ar=f"{tx_type_ar} ({transaction.get('ref_no')}) تم تنفيذه من ستاس",
        priority=NotificationPriority.NORMAL,
        reference_type="transaction",
        reference_id=transaction.get('id'),
        reference_url=f"/transactions/{transaction.get('id')}",
        metadata={"ref_no": transaction.get('ref_no')}
    )


async def notify_deduction_proposed(employee_id: str, deduction: dict):
    """إشعار بمقترح خصم جديد - لسلطان"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    employee_name = employee.get('full_name_ar', employee.get('full_name', '')) if employee else ''
    
    # إشعار لسلطان ونايف
    admins = await db.users.find({"role": {"$in": ["sultan", "naif"]}, "is_active": True}, {"_id": 0}).to_list(10)
    
    for admin in admins:
        await create_notification(
            recipient_id=admin['id'],
            notification_type=NotificationType.DEDUCTION_PROPOSED,
            title="New deduction proposal",
            title_ar="مقترح خصم جديد",
            message=f"Deduction for {employee_name}: {deduction.get('amount')} SAR",
            message_ar=f"خصم على {employee_name}: {deduction.get('amount')} ر.س - {deduction.get('reason_ar', '')}",
            priority=NotificationPriority.HIGH,
            recipient_role=admin['role'],
            reference_type="deduction",
            reference_id=deduction.get('id'),
            reference_url="/deductions",
            metadata={"employee_id": employee_id, "amount": deduction.get('amount')}
        )


async def notify_deduction_executed(employee_id: str, deduction: dict):
    """إشعار بتنفيذ خصم - للموظف"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=NotificationType.DEDUCTION_EXECUTED,
        title="Deduction applied",
        title_ar="تم تطبيق خصم",
        message=f"A deduction of {deduction.get('amount')} SAR has been applied to your account",
        message_ar=f"تم خصم {deduction.get('amount')} ر.س من حسابك - {deduction.get('reason_ar', '')}",
        priority=NotificationPriority.HIGH,
        reference_type="deduction",
        reference_id=deduction.get('id'),
        reference_url="/",
        metadata={"amount": deduction.get('amount'), "reason": deduction.get('reason_ar')}
    )


async def notify_attendance_issue(employee_id: str, issue_type: str, date: str, details: dict = None):
    """إشعار بمشكلة حضور - للموظف"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    type_map = {
        'late': (NotificationType.ATTENDANCE_LATE, "Late arrival recorded", "تم تسجيل تأخير"),
        'absent': (NotificationType.ATTENDANCE_ABSENT, "Absence recorded", "تم تسجيل غياب"),
        'early_leave': (NotificationType.ATTENDANCE_EARLY_LEAVE, "Early leave recorded", "تم تسجيل خروج مبكر"),
    }
    
    notification_type, title, title_ar = type_map.get(issue_type, (NotificationType.SYSTEM, "Attendance issue", "مشكلة حضور"))
    
    message = f"Date: {date}"
    message_ar = f"التاريخ: {date}"
    
    if details:
        if details.get('late_minutes'):
            message += f" - {details['late_minutes']} minutes late"
            message_ar += f" - تأخير {details['late_minutes']} دقيقة"
        if details.get('early_minutes'):
            message += f" - Left {details['early_minutes']} minutes early"
            message_ar += f" - خروج مبكر {details['early_minutes']} دقيقة"
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=notification_type,
        title=title,
        title_ar=title_ar,
        message=message,
        message_ar=message_ar,
        priority=NotificationPriority.NORMAL,
        reference_type="attendance",
        reference_id=date,
        reference_url="/attendance",
        metadata={"date": date, **details} if details else {"date": date}
    )


async def notify_warning_issued(employee_id: str, warning: dict):
    """إشعار بإصدار إنذار - للموظف"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee or not employee.get('user_id'):
        return
    
    warning_level = warning.get('level', 1)
    level_ar = {1: 'أول', 2: 'ثاني', 3: 'ثالث'}.get(warning_level, str(warning_level))
    
    await create_notification(
        recipient_id=employee['user_id'],
        notification_type=NotificationType.WARNING_ISSUED,
        title=f"Warning #{warning_level} issued",
        title_ar=f"تم إصدار إنذار {level_ar}",
        message=f"You have received warning #{warning_level}. Reason: {warning.get('reason', '')}",
        message_ar=f"تم إصدار إنذار {level_ar} بحقك. السبب: {warning.get('reason_ar', warning.get('reason', ''))}",
        priority=NotificationPriority.CRITICAL,
        reference_type="warning",
        reference_id=warning.get('id'),
        reference_url="/",
        metadata={"level": warning_level, "reason": warning.get('reason')}
    )


async def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 50) -> List[dict]:
    """جلب إشعارات المستخدم"""
    query = {"recipient_id": user_id}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return notifications


async def get_user_notifications_by_role(role: str, unread_only: bool = False, limit: int = 50) -> List[dict]:
    """جلب إشعارات حسب الدور"""
    query = {"recipient_role": role}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return notifications


async def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """تحديد إشعار كمقروء"""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.notifications.update_one(
        {"id": notification_id, "recipient_id": user_id},
        {"$set": {"is_read": True, "read_at": now}}
    )
    return result.modified_count > 0


async def mark_all_notifications_read(user_id: str) -> int:
    """تحديد جميع الإشعارات كمقروءة"""
    now = datetime.now(timezone.utc).isoformat()
    result = await db.notifications.update_many(
        {"recipient_id": user_id, "is_read": False},
        {"$set": {"is_read": True, "read_at": now}}
    )
    return result.modified_count


async def get_unread_count(user_id: str) -> int:
    """عدد الإشعارات غير المقروءة"""
    count = await db.notifications.count_documents({
        "recipient_id": user_id,
        "is_read": False
    })
    return count


async def delete_old_notifications(days: int = 30):
    """حذف الإشعارات القديمة"""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = await db.notifications.delete_many({
        "created_at": {"$lt": cutoff},
        "is_read": True
    })
    return result.deleted_count
