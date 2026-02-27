"""
Security Management APIs - نظام إدارة الأمان المتقدم
====================================================
- تعطيل/تفعيل حسابات الموظفين
- حظر الأجهزة
- سجل الأمان
- كشف التلاعب
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security"])


def require_stas(user=Depends(get_current_user)):
    """التحقق من صلاحية STAS فقط"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="هذا الإجراء متاح فقط لـ STAS")
    return user


# ==================== Models ====================

class SuspendRequest(BaseModel):
    employee_ids: List[str]  # قائمة الموظفين
    reason: str  # سبب التعطيل
    duration_hours: Optional[int] = None  # مدة التعطيل (None = دائم حتى الإلغاء)
    notify_employee: bool = True  # إرسال إشعار


class UnblockRequest(BaseModel):
    employee_ids: List[str]
    reason: str


class BlockDeviceRequest(BaseModel):
    device_signature: str
    reason: str


# ==================== تعطيل الحسابات ====================

@router.post("/suspend-accounts")
async def suspend_accounts(req: SuspendRequest, request: Request, user=Depends(require_stas)):
    """
    تعطيل حساب موظف أو أكثر
    - يمنع تسجيل الدخول
    - يسجل الخروج الإجباري لجميع الجلسات النشطة
    - يحفظ سجل الإجراء
    """
    suspended_count = 0
    errors = []
    
    for emp_id in req.employee_ids:
        try:
            # جلب بيانات الموظف
            employee = await db.employees.find_one({"id": emp_id})
            if not employee:
                errors.append(f"الموظف {emp_id} غير موجود")
                continue
            
            # حساب وقت انتهاء التعطيل
            suspended_until = None
            if req.duration_hours:
                suspended_until = (datetime.now(timezone.utc) + timedelta(hours=req.duration_hours)).isoformat()
            
            # تحديث حالة المستخدم
            await db.users.update_one(
                {"employee_id": emp_id},
                {
                    "$set": {
                        "is_suspended": True,
                        "suspended_at": datetime.now(timezone.utc).isoformat(),
                        "suspended_until": suspended_until,
                        "suspended_by": user.get('user_id'),
                        "suspend_reason": req.reason
                    }
                }
            )
            
            # إنهاء جميع الجلسات النشطة
            await db.login_sessions.update_many(
                {"employee_id": emp_id, "status": "active"},
                {
                    "$set": {
                        "status": "force_logout",
                        "logout_at": datetime.now(timezone.utc).isoformat(),
                        "logout_reason": "account_suspended"
                    }
                }
            )
            
            # تسجيل في سجل الأمان
            await db.security_log.insert_one({
                "id": str(uuid.uuid4()),
                "action": "account_suspended",
                "employee_id": emp_id,
                "employee_name": employee.get('full_name_ar', ''),
                "performed_by": user.get('user_id'),
                "performed_by_name": user.get('full_name', ''),
                "reason": req.reason,
                "duration_hours": req.duration_hours,
                "suspended_until": suspended_until,
                "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            suspended_count += 1
            logger.info(f"Account suspended: {emp_id} by {user.get('user_id')}, reason: {req.reason}")
            
        except Exception as e:
            logger.error(f"Error suspending {emp_id}: {e}")
            errors.append(f"خطأ في تعطيل {emp_id}: {str(e)}")
    
    return {
        "success": True,
        "suspended_count": suspended_count,
        "errors": errors,
        "message_ar": f"تم تعطيل {suspended_count} حساب بنجاح"
    }


@router.post("/unblock-accounts")
async def unblock_accounts(req: UnblockRequest, request: Request, user=Depends(require_stas)):
    """
    إلغاء تعطيل حساب موظف أو أكثر
    """
    unblocked_count = 0
    errors = []
    
    for emp_id in req.employee_ids:
        try:
            # تحديث حالة المستخدم
            result = await db.users.update_one(
                {"employee_id": emp_id},
                {
                    "$set": {
                        "is_suspended": False,
                        "unblocked_at": datetime.now(timezone.utc).isoformat(),
                        "unblocked_by": user.get('user_id'),
                        "unblock_reason": req.reason
                    },
                    "$unset": {
                        "suspended_until": ""
                    }
                }
            )
            
            if result.modified_count > 0:
                # جلب اسم الموظف
                employee = await db.employees.find_one({"id": emp_id})
                emp_name = employee.get('full_name_ar', '') if employee else ''
                
                # تسجيل في سجل الأمان
                await db.security_log.insert_one({
                    "id": str(uuid.uuid4()),
                    "action": "account_unblocked",
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "performed_by": user.get('user_id'),
                    "performed_by_name": user.get('full_name', ''),
                    "reason": req.reason,
                    "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
                
                unblocked_count += 1
                logger.info(f"Account unblocked: {emp_id} by {user.get('user_id')}")
            else:
                errors.append(f"الموظف {emp_id} غير موجود أو غير معطل")
                
        except Exception as e:
            logger.error(f"Error unblocking {emp_id}: {e}")
            errors.append(f"خطأ في إلغاء تعطيل {emp_id}")
    
    return {
        "success": True,
        "unblocked_count": unblocked_count,
        "errors": errors,
        "message_ar": f"تم إلغاء تعطيل {unblocked_count} حساب بنجاح"
    }


@router.post("/force-logout/{employee_id}")
async def force_logout(employee_id: str, request: Request, user=Depends(require_stas)):
    """
    تسجيل خروج إجباري لموظف معين من جميع الأجهزة
    """
    result = await db.login_sessions.update_many(
        {"employee_id": employee_id, "status": "active"},
        {
            "$set": {
                "status": "force_logout",
                "logout_at": datetime.now(timezone.utc).isoformat(),
                "logout_reason": "forced_by_admin",
                "forced_by": user.get('user_id')
            }
        }
    )
    
    # تسجيل في سجل الأمان
    employee = await db.employees.find_one({"id": employee_id})
    await db.security_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "force_logout",
        "employee_id": employee_id,
        "employee_name": employee.get('full_name_ar', '') if employee else '',
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "sessions_closed": result.modified_count,
        "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "sessions_closed": result.modified_count,
        "message_ar": f"تم إنهاء {result.modified_count} جلسة نشطة"
    }


@router.post("/force-logout-all")
async def force_logout_all(request: Request, user=Depends(require_stas)):
    """
    تسجيل خروج إجباري لجميع المستخدمين (طوارئ)
    """
    result = await db.login_sessions.update_many(
        {"status": "active"},
        {
            "$set": {
                "status": "force_logout",
                "logout_at": datetime.now(timezone.utc).isoformat(),
                "logout_reason": "emergency_logout",
                "forced_by": user.get('user_id')
            }
        }
    )
    
    await db.security_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "emergency_logout_all",
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "sessions_closed": result.modified_count,
        "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "sessions_closed": result.modified_count,
        "message_ar": f"تم إنهاء {result.modified_count} جلسة نشطة لجميع المستخدمين"
    }


# ==================== حظر الأجهزة ====================

@router.post("/block-device")
async def block_device(req: BlockDeviceRequest, request: Request, user=Depends(require_stas)):
    """
    حظر جهاز معين من تسجيل الدخول
    """
    await db.blocked_devices.insert_one({
        "id": str(uuid.uuid4()),
        "device_signature": req.device_signature,
        "reason": req.reason,
        "blocked_by": user.get('user_id'),
        "blocked_by_name": user.get('full_name', ''),
        "blocked_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    })
    
    await db.security_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "device_blocked",
        "device_signature": req.device_signature,
        "performed_by": user.get('user_id'),
        "performed_by_name": user.get('full_name', ''),
        "reason": req.reason,
        "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"success": True, "message_ar": "تم حظر الجهاز بنجاح"}


@router.delete("/unblock-device/{device_signature}")
async def unblock_device(device_signature: str, request: Request, user=Depends(require_stas)):
    """
    إلغاء حظر جهاز
    """
    result = await db.blocked_devices.update_one(
        {"device_signature": device_signature},
        {"$set": {"is_active": False, "unblocked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count > 0:
        await db.security_log.insert_one({
            "id": str(uuid.uuid4()),
            "action": "device_unblocked",
            "device_signature": device_signature,
            "performed_by": user.get('user_id'),
            "performed_by_name": user.get('full_name', ''),
            "ip_address": request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"success": True, "message_ar": "تم إلغاء حظر الجهاز"}


# ==================== الحسابات المعطلة ====================

@router.get("/suspended-accounts")
async def get_suspended_accounts(user=Depends(require_stas)):
    """
    جلب قائمة الحسابات المعطلة
    """
    suspended_users = await db.users.find(
        {"is_suspended": True},
        {"_id": 0, "password_hash": 0}
    ).to_list(100)
    
    # إضافة بيانات الموظف
    result = []
    for u in suspended_users:
        emp = await db.employees.find_one(
            {"id": u.get('employee_id')},
            {"_id": 0, "full_name_ar": 1, "employee_number": 1, "department": 1}
        )
        result.append({
            **u,
            "employee_name_ar": emp.get('full_name_ar', '') if emp else '',
            "employee_number": emp.get('employee_number', '') if emp else '',
            "department": emp.get('department', '') if emp else ''
        })
    
    return result


# ==================== سجل الأمان ====================

@router.get("/security-log")
async def get_security_log(
    limit: int = 50,
    action_type: Optional[str] = None,
    employee_id: Optional[str] = None,
    user=Depends(require_stas)
):
    """
    جلب سجل الأمان
    """
    query = {}
    if action_type:
        query["action"] = action_type
    if employee_id:
        query["employee_id"] = employee_id
    
    logs = await db.security_log.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return logs


# ==================== إحصائيات الأمان ====================

@router.get("/stats")
async def get_security_stats(user=Depends(require_stas)):
    """
    إحصائيات الأمان
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # الجلسات النشطة
    active_sessions = await db.login_sessions.count_documents({"status": "active"})
    
    # الحسابات المعطلة
    suspended_accounts = await db.users.count_documents({"is_suspended": True})
    
    # الأجهزة المحظورة
    blocked_devices = await db.blocked_devices.count_documents({"is_active": True})
    
    # تسجيلات الدخول اليوم
    logins_today = await db.login_sessions.count_documents({
        "login_at": {"$gte": today_start.isoformat()}
    })
    
    # التنبيهات الأمنية (التلاعب المكتشف)
    alerts_today = await db.security_log.count_documents({
        "action": {"$in": ["fraud_detected", "suspicious_login", "device_mismatch"]},
        "created_at": {"$gte": today_start.isoformat()}
    })
    
    # أجهزة جديدة اليوم
    new_devices_today = await db.employee_devices.count_documents({
        "registered_at": {"$gte": today_start.isoformat()}
    })
    
    return {
        "active_sessions": active_sessions,
        "suspended_accounts": suspended_accounts,
        "blocked_devices": blocked_devices,
        "logins_today": logins_today,
        "alerts_today": alerts_today,
        "new_devices_today": new_devices_today
    }


# ==================== كشف التلاعب ====================

@router.get("/fraud-alerts")
async def get_fraud_alerts(user=Depends(require_stas)):
    """
    جلب تنبيهات التلاعب المكتشفة
    """
    from services.advanced_device_analysis import detect_fraud_indicators
    
    alerts = []
    
    # 1. كشف الأجهزة المشتركة بين موظفين
    pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {
            "_id": "$core_signature",
            "employees": {"$addToSet": "$employee_id"},
            "count": {"$sum": 1}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    
    shared_devices = await db.login_sessions.aggregate(pipeline).to_list(50)
    
    for device in shared_devices:
        if len(device['employees']) > 1:
            # جلب أسماء الموظفين
            emp_names = []
            for emp_id in device['employees']:
                emp = await db.employees.find_one({"id": emp_id}, {"full_name_ar": 1})
                if emp:
                    emp_names.append(emp.get('full_name_ar', emp_id))
            
            alerts.append({
                "id": str(uuid.uuid4()),
                "type": "shared_device",
                "severity": "critical",
                "title_ar": "جهاز مشترك بين موظفين",
                "message_ar": f"نفس الجهاز يستخدمه: {', '.join(emp_names)}",
                "employees": device['employees'],
                "employee_names": emp_names,
                "device_signature": device['_id'],
                "detected_at": datetime.now(timezone.utc).isoformat()
            })
    
    # 2. كشف الجلسات المتزامنة
    active_sessions = await db.login_sessions.find(
        {"status": "active"},
        {"_id": 0}
    ).to_list(500)
    
    # تجميع حسب الموظف
    emp_sessions = {}
    for session in active_sessions:
        emp_id = session.get('employee_id')
        if emp_id not in emp_sessions:
            emp_sessions[emp_id] = []
        emp_sessions[emp_id].append(session)
    
    # كشف موظف له أكثر من جلسة نشطة من أجهزة مختلفة
    for emp_id, sessions in emp_sessions.items():
        if len(sessions) > 1:
            signatures = set(s.get('core_signature') for s in sessions if s.get('core_signature'))
            if len(signatures) > 1:
                emp = await db.employees.find_one({"id": emp_id}, {"full_name_ar": 1})
                alerts.append({
                    "id": str(uuid.uuid4()),
                    "type": "concurrent_sessions",
                    "severity": "high",
                    "title_ar": "جلسات متزامنة من أجهزة مختلفة",
                    "message_ar": f"{emp.get('full_name_ar', emp_id)} نشط على {len(signatures)} أجهزة مختلفة",
                    "employee_id": emp_id,
                    "employee_name": emp.get('full_name_ar', '') if emp else '',
                    "session_count": len(sessions),
                    "device_count": len(signatures),
                    "detected_at": datetime.now(timezone.utc).isoformat()
                })
    
    # ترتيب حسب الخطورة
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 99))
    
    return alerts


@router.get("/device-usage/{employee_id}")
async def get_employee_device_usage(employee_id: str, user=Depends(require_stas)):
    """
    جلب تفاصيل استخدام الأجهزة لموظف معين
    """
    # جلب بيانات الموظف
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # جلب الأجهزة المسجلة
    devices = await db.employee_devices.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(50)
    
    # جلب آخر 50 جلسة
    sessions = await db.login_sessions.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("login_at", -1).limit(50).to_list(50)
    
    # جلب المستخدم
    user_data = await db.users.find_one(
        {"employee_id": employee_id},
        {"_id": 0, "password_hash": 0}
    )
    
    return {
        "employee": employee,
        "user": user_data,
        "devices": devices,
        "recent_sessions": sessions,
        "is_suspended": user_data.get('is_suspended', False) if user_data else False,
        "suspend_reason": user_data.get('suspend_reason', '') if user_data else ''
    }
