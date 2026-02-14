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
        raise HTTPException(status_code=403, detail="Only STAS can update company branding")
    
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
        raise HTTPException(status_code=403, detail="Only STAS can upload company logo")
    
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
        raise HTTPException(status_code=403, detail="Only STAS can delete company logo")
    
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
