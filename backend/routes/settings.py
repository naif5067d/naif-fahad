"""
Company Branding Settings API
Allows STAS to configure company logo, name, and slogan.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone
import base64
import uuid

router = APIRouter(prefix="/api/settings", tags=["settings"])


class CompanyBrandingUpdate(BaseModel):
    company_name_en: Optional[str] = None
    company_name_ar: Optional[str] = None
    slogan_en: Optional[str] = None
    slogan_ar: Optional[str] = None


@router.get("/branding")
async def get_company_branding(user=Depends(get_current_user)):
    """Get company branding settings - accessible to all authenticated users"""
    settings = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    if not settings:
        # Return default settings
        return {
            "type": "company_branding",
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_url": None,
            "logo_data": None,
            "updated_at": None,
            "updated_by": None
        }
    return settings


@router.put("/branding")
async def update_company_branding(body: CompanyBrandingUpdate, user=Depends(get_current_user)):
    """Update company branding - STAS only"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه تحديث هوية الشركة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get existing settings or create new
    existing = await db.settings.find_one({"type": "company_branding"})
    
    update_data = {
        "type": "company_branding",
        "updated_at": now,
        "updated_by": user.get('user_id')
    }
    
    # Only update provided fields
    if body.company_name_en is not None:
        update_data["company_name_en"] = body.company_name_en
    if body.company_name_ar is not None:
        update_data["company_name_ar"] = body.company_name_ar
    if body.slogan_en is not None:
        update_data["slogan_en"] = body.slogan_en
    if body.slogan_ar is not None:
        update_data["slogan_ar"] = body.slogan_ar
    
    if existing:
        await db.settings.update_one(
            {"type": "company_branding"},
            {"$set": update_data}
        )
    else:
        # Create with defaults + updates
        full_settings = {
            "type": "company_branding",
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_url": None,
            "logo_data": None,
            **update_data
        }
        await db.settings.insert_one(full_settings)
    
    # Return updated settings
    result = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    return result


@router.post("/branding/logo")
async def upload_company_logo(file: UploadFile = File(...), user=Depends(get_current_user)):
    """Upload company logo - STAS only, no size restrictions"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه رفع شعار الشركة")
    
    # Read file content
    content = await file.read()
    
    # Convert to base64 for storage
    content_type = file.content_type or 'image/png'
    base64_data = base64.b64encode(content).decode('utf-8')
    logo_data = f"data:{content_type};base64,{base64_data}"
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update or create settings
    existing = await db.settings.find_one({"type": "company_branding"})
    
    if existing:
        await db.settings.update_one(
            {"type": "company_branding"},
            {"$set": {
                "logo_data": logo_data,
                "logo_updated_at": now,
                "updated_at": now,
                "updated_by": user.get('user_id')
            }}
        )
    else:
        await db.settings.insert_one({
            "type": "company_branding",
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي",
            "logo_data": logo_data,
            "logo_updated_at": now,
            "updated_at": now,
            "updated_by": user.get('user_id')
        })
    
    return {"message": "Logo uploaded successfully", "logo_updated_at": now}


@router.delete("/branding/logo")
async def delete_company_logo(user=Depends(get_current_user)):
    """Delete company logo - STAS only"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه حذف شعار الشركة")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.settings.update_one(
        {"type": "company_branding"},
        {"$set": {
            "logo_data": None,
            "logo_url": None,
            "updated_at": now,
            "updated_by": user.get('user_id')
        }}
    )
    
    return {"message": "Logo deleted successfully"}


# ==================== إدارة إصدار التطبيق ====================

class VersionUpdate(BaseModel):
    version: str
    release_notes_en: Optional[str] = None
    release_notes_ar: Optional[str] = None


@router.get("/version")
async def get_app_version(user=Depends(get_current_user)):
    """Get current app version - accessible to all authenticated users"""
    version_info = await db.settings.find_one({"type": "app_version"}, {"_id": 0})
    if not version_info:
        # Return default version
        return {
            "type": "app_version",
            "version": "1.0.0",
            "release_notes_en": "Initial release",
            "release_notes_ar": "الإصدار الأول",
            "updated_at": None,
            "updated_by": None
        }
    return version_info


@router.put("/version")
async def update_app_version(body: VersionUpdate, user=Depends(get_current_user)):
    """Update app version - STAS only"""
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه تحديث إصدار التطبيق")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "type": "app_version",
        "version": body.version,
        "release_notes_en": body.release_notes_en or "",
        "release_notes_ar": body.release_notes_ar or "",
        "updated_at": now,
        "updated_by": user.get('user_id')
    }
    
    existing = await db.settings.find_one({"type": "app_version"})
    
    if existing:
        # حفظ تاريخ الإصدارات السابقة
        version_history = existing.get("version_history", [])
        version_history.append({
            "version": existing.get("version"),
            "updated_at": existing.get("updated_at"),
            "updated_by": existing.get("updated_by")
        })
        update_data["version_history"] = version_history[-10:]  # احتفاظ بآخر 10 إصدارات
        
        await db.settings.update_one(
            {"type": "app_version"},
            {"$set": update_data}
        )
    else:
        update_data["version_history"] = []
        await db.settings.insert_one(update_data)
    
    result = await db.settings.find_one({"type": "app_version"}, {"_id": 0})
    return result


@router.post("/version/check-update")
async def check_for_update(user=Depends(get_current_user)):
    """
    Check if client needs to update.
    يتحقق من وجود تحديث للتطبيق
    """
    version_info = await db.settings.find_one({"type": "app_version"}, {"_id": 0})
    if not version_info:
        return {
            "update_available": False,
            "current_version": "1.0.0",
            "message_en": "No updates available",
            "message_ar": "لا توجد تحديثات متاحة"
        }
    
    return {
        "update_available": True,
        "current_version": version_info.get("version", "1.0.0"),
        "release_notes_en": version_info.get("release_notes_en", ""),
        "release_notes_ar": version_info.get("release_notes_ar", ""),
        "updated_at": version_info.get("updated_at"),
        "message_en": f"Version {version_info.get('version', '1.0.0')} is available",
        "message_ar": f"الإصدار {version_info.get('version', '1.0.0')} متاح"
    }


# ==================== سماح التعويض الشهري (Smart Hours) ====================

class CompensationAllowanceUpdate(BaseModel):
    """
    إعداد سماح التعويض الشهري
    يحدد عدد الساعات التي يمكن للموظفين تعويض تأخيراتهم خلالها
    """
    monthly_compensation_hours: int  # 0-50 ساعة


@router.get("/compensation-allowance")
async def get_compensation_allowance(user=Depends(get_current_user)):
    """
    الحصول على إعداد سماح التعويض - للمدراء فقط
    الموظف العادي لا يرى هذا الإعداد
    """
    # فقط المدراء يمكنهم رؤية هذا الإعداد
    if user.get('role') not in ['stas', 'sultan', 'naif', 'salah', 'mohammed']:
        raise HTTPException(status_code=403, detail="غير مصرح لك بالوصول لهذا الإعداد")
    
    settings = await db.settings.find_one({"type": "compensation_allowance"}, {"_id": 0})
    if not settings:
        # إرجاع القيمة الافتراضية
        return {
            "type": "compensation_allowance",
            "monthly_compensation_hours": 0,
            "updated_at": None,
            "updated_by": None,
            "description_ar": "سماح التعويض الشهري - عدد الساعات التي يمكن للموظفين تعويض تأخيراتهم خلالها",
            "description_en": "Monthly compensation allowance - hours employees can use to offset their delays"
        }
    return settings


@router.put("/compensation-allowance")
async def update_compensation_allowance(body: CompensationAllowanceUpdate, user=Depends(get_current_user)):
    """
    تحديث سماح التعويض الشهري - للمدراء فقط (stas, sultan, naif)
    
    القيم المسموحة: 0-50 ساعة
    - 0 = لا يوجد سماح تعويض
    - 2 = الموظف يمكنه تعويض ساعتين من تأخيراته
    - 30 = الموظف يمكنه تعويض 30 ساعة من تأخيراته
    """
    if user.get('role') not in ['stas', 'sultan', 'naif']:
        raise HTTPException(status_code=403, detail="فقط المدراء يمكنهم تحديث هذا الإعداد")
    
    # التحقق من القيمة
    hours = max(0, min(50, body.monthly_compensation_hours))
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "type": "compensation_allowance",
        "monthly_compensation_hours": hours,
        "updated_at": now,
        "updated_by": user.get('user_id'),
        "updated_by_name": user.get('full_name', user.get('username', '')),
        "description_ar": "سماح التعويض الشهري - عدد الساعات التي يمكن للموظفين تعويض تأخيراتهم خلالها",
        "description_en": "Monthly compensation allowance - hours employees can use to offset their delays"
    }
    
    existing = await db.settings.find_one({"type": "compensation_allowance"})
    
    if existing:
        # حفظ تاريخ التغييرات
        history = existing.get("change_history", [])
        history.append({
            "previous_value": existing.get("monthly_compensation_hours"),
            "new_value": hours,
            "changed_at": now,
            "changed_by": user.get('user_id'),
            "changed_by_name": user.get('full_name', user.get('username', ''))
        })
        update_data["change_history"] = history[-20:]  # احتفاظ بآخر 20 تغيير
        
        await db.settings.update_one(
            {"type": "compensation_allowance"},
            {"$set": update_data}
        )
    else:
        update_data["change_history"] = []
        await db.settings.insert_one(update_data)
    
    result = await db.settings.find_one({"type": "compensation_allowance"}, {"_id": 0})
    return result
