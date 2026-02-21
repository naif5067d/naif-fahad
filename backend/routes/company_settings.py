"""
Company Settings Routes - إعدادات الشركة
============================================================
إعدادات الهوية البصرية لصفحة تسجيل الدخول
- شعار الشركة
- صورة الجانب الأيسر
- عبارة الترحيب
- ألوان الشركة
============================================================
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import uuid
import base64
import os

router = APIRouter(prefix="/api/company-settings", tags=["company-settings"])


# ============================================================
# MODELS
# ============================================================

class CompanySettingsUpdate(BaseModel):
    welcome_text_ar: Optional[str] = None
    welcome_text_en: Optional[str] = None
    primary_color: Optional[str] = None  # hex color
    secondary_color: Optional[str] = None  # hex color
    

# ============================================================
# GET SETTINGS (PUBLIC - No Auth Required)
# ============================================================

@router.get("/public")
async def get_public_settings():
    """
    Get company settings for login page.
    This is public - no authentication required.
    """
    settings = await db.company_settings.find_one({"key": "login_page"}, {"_id": 0})
    
    if not settings:
        # Return defaults
        return {
            "logo_url": None,
            "side_image_url": None,
            "welcome_text_ar": "أنتم الدار ونحن الكود",
            "welcome_text_en": "You are the Home, We are the Code",
            "primary_color": "#1E3A5F",  # Navy
            "secondary_color": "#A78BFA",  # Lavender
            "company_name_ar": "شركة دار الأركان",
            "company_name_en": "Dar Al Arkan"
        }
    
    return settings


# ============================================================
# GET FULL SETTINGS (STAS Only)
# ============================================================

@router.get("")
async def get_settings(user=Depends(require_roles('stas'))):
    """
    Get full company settings including metadata.
    STAS only.
    """
    settings = await db.company_settings.find_one({"key": "login_page"}, {"_id": 0})
    
    if not settings:
        return {
            "key": "login_page",
            "logo_url": None,
            "side_image_url": None,
            "welcome_text_ar": "أنتم الدار ونحن الكود",
            "welcome_text_en": "You are the Home, We are the Code",
            "primary_color": "#1E3A5F",
            "secondary_color": "#A78BFA",
            "company_name_ar": "شركة دار الأركان",
            "company_name_en": "Dar Al Arkan",
            "updated_at": None,
            "updated_by": None
        }
    
    return settings


# ============================================================
# UPDATE TEXT SETTINGS (STAS Only)
# ============================================================

@router.put("")
async def update_settings(
    req: CompanySettingsUpdate,
    user=Depends(require_roles('stas'))
):
    """
    Update company settings text fields.
    STAS only.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "updated_at": now,
        "updated_by": user["user_id"],
        "updated_by_name": user.get("full_name_ar") or user.get("full_name")
    }
    
    if req.welcome_text_ar is not None:
        update_data["welcome_text_ar"] = req.welcome_text_ar
    if req.welcome_text_en is not None:
        update_data["welcome_text_en"] = req.welcome_text_en
    if req.primary_color is not None:
        update_data["primary_color"] = req.primary_color
    if req.secondary_color is not None:
        update_data["secondary_color"] = req.secondary_color
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "تم تحديث الإعدادات بنجاح"}


# ============================================================
# UPLOAD LOGO (STAS Only)
# ============================================================

@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    user=Depends(require_roles('stas'))
):
    """
    Upload company logo.
    Accepts PNG, SVG, JPG.
    STAS only.
    """
    # Validate file type
    allowed_types = ['image/png', 'image/svg+xml', 'image/jpeg', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم. يُقبل PNG, SVG, JPG فقط")
    
    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 2MB")
    
    # Convert to base64 data URL
    file_ext = file.filename.split('.')[-1].lower()
    mime_type = file.content_type
    base64_data = base64.b64encode(content).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_data}"
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "logo_url": data_url,
                "logo_filename": file.filename,
                "logo_updated_at": now,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        },
        upsert=True
    )
    
    return {"message": "تم رفع الشعار بنجاح", "logo_url": data_url}


# ============================================================
# UPLOAD SIDE IMAGE (STAS Only)
# ============================================================

@router.post("/upload-side-image")
async def upload_side_image(
    file: UploadFile = File(...),
    user=Depends(require_roles('stas'))
):
    """
    Upload side image for login page.
    Accepts PNG, JPG, WEBP.
    STAS only.
    """
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم. يُقبل PNG, JPG, WEBP فقط")
    
    # Validate file size (max 5MB)
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 5MB")
    
    # Convert to base64 data URL
    mime_type = file.content_type
    base64_data = base64.b64encode(content).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_data}"
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "side_image_url": data_url,
                "side_image_filename": file.filename,
                "side_image_updated_at": now,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        },
        upsert=True
    )
    
    return {"message": "تم رفع الصورة الجانبية بنجاح", "side_image_url": data_url}


# ============================================================
# DELETE LOGO (STAS Only)
# ============================================================

@router.delete("/logo")
async def delete_logo(user=Depends(require_roles('stas'))):
    """Delete company logo"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "logo_url": None,
                "logo_filename": None,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        }
    )
    
    return {"message": "تم حذف الشعار"}


# ============================================================
# DELETE SIDE IMAGE (STAS Only)
# ============================================================

@router.delete("/side-image")
async def delete_side_image(user=Depends(require_roles('stas'))):
    """Delete side image"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "side_image_url": None,
                "side_image_filename": None,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        }
    )
    
    return {"message": "تم حذف الصورة الجانبية"}
