"""
Device Management Routes - إدارة الأجهزة
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from services.device_service import (
    validate_device,
    approve_device,
    block_device,
    delete_device,
    block_account,
    unblock_account,
    check_account_blocked,
    get_employee_devices,
    get_all_devices,
    get_security_logs,
    generate_device_signature
)

router = APIRouter(prefix="/api/devices", tags=["devices"])


class FingerprintData(BaseModel):
    userAgent: str
    platform: str
    screenResolution: str
    timezone: str
    language: str
    webglVendor: Optional[str] = ""
    webglRenderer: Optional[str] = ""
    canvasFingerprint: Optional[str] = ""
    deviceMemory: Optional[str] = ""
    hardwareConcurrency: Optional[str] = ""
    touchSupport: Optional[str] = ""
    cookiesEnabled: Optional[str] = ""
    localStorageEnabled: Optional[str] = ""


class DeviceActionRequest(BaseModel):
    reason: Optional[str] = ""


# ==================== DEVICE VALIDATION ====================

@router.post("/validate")
async def validate_employee_device(req: FingerprintData, user=Depends(get_current_user)):
    """
    التحقق من صلاحية الجهاز للتبصيم
    يُستدعى قبل كل عملية تبصيم
    """
    employee_id = user.get('employee_id')
    if not employee_id:
        raise HTTPException(400, "لا يوجد حساب موظف مرتبط")
    
    result = await validate_device(employee_id, req.dict())
    
    if not result['valid']:
        return {
            "valid": False,
            "status": result['status'],
            "device_id": result.get('device_id'),
            "message_ar": result['error']['message_ar']
        }
    
    return {
        "valid": True,
        "status": result['status'],
        "device_id": result.get('device_id'),
        "is_first_device": result.get('is_first_device', False)
    }


@router.post("/signature")
async def get_device_signature(req: FingerprintData):
    """توليد بصمة الجهاز (للاختبار)"""
    signature = await generate_device_signature(req.dict())
    return {"signature": signature}


# ==================== STAS DEVICE MANAGEMENT ====================

@router.get("/all")
async def get_devices_list(
    status: Optional[str] = None,
    user=Depends(require_roles('stas'))
):
    """جلب جميع الأجهزة (STAS فقط)"""
    devices = await get_all_devices(status)
    return devices


@router.get("/pending")
async def get_pending_devices(user=Depends(require_roles('stas'))):
    """جلب الأجهزة بانتظار الاعتماد"""
    devices = await get_all_devices("pending")
    return devices


@router.get("/employee/{employee_id}")
async def get_employee_device_list(
    employee_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """جلب أجهزة موظف معين"""
    devices = await get_employee_devices(employee_id)
    return devices


@router.post("/{device_id}/approve")
async def approve_employee_device(
    device_id: str,
    user=Depends(require_roles('stas'))
):
    """اعتماد جهاز (STAS فقط)"""
    result = await approve_device(device_id, user['user_id'])
    if not result['success']:
        raise HTTPException(400, result.get('error', 'فشل في اعتماد الجهاز'))
    return result


@router.post("/{device_id}/block")
async def block_employee_device(
    device_id: str,
    req: DeviceActionRequest,
    user=Depends(require_roles('stas'))
):
    """حظر جهاز (STAS فقط)"""
    result = await block_device(device_id, user['user_id'], req.reason)
    if not result['success']:
        raise HTTPException(400, result.get('error', 'فشل في حظر الجهاز'))
    return result


@router.delete("/{device_id}")
async def delete_employee_device(
    device_id: str,
    user=Depends(require_roles('stas'))
):
    """حذف جهاز (STAS فقط)"""
    result = await delete_device(device_id, user['user_id'])
    if not result['success']:
        raise HTTPException(400, result.get('error', 'فشل في حذف الجهاز'))
    return result


# ==================== ACCOUNT BLOCK/UNBLOCK ====================

@router.post("/account/{employee_id}/block")
async def block_employee_account(
    employee_id: str,
    req: DeviceActionRequest,
    user=Depends(require_roles('stas'))
):
    """
    إيقاف حساب موظف للتحقيق (STAS فقط)
    
    - يمنع تسجيل الدخول
    - يمنع الحضور والانصراف
    - يمنع أي معاملة
    """
    # منع حظر حسابات STAS
    if employee_id in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF', 'EMP-SULTAN']:
        raise HTTPException(403, "لا يمكن إيقاف حساب مستخدم إداري")
    
    result = await block_account(employee_id, user['user_id'], req.reason)
    return result


@router.post("/account/{employee_id}/unblock")
async def unblock_employee_account(
    employee_id: str,
    user=Depends(require_roles('stas'))
):
    """إلغاء إيقاف حساب موظف (STAS فقط)"""
    result = await unblock_account(employee_id, user['user_id'])
    return result


@router.get("/account/{employee_id}/status")
async def get_account_block_status(
    employee_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """التحقق من حالة الحساب"""
    result = await check_account_blocked(employee_id)
    return result


# ==================== SECURITY AUDIT LOG ====================

@router.get("/security-logs")
async def get_security_audit_logs(
    employee_id: Optional[str] = None,
    limit: int = 100,
    user=Depends(require_roles('stas'))
):
    """جلب سجلات الأمان (STAS فقط)"""
    logs = await get_security_logs(employee_id, limit)
    return logs


@router.get("/security-logs/{employee_id}")
async def get_employee_security_logs(
    employee_id: str,
    user=Depends(require_roles('stas'))
):
    """جلب سجلات أمان موظف معين"""
    logs = await get_security_logs(employee_id, 100)
    return logs
