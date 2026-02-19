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


def generate_core_hardware_signature(fingerprint_data: dict) -> str:
    """
    توليد بصمة الجهاز الأساسية (Hardware Core)
    
    هذه البصمة لا تتغير بتغيير المتصفح!
    تعتمد على:
    - WebGL Vendor + Renderer (كرت الشاشة)
    - Canvas Hash
    - Hardware Concurrency (عدد أنوية المعالج)
    - Device Memory (الذاكرة)
    - Platform (نظام التشغيل)
    - Screen Resolution (دقة الشاشة)
    """
    core_values = [
        str(fingerprint_data.get('webglVendor', '')),
        str(fingerprint_data.get('webglRenderer', '')),
        str(fingerprint_data.get('canvasFingerprint', '')),
        str(fingerprint_data.get('hardwareConcurrency', '')),
        str(fingerprint_data.get('deviceMemory', '')),
        str(fingerprint_data.get('platform', '')),
        str(fingerprint_data.get('screenResolution', '')),
    ]
    
    combined = '|'.join(core_values)
    return hashlib.sha256(combined.encode()).hexdigest()


def extract_browser_info(fingerprint_data: dict) -> dict:
    """
    استخراج معلومات المتصفح (Soft Data)
    
    هذه البيانات للتسجيل فقط - لا تُستخدم للمطابقة!
    """
    user_agent = fingerprint_data.get('userAgent', '')
    device_info = _parse_user_agent(user_agent)
    
    return {
        "browser": device_info.get('browser', 'Unknown'),
        "browser_version": device_info.get('browser_version', ''),
        "language": fingerprint_data.get('language', ''),
        "timezone": fingerprint_data.get('timezone', ''),
        "user_agent": user_agent
    }


async def generate_device_signature(fingerprint_data: dict) -> str:
    """
    [DEPRECATED - استخدم generate_core_hardware_signature]
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


async def register_login_session(
    employee_id: str,
    fingerprint_data: dict,
    username: str,
    role: str
) -> dict:
    """
    تسجيل جلسة دخول للموظف مع كشف الجهاز الذكي
    
    المنطق:
    1. توليد Core Hardware Signature (لا يتغير بتغيير المتصفح)
    2. البحث عن جهاز موجود بنفس البصمة الأساسية
    3. إذا وُجد = تحديث المتصفح فقط (Same Device – Different Browser)
    4. إذا لم يُوجد = جهاز جديد
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # 1️⃣ توليد البصمة الأساسية (Hardware Core)
    core_signature = generate_core_hardware_signature(fingerprint_data)
    
    # 2️⃣ استخراج معلومات المتصفح (Soft Data)
    browser_info = extract_browser_info(fingerprint_data)
    device_info = _parse_user_agent(fingerprint_data.get('userAgent', ''))
    
    # 3️⃣ البحث عن جهاز موجود بنفس البصمة الأساسية
    existing_device = await db.employee_devices.find_one({
        "employee_id": employee_id,
        "core_signature": core_signature
    })
    
    device_status = "existing"
    device_id = None
    
    if existing_device:
        # ✅ نفس الجهاز - تحديث المتصفح فقط
        device_id = existing_device['id']
        await db.employee_devices.update_one(
            {"id": device_id},
            {"$set": {
                "browser": browser_info['browser'],
                "browser_version": browser_info['browser_version'],
                "last_browser_change": now,
                "last_used_at": now,
                "fingerprint_data": fingerprint_data
            }}
        )
        device_status = "same_device_browser_changed" if existing_device.get('browser') != browser_info['browser'] else "existing"
    else:
        # 🆕 جهاز جديد - تسجيله
        device_id = str(uuid.uuid4())
        new_device = {
            "id": device_id,
            "employee_id": employee_id,
            "core_signature": core_signature,  # البصمة الأساسية
            "device_type": device_info['device_type'],
            "device_name": device_info.get('friendly_name', 'جهاز غير معروف'),
            "device_brand": device_info.get('device_brand', ''),
            "device_model": device_info.get('device_model', ''),
            "browser": browser_info['browser'],
            "browser_version": browser_info['browser_version'],
            "os": device_info['os'],
            "os_display": device_info.get('os_display', ''),
            "is_mobile": device_info.get('is_mobile', False),
            "is_tablet": device_info.get('is_tablet', False),
            "is_pc": device_info.get('is_pc', True),
            "platform": fingerprint_data.get('platform', ''),
            "screen_resolution": fingerprint_data.get('screenResolution', ''),
            "fingerprint_data": fingerprint_data,
            "status": "trusted",  # موثوق تلقائياً
            "registered_at": now,
            "last_used_at": now
        }
        await db.employee_devices.insert_one(new_device)
        device_status = "new_device"
    
    # 4️⃣ تسجيل الجلسة
    session = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "username": username,
        "role": role,
        "device_id": device_id,
        "core_signature": core_signature,
        "login_at": now,
        "logout_at": None,
        "device_type": device_info['device_type'],
        "device_name": device_info.get('friendly_name', 'جهاز غير معروف'),
        "browser": browser_info['browser'],
        "os": device_info['os'],
        "os_display": device_info.get('os_display', ''),
        "is_mobile": device_info.get('is_mobile', False),
        "device_status": device_status,  # existing / new_device / same_device_browser_changed
        "fingerprint_data": fingerprint_data,
        "status": "active"
    }
    
    await db.login_sessions.insert_one(session)
    session.pop('_id', None)
    
    return session


async def register_logout_session(employee_id: str) -> dict:
    """تسجيل خروج الموظف"""
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث آخر جلسة نشطة
    result = await db.login_sessions.update_one(
        {"employee_id": employee_id, "status": "active"},
        {"$set": {"logout_at": now, "status": "completed"}},
        sort=[("login_at", -1)]
    )
    
    return {"updated": result.modified_count > 0}




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


async def reset_employee_devices(employee_id: str, reset_by: str) -> dict:
    """
    إعادة تعيين جميع أجهزة الموظف
    يُستخدم من قبل STAS لتغيير جهاز الموظف
    """
    # حذف جميع الأجهزة المسجلة
    result = await db.employee_devices.delete_many({"employee_id": employee_id})
    
    await log_security_event(
        employee_id=employee_id,
        action="all_devices_reset",
        performed_by=reset_by,
        details={"deleted_count": result.deleted_count}
    )
    
    return {
        "success": True,
        "deleted_count": result.deleted_count,
        "message_ar": f"تم حذف {result.deleted_count} جهاز. الجهاز القادم سيُعتمد تلقائياً."
    }


async def set_device_as_primary(employee_id: str, device_id: str, set_by: str) -> dict:
    """
    تعيين جهاز كجهاز رئيسي للموظف
    وحظر باقي الأجهزة
    """
    # التحقق من وجود الجهاز
    device = await db.employee_devices.find_one({"id": device_id})
    if not device:
        return {"success": False, "error": "الجهاز غير موجود"}
    
    if device['employee_id'] != employee_id:
        return {"success": False, "error": "الجهاز لا ينتمي لهذا الموظف"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تعيين الجهاز المختار كموثوق
    await db.employee_devices.update_one(
        {"id": device_id},
        {"$set": {
            "status": "trusted",
            "approved_by": set_by,
            "approved_at": now
        }}
    )
    
    # حظر باقي الأجهزة
    await db.employee_devices.update_many(
        {
            "employee_id": employee_id,
            "id": {"$ne": device_id}
        },
        {"$set": {
            "status": "blocked",
            "blocked_by": set_by,
            "blocked_at": now,
            "block_reason": "تم تعيين جهاز آخر كجهاز رئيسي"
        }}
    )
    
    await log_security_event(
        employee_id=employee_id,
        action="device_set_as_primary",
        device_signature=device['device_signature'],
        performed_by=set_by,
        details={"device_id": device_id}
    )
    
    return {
        "success": True,
        "message_ar": "تم تعيين الجهاز كجهاز رئيسي"
    }


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
    """جلب جميع الأجهزة (للـ STAS) مع معلومات محسّنة"""
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    devices = await db.employee_devices.find(
        query,
        {"_id": 0}
    ).sort("registered_at", -1).to_list(500)
    
    # إضافة بيانات الموظف ومعلومات الجهاز المحسّنة
    for device in devices:
        emp = await db.employees.find_one(
            {"id": device['employee_id']},
            {"_id": 0, "full_name_ar": 1, "employee_number": 1}
        )
        device['employee_name_ar'] = emp.get('full_name_ar', '') if emp else ''
        device['employee_number'] = emp.get('employee_number', '') if emp else ''
        
        # تحليل User-Agent للحصول على معلومات سهلة
        fingerprint = device.get('fingerprint_data', {})
        ua_string = fingerprint.get('userAgent', '')
        if ua_string:
            parsed = _parse_user_agent(ua_string)
            device['friendly_name'] = parsed.get('friendly_name', 'جهاز غير معروف')
            device['device_brand'] = parsed.get('device_brand', '')
            device['device_model'] = parsed.get('device_model', '')
            device['os_display'] = parsed.get('os_display', device.get('os', ''))
            device['is_mobile'] = parsed.get('is_mobile', False)
            device['is_tablet'] = parsed.get('is_tablet', False)
            device['is_pc'] = parsed.get('is_pc', True)
        else:
            device['friendly_name'] = device.get('device_type', 'جهاز')
            device['os_display'] = device.get('os', '')
            device['is_mobile'] = device.get('device_type') == 'mobile'
            device['is_tablet'] = device.get('device_type') == 'tablet'
            device['is_pc'] = device.get('device_type') == 'desktop'
    
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
    """استخراج معلومات الجهاز من User Agent بشكل سهل للمستخدم"""
    from user_agents import parse
    
    try:
        ua = parse(user_agent)
        
        # تحديد نوع الجهاز بشكل واضح
        if ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        else:
            device_type = "unknown"
        
        # استخراج اسم الجهاز بشكل واضح
        device_brand = ua.device.brand or ""
        device_model = ua.device.model or ""
        device_family = ua.device.family or ""
        
        # بناء اسم جهاز سهل للمستخدم
        if device_brand and device_model:
            device_name = f"{device_brand} {device_model}"
        elif device_family and device_family != "Other":
            device_name = device_family
        elif ua.is_mobile:
            device_name = "هاتف محمول"
        elif ua.is_tablet:
            device_name = "جهاز لوحي"
        else:
            device_name = "كمبيوتر"
        
        # المتصفح
        browser = ua.browser.family or "متصفح غير معروف"
        browser_version = ua.browser.version_string or ""
        
        # نظام التشغيل
        os_name = ua.os.family or "نظام غير معروف"
        os_version = ua.os.version_string or ""
        
        # بناء اسم نظام سهل
        if os_name == "iOS":
            os_display = f"iOS {os_version}" if os_version else "iOS"
        elif os_name == "Android":
            os_display = f"أندرويد {os_version}" if os_version else "أندرويد"
        elif os_name == "Windows":
            os_display = f"ويندوز {os_version}" if os_version else "ويندوز"
        elif os_name == "Mac OS X":
            os_display = "ماك"
        else:
            os_display = os_name
        
        # اسم مختصر للعرض
        friendly_name = _get_friendly_device_name(device_type, device_brand, device_model, os_name, browser)
        
        return {
            "device_type": device_type,
            "device_name": device_name,
            "device_brand": device_brand,
            "device_model": device_model,
            "browser": browser,
            "browser_version": browser_version,
            "os": os_name,
            "os_version": os_version,
            "os_display": os_display,
            "friendly_name": friendly_name,
            "is_mobile": ua.is_mobile,
            "is_tablet": ua.is_tablet,
            "is_pc": ua.is_pc
        }
    except Exception:
        # في حالة فشل التحليل، نستخدم الطريقة القديمة
        ua_lower = user_agent.lower()
        device_type = "desktop"
        if "mobile" in ua_lower or ("android" in ua_lower and "mobile" in ua_lower):
            device_type = "mobile"
        elif "tablet" in ua_lower or "ipad" in ua_lower:
            device_type = "tablet"
        
        return {
            "device_type": device_type,
            "device_name": "جهاز غير معروف",
            "device_brand": "",
            "device_model": "",
            "browser": "متصفح",
            "browser_version": "",
            "os": "نظام",
            "os_version": "",
            "os_display": "غير معروف",
            "friendly_name": "جهاز غير معروف",
            "is_mobile": device_type == "mobile",
            "is_tablet": device_type == "tablet",
            "is_pc": device_type == "desktop"
        }


def _get_friendly_device_name(device_type: str, brand: str, model: str, os_name: str, browser: str) -> str:
    """توليد اسم جهاز سهل للعرض"""
    
    # أجهزة آبل
    if brand and "apple" in brand.lower():
        if "iphone" in model.lower():
            return f"آيفون {model.replace('iPhone', '').strip()}"
        elif "ipad" in model.lower():
            return f"آيباد {model.replace('iPad', '').strip()}"
        elif os_name == "Mac OS X":
            return "ماك"
    
    # أجهزة سامسونج
    if brand and "samsung" in brand.lower():
        if model:
            return f"سامسونج {model}"
        return "جهاز سامسونج"
    
    # أجهزة هواوي
    if brand and "huawei" in brand.lower():
        if model:
            return f"هواوي {model}"
        return "جهاز هواوي"
    
    # أجهزة شاومي
    if brand and ("xiaomi" in brand.lower() or "redmi" in brand.lower()):
        if model:
            return f"شاومي {model}"
        return "جهاز شاومي"
    
    # حسب نظام التشغيل
    if os_name == "iOS":
        return "آيفون"
    elif os_name == "Android":
        if device_type == "tablet":
            return "جهاز لوحي أندرويد"
        return "هاتف أندرويد"
    elif os_name == "Windows":
        return f"كمبيوتر ويندوز ({browser})"
    elif os_name == "Mac OS X":
        return f"ماك ({browser})"
    elif os_name == "Linux":
        return f"كمبيوتر لينكس ({browser})"
    
    # افتراضي
    if device_type == "mobile":
        return "هاتف محمول"
    elif device_type == "tablet":
        return "جهاز لوحي"
    return f"كمبيوتر ({browser})"


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
