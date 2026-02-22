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
    company_name_ar: Optional[str] = None
    company_name_en: Optional[str] = None
    

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
    if req.company_name_ar is not None:
        update_data["company_name_ar"] = req.company_name_ar
    if req.company_name_en is not None:
        update_data["company_name_en"] = req.company_name_en
    
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


# ============================================================
# PWA ICON MANAGEMENT - إدارة أيقونات التطبيق
# ============================================================

@router.post("/upload-pwa-icon")
async def upload_pwa_icon(
    file: UploadFile = File(...),
    user=Depends(require_roles('stas'))
):
    """
    Upload PWA icon. This will be used for app icons on all devices.
    Accepts PNG, JPG (512x512 recommended).
    STAS only.
    """
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="نوع الملف غير مدعوم. يُقبل PNG, JPG فقط")
    
    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف أكبر من 2MB")
    
    # Convert to base64 data URL
    mime_type = file.content_type
    base64_data = base64.b64encode(content).decode('utf-8')
    data_url = f"data:{mime_type};base64,{base64_data}"
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Save to database
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "pwa_icon_url": data_url,
                "pwa_icon_filename": file.filename,
                "pwa_icon_updated_at": now,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        },
        upsert=True
    )
    
    # Also save the raw bytes to serve as actual icon files
    await db.company_settings.update_one(
        {"key": "pwa_icons"},
        {
            "$set": {
                "icon_data": base64_data,
                "mime_type": mime_type,
                "updated_at": now,
                "version": str(uuid.uuid4())[:8]
            }
        },
        upsert=True
    )
    
    return {
        "message": "تم رفع أيقونة التطبيق بنجاح",
        "pwa_icon_url": data_url
    }


@router.delete("/pwa-icon")
async def delete_pwa_icon(user=Depends(require_roles('stas'))):
    """Delete PWA icon - will revert to default"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.company_settings.update_one(
        {"key": "login_page"},
        {
            "$set": {
                "pwa_icon_url": None,
                "pwa_icon_filename": None,
                "updated_at": now,
                "updated_by": user["user_id"]
            }
        }
    )
    
    await db.company_settings.delete_one({"key": "pwa_icons"})
    
    return {"message": "تم حذف أيقونة التطبيق"}


@router.get("/pwa-icon/{size}")
async def get_pwa_icon(size: str):
    """
    Get PWA icon in requested size. No auth required.
    Sizes: 192, 512, 180 (apple-touch)
    Returns the actual image file.
    """
    from fastapi.responses import Response
    from PIL import Image
    from io import BytesIO
    
    # Get icon from database
    icon_data = await db.company_settings.find_one({"key": "pwa_icons"})
    
    if not icon_data or not icon_data.get("icon_data"):
        # Fall back to company logo
        settings = await db.company_settings.find_one({"key": "login_page"})
        if settings and settings.get("logo_url"):
            # Extract base64 from data URL
            logo_url = settings["logo_url"]
            if logo_url.startswith("data:"):
                parts = logo_url.split(",", 1)
                if len(parts) == 2:
                    base64_data = parts[1]
                    mime_type = parts[0].split(":")[1].split(";")[0]
                else:
                    raise HTTPException(status_code=404, detail="Icon not found")
            else:
                raise HTTPException(status_code=404, detail="Icon not found")
        else:
            raise HTTPException(status_code=404, detail="Icon not found")
    else:
        base64_data = icon_data["icon_data"]
        mime_type = icon_data.get("mime_type", "image/png")
    
    # Decode base64
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid icon data")
    
    # Parse requested size
    try:
        target_size = int(size)
        if target_size not in [32, 180, 192, 512]:
            target_size = 512
    except ValueError:
        target_size = 512
    
    # Resize image
    try:
        img = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed (for PNG with transparency, add white background)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize
        img = img.resize((target_size, target_size), Image.LANCZOS)
        
        # Save to bytes
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        
        return Response(
            content=output.read(),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename=icon-{target_size}.png"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process icon: {str(e)}")
