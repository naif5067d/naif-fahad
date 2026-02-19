"""
Device Fingerprint Service - خدمة بصمة الجهاز
============================================================
يتعرف على الجهاز عبر Browser Fingerprint Hybrid
لا يعتمد على IP أو User-Agent فقط
"""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List
from database import db


async def generate_device_signature(fingerprint_data: dict) -> str:
    """
    توليد بصمة فريدة للجهاز من مجموعة البيانات
    
    يستخدم:
    - User Agent
    - Platform
    - Screen Resolution
    - Timezone
    - Language
    - WebGL Vendor + Renderer
    - Canvas Fingerprint
    - Device Memory
    - Hardware Concurrency
    - Touch Support
    - Cookies/Storage Enabled
    """
    # ترتيب البيانات للحصول على hash ثابت
    values = [
        str(fingerprint_data.get('userAgent', '')),
        str(fingerprint_data.get('platform', '')),
        str(fingerprint_data.get('screenResolution', '')),
        str(fingerprint_data.get('timezone', '')),
        str(fingerprint_data.get('language', '')),
        str(fingerprint_data.get('webglVendor', '')),
        str(fingerprint_data.get('webglRenderer', '')),
        str(fingerprint_data.get('canvasFingerprint', '')),
        str(fingerprint_data.get('deviceMemory', '')),
        str(fingerprint_data.get('hardwareConcurrency', '')),
        str(fingerprint_data.get('touchSupport', '')),
        str(fingerprint_data.get('cookiesEnabled', '')),
        str(fingerprint_data.get('localStorageEnabled', '')),
    ]
    
    combined = '|'.join(values)
    signature = hashlib.sha256(combined.encode()).hexdigest()
    
    return signature


async def register_device(
    employee_id: str,
    fingerprint_data: dict,
    is_first_device: bool = False
) -> dict:
    """
    تسجيل جهاز جديد للموظف
    
    الحالات:
    - أول جهاز: يُعتمد تلقائياً
    - جهاز جديد: يُسجل بحالة pending (بانتظار اعتماد STAS)
    """
    signature = await generate_device_signature(fingerprint_data)
    now = datetime.now(timezone.utc).isoformat()
    
    # التحقق إذا الجهاز موجود مسبقاً
    existing = await db.employee_devices.find_one({
        "employee_id": employee_id,
        "device_signature": signature
    })
    
    if existing:
        # تحديث آخر استخدام
        await db.employee_devices.update_one(
            {"id": existing['id']},
            {"$set": {
                "last_used_at": now,
                "usage_count": existing.get('usage_count', 0) + 1
            }}
        )
        return {
            "device_id": existing['id'],
            "status": existing['status'],
            "is_new": False,
            "signature": signature
        }
    
    # جهاز جديد
    device_id = str(uuid.uuid4())
    
    # استخراج معلومات الجهاز للعرض
    user_agent = fingerprint_data.get('userAgent', '')
    device_info = _parse_user_agent(user_agent)
    
    device = {
        "id": device_id,
        "employee_id": employee_id,
        "device_signature": signature,
        "fingerprint_data": fingerprint_data,
        "device_type": device_info['device_type'],
        "browser": device_info['browser'],
        "browser_version": device_info['browser_version'],
        "os": device_info['os'],
        "os_version": device_info['os_version'],
        "status": "trusted" if is_first_device else "pending",  # أول جهاز = موثوق تلقائياً
        "registered_at": now,
        "last_used_at": now,
        "usage_count": 1,
        "approved_by": "system" if is_first_device else None,
        "approved_at": now if is_first_device else None
    }
    
    await db.employee_devices.insert_one(device)
    device.pop('_id', None)
    
    # تسجيل في security_audit_log
    await log_security_event(
        employee_id=employee_id,
        action="new_device_registered",
        device_signature=signature,
        fingerprint_data=fingerprint_data,
        performed_by="system",
        details={
            "device_id": device_id,
            "is_first_device": is_first_device,
            "auto_approved": is_first_device
        }
    )
    
    return {
        "device_id": device_id,
        "status": device['status'],
        "is_new": True,
        "signature": signature
    }


async def check_device_for_login(
    employee_id: str,
    device_signature: str,
    fingerprint_data: dict
) -> dict:
    """
    التحقق من الجهاز عند تسجيل الدخول
    
    Returns:
        {
            "allowed": bool,
            "error": str,
            "message_ar": str,
            "message_en": str
        }
    """
    # التحقق من وجود أجهزة مسجلة
    devices_count = await db.employee_devices.count_documents({
        "employee_id": employee_id
    })
    
    if devices_count == 0:
        # أول جهاز - تسجيله تلقائياً
        await register_device(employee_id, fingerprint_data, is_first_device=True)
        return {"allowed": True}
    
    # البحث عن الجهاز
    device = await db.employee_devices.find_one({
        "employee_id": employee_id,
        "device_signature": device_signature
    })
    
    if not device:
        # جهاز جديد غير مسجل - تسجيله بحالة pending
        await register_device(employee_id, fingerprint_data, is_first_device=False)
        
        return {
            "allowed": False,
            "error": "NEW_DEVICE",
            "message_ar": "تم اكتشاف جهاز جديد. بانتظار اعتماد STAS. يرجى مراجعة الإدارة.",
            "message_en": "New device detected. Waiting for STAS approval."
        }
    
    # الجهاز موجود - التحقق من حالته
    if device['status'] == 'trusted':
        # تحديث آخر استخدام
        await db.employee_devices.update_one(
            {"id": device['id']},
            {"$set": {
                "last_used_at": datetime.now(timezone.utc).isoformat(),
                "usage_count": device.get('usage_count', 0) + 1
            }}
        )
        return {"allowed": True}
    
    elif device['status'] == 'pending':
        return {
            "allowed": False,
            "error": "DEVICE_PENDING",
            "message_ar": "الجهاز بانتظار اعتماد STAS. يرجى مراجعة الإدارة.",
            "message_en": "Device pending STAS approval."
        }
    
    elif device['status'] == 'blocked':
        return {
            "allowed": False,
            "error": "DEVICE_BLOCKED",
            "message_ar": "الجهاز محظور. يرجى مراجعة الإدارة.",
            "message_en": "Device blocked. Please contact administration."
        }
    
    return {
        "allowed": False,
        "error": "UNKNOWN_DEVICE_STATUS",
        "message_ar": "حالة الجهاز غير معروفة.",
        "message_en": "Unknown device status."
    }


async def validate_device(employee_id: str, fingerprint_data: dict) -> dict:
    """
    التحقق من صلاحية الجهاز للتبصيم
    
    Returns:
        {
            "valid": bool,
            "status": str (trusted/pending/blocked),
            "device_id": str,
            "error": Optional[dict]
        }
    """
    signature = await generate_device_signature(fingerprint_data)
    
    # التحقق من وجود أجهزة مسجلة
    devices_count = await db.employee_devices.count_documents({
        "employee_id": employee_id
    })
    
    if devices_count == 0:
        # أول جهاز - تسجيله تلقائياً
        result = await register_device(employee_id, fingerprint_data, is_first_device=True)
        return {
            "valid": True,
            "status": "trusted",
            "device_id": result['device_id'],
            "is_first_device": True
        }
    
    # البحث عن الجهاز
    device = await db.employee_devices.find_one({
        "employee_id": employee_id,
        "device_signature": signature
    })
    
    if not device:
        # جهاز جديد غير مسجل - تسجيله بحالة pending
        result = await register_device(employee_id, fingerprint_data, is_first_device=False)
        
        # إرسال إشعار لـ STAS
        await _notify_stas_new_device(employee_id, result['device_id'], fingerprint_data)
        
        return {
            "valid": False,
            "status": "pending",
            "device_id": result['device_id'],
            "error": {
                "code": "error.new_device",
                "message": "New device detected. Waiting for STAS approval.",
                "message_ar": "تم اكتشاف جهاز جديد. بانتظار اعتماد STAS."
            }
        }
    
    # الجهاز موجود - التحقق من حالته
    if device['status'] == 'trusted':
        # تحديث آخر استخدام
        await db.employee_devices.update_one(
            {"id": device['id']},
            {"$set": {
                "last_used_at": datetime.now(timezone.utc).isoformat(),
                "usage_count": device.get('usage_count', 0) + 1
            }}
        )
        return {
            "valid": True,
            "status": "trusted",
            "device_id": device['id']
        }
    
    elif device['status'] == 'pending':
        return {
            "valid": False,
            "status": "pending",
            "device_id": device['id'],
            "error": {
                "code": "error.device_pending",
                "message": "Device pending approval",
                "message_ar": "الجهاز بانتظار اعتماد STAS"
            }
        }
    
    elif device['status'] == 'blocked':
        return {
            "valid": False,
            "status": "blocked",
            "device_id": device['id'],
            "error": {
                "code": "error.device_blocked",
                "message": "Device blocked by administrator",
                "message_ar": "الجهاز محظور من قبل الإدارة"
            }
        }
    
    return {
        "valid": False,
        "status": device['status'],
        "device_id": device['id'],
        "error": {
            "code": "error.unknown_device_status",
            "message": "Unknown device status",
            "message_ar": "حالة الجهاز غير معروفة"
        }
    }


async def approve_device(device_id: str, approved_by: str) -> dict:
    """اعتماد جهاز من قبل STAS"""
    now = datetime.now(timezone.utc).isoformat()
    
    device = await db.employee_devices.find_one({"id": device_id})
    if not device:
        return {"success": False, "error": "الجهاز غير موجود"}
    
    await db.employee_devices.update_one(
        {"id": device_id},
        {"$set": {
            "status": "trusted",
            "approved_by": approved_by,
            "approved_at": now
        }}
    )
    
    await log_security_event(
        employee_id=device['employee_id'],
        action="device_approved",
        device_signature=device['device_signature'],
        performed_by=approved_by,
        details={"device_id": device_id}
    )
    
    return {"success": True, "message_ar": "تم اعتماد الجهاز"}


async def block_device(device_id: str, blocked_by: str, reason: str = "") -> dict:
    """حظر جهاز"""
    now = datetime.now(timezone.utc).isoformat()
    
    device = await db.employee_devices.find_one({"id": device_id})
    if not device:
        return {"success": False, "error": "الجهاز غير موجود"}
    
    await db.employee_devices.update_one(
        {"id": device_id},
        {"$set": {
            "status": "blocked",
            "blocked_by": blocked_by,
            "blocked_at": now,
            "block_reason": reason
        }}
    )
    
    await log_security_event(
        employee_id=device['employee_id'],
        action="device_blocked",
        device_signature=device['device_signature'],
        performed_by=blocked_by,
        details={"device_id": device_id, "reason": reason}
    )
    
    return {"success": True, "message_ar": "تم حظر الجهاز"}


async def delete_device(device_id: str, deleted_by: str) -> dict:
    """حذف جهاز"""
    device = await db.employee_devices.find_one({"id": device_id})
    if not device:
        return {"success": False, "error": "الجهاز غير موجود"}
    
    await db.employee_devices.delete_one({"id": device_id})
    
    await log_security_event(
        employee_id=device['employee_id'],
        action="device_deleted",
        device_signature=device['device_signature'],
        performed_by=deleted_by,
        details={"device_id": device_id}
    )
    
    return {"success": True, "message_ar": "تم حذف الجهاز"}


async def block_account(employee_id: str, blocked_by: str, reason: str = "") -> dict:
    """إيقاف حساب موظف للتحقيق"""
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث حالة الموظف
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "is_blocked": True,
            "blocked_at": now,
            "blocked_by": blocked_by,
            "block_reason": reason
        }}
    )
    
    # تحديث حالة المستخدم
    await db.users.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "is_blocked": True,
            "blocked_at": now,
            "blocked_by": blocked_by,
            "block_reason": reason
        }}
    )
    
    await log_security_event(
        employee_id=employee_id,
        action="account_blocked",
        performed_by=blocked_by,
        details={"reason": reason}
    )
    
    return {
        "success": True,
        "message_ar": "تم إيقاف الحساب للتحقيق"
    }


async def unblock_account(employee_id: str, unblocked_by: str) -> dict:
    """إلغاء إيقاف حساب موظف"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "is_blocked": False,
            "unblocked_at": now,
            "unblocked_by": unblocked_by
        },
        "$unset": {
            "blocked_at": "",
            "blocked_by": "",
            "block_reason": ""
        }}
    )
    
    await db.users.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "is_blocked": False,
            "unblocked_at": now,
            "unblocked_by": unblocked_by
        },
        "$unset": {
            "blocked_at": "",
            "blocked_by": "",
            "block_reason": ""
        }}
    )
    
    await log_security_event(
        employee_id=employee_id,
        action="account_unblocked",
        performed_by=unblocked_by
    )
    
    return {
        "success": True,
        "message_ar": "تم إلغاء إيقاف الحساب"
    }


async def check_account_blocked(employee_id: str) -> dict:
    """التحقق إذا كان الحساب محجوب"""
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if emp and emp.get('is_blocked'):
        return {
            "is_blocked": True,
            "blocked_at": emp.get('blocked_at'),
            "reason": emp.get('block_reason', ''),
            "message_ar": "تم إيقاف حسابك مؤقتاً للتحقق من تجاوزات تخالف سياسة النظام. يرجى مراجعة مقر الشركة."
        }
    
    return {"is_blocked": False}


async def log_security_event(
    employee_id: str,
    action: str,
    device_signature: str = None,
    fingerprint_data: dict = None,
    performed_by: str = "system",
    details: dict = None
):
    """تسجيل حدث أمني في security_audit_log"""
    event = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "action": action,
        "device_signature": device_signature,
        "fingerprint_data": fingerprint_data,
        "performed_by": performed_by,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.security_audit_log.insert_one(event)


async def get_employee_devices(employee_id: str) -> List[dict]:
    """جلب أجهزة موظف معين"""
    devices = await db.employee_devices.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("registered_at", -1).to_list(50)
    
    return devices


async def get_all_devices(status_filter: str = None) -> List[dict]:
    """جلب جميع الأجهزة (للـ STAS)"""
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    devices = await db.employee_devices.find(
        query,
        {"_id": 0}
    ).sort("registered_at", -1).to_list(500)
    
    # إضافة بيانات الموظف
    for device in devices:
        emp = await db.employees.find_one(
            {"id": device['employee_id']},
            {"_id": 0, "full_name_ar": 1, "employee_number": 1}
        )
        device['employee_name_ar'] = emp.get('full_name_ar', '') if emp else ''
        device['employee_number'] = emp.get('employee_number', '') if emp else ''
    
    return devices


async def get_security_logs(employee_id: str = None, limit: int = 100) -> List[dict]:
    """جلب سجلات الأمان"""
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    
    logs = await db.security_audit_log.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).to_list(limit)
    
    return logs


def _parse_user_agent(user_agent: str) -> dict:
    """استخراج معلومات الجهاز من User Agent"""
    ua = user_agent.lower()
    
    # نوع الجهاز
    device_type = "desktop"
    if "mobile" in ua or "android" in ua and "mobile" in ua:
        device_type = "mobile"
    elif "tablet" in ua or "ipad" in ua:
        device_type = "tablet"
    
    # المتصفح
    browser = "Unknown"
    browser_version = ""
    if "chrome" in ua and "edg" not in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "edg" in ua:
        browser = "Edge"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera"
    
    # نظام التشغيل
    os_name = "Unknown"
    os_version = ""
    if "windows" in ua:
        os_name = "Windows"
        if "windows nt 10" in ua:
            os_version = "10/11"
    elif "mac os" in ua or "macos" in ua:
        os_name = "macOS"
    elif "android" in ua:
        os_name = "Android"
    elif "iphone" in ua or "ipad" in ua:
        os_name = "iOS"
    elif "linux" in ua:
        os_name = "Linux"
    
    return {
        "device_type": device_type,
        "browser": browser,
        "browser_version": browser_version,
        "os": os_name,
        "os_version": os_version
    }


async def _notify_stas_new_device(employee_id: str, device_id: str, fingerprint_data: dict):
    """إرسال إشعار لـ STAS عن جهاز جديد"""
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        emp = await db.employees.find_one({"id": employee_id}, {"_id": 0, "full_name_ar": 1})
        emp_name = emp.get('full_name_ar', employee_id) if emp else employee_id
        
        device_info = _parse_user_agent(fingerprint_data.get('userAgent', ''))
        
        await create_notification(
            recipient_id="",
            notification_type=NotificationType.ALERT,
            title="New Device Detected",
            title_ar="جهاز جديد مكتشف",
            message=f"New device for {emp_name}: {device_info['browser']} on {device_info['os']}",
            message_ar=f"جهاز جديد لـ {emp_name}: {device_info['browser']} على {device_info['os']}",
            priority=NotificationPriority.HIGH,
            recipient_role="stas",
            reference_type="device",
            reference_id=device_id,
            reference_url="/stas-mirror?tab=devices"
        )
    except Exception:
        pass
