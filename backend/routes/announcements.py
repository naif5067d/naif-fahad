"""
Announcements System - إشعارات النظام
Supports:
- Regular announcements (shown once on login)
- Pinned announcements (always visible under welcome message)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from database import db
from utils.auth import get_current_user, require_roles
import uuid

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


class AnnouncementCreate(BaseModel):
    message_ar: str
    message_en: str = ""
    is_pinned: bool = False  # إشعار مثبت (هام جداً)
    expires_at: Optional[str] = None  # تاريخ انتهاء الإشعار


class AnnouncementUpdate(BaseModel):
    message_ar: Optional[str] = None
    message_en: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_active: Optional[bool] = None
    expires_at: Optional[str] = None


@router.get("")
async def get_announcements(user=Depends(get_current_user)):
    """Get all active announcements for current user"""
    now = datetime.now(timezone.utc).isoformat()
    
    # Get active announcements
    announcements = await db.announcements.find({
        "is_active": True,
        "$or": [
            {"expires_at": None},
            {"expires_at": {"$gt": now}}
        ]
    }, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    # Get user's dismissed announcements
    user_dismissed = await db.user_dismissed_announcements.find(
        {"user_id": user["user_id"]},
        {"announcement_id": 1, "_id": 0}
    ).to_list(100)
    dismissed_ids = {d["announcement_id"] for d in user_dismissed}
    
    # Filter: pinned always shown, regular only if not dismissed
    result = {
        "pinned": [],
        "regular": []
    }
    
    for ann in announcements:
        if ann["is_pinned"]:
            result["pinned"].append(ann)
        elif ann["id"] not in dismissed_ids:
            result["regular"].append(ann)
    
    return result


@router.get("/all")
async def get_all_announcements(user=Depends(require_roles('stas', 'sultan', 'mohammed'))):
    """Get all announcements (admin view)"""
    announcements = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return announcements


@router.post("")
async def create_announcement(req: AnnouncementCreate, user=Depends(require_roles('stas', 'sultan', 'mohammed'))):
    """Create a new announcement"""
    now = datetime.now(timezone.utc).isoformat()
    
    announcement = {
        "id": str(uuid.uuid4()),
        "message_ar": req.message_ar,
        "message_en": req.message_en or req.message_ar,
        "is_pinned": req.is_pinned,
        "is_active": True,
        "expires_at": req.expires_at,
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name_ar", user.get("full_name", user["username"])),
        "created_at": now,
        "updated_at": now
    }
    
    await db.announcements.insert_one(announcement)
    announcement.pop("_id", None)
    
    return announcement


@router.put("/{announcement_id}")
async def update_announcement(announcement_id: str, req: AnnouncementUpdate, user=Depends(require_roles('stas', 'sultan', 'mohammed'))):
    """Update an announcement"""
    update_data = {k: v for k, v in req.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.announcements.update_one(
        {"id": announcement_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")
    
    return {"message": "تم تحديث الإشعار"}


@router.delete("/{announcement_id}")
async def delete_announcement(announcement_id: str, user=Depends(require_roles('stas', 'sultan', 'mohammed'))):
    """Delete an announcement"""
    result = await db.announcements.delete_one({"id": announcement_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")
    
    # Also delete all dismissals for this announcement
    await db.user_dismissed_announcements.delete_many({"announcement_id": announcement_id})
    
    return {"message": "تم حذف الإشعار"}


@router.post("/{announcement_id}/dismiss")
async def dismiss_announcement(announcement_id: str, user=Depends(get_current_user)):
    """Dismiss a regular announcement (user won't see it again)"""
    # Check if announcement exists and is not pinned
    announcement = await db.announcements.find_one({"id": announcement_id}, {"_id": 0})
    if not announcement:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")
    
    if announcement.get("is_pinned"):
        raise HTTPException(status_code=400, detail="لا يمكن إخفاء الإشعارات المثبتة")
    
    # Add to dismissed list
    await db.user_dismissed_announcements.update_one(
        {"user_id": user["user_id"], "announcement_id": announcement_id},
        {"$set": {
            "user_id": user["user_id"],
            "announcement_id": announcement_id,
            "dismissed_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "تم إخفاء الإشعار"}
