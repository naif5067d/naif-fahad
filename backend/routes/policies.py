"""
Policies Module - نظام السياسات والحوكمة
Professional Governance Booklet Engine

Features:
- Public System (النظام العام)
- Private System (النظام الخاص) - أكثر رسمية
- Chapter management with draft/publish workflow
- Legal footer management (STAS only)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/policies", tags=["Policies"])


# ============================================================
# MODELS
# ============================================================

class ChapterCreate(BaseModel):
    system_id: str  # "public" or "private"
    title: str
    title_ar: str
    content: str = ""
    order_index: Optional[int] = None


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    title_ar: Optional[str] = None
    content: Optional[str] = None
    order_index: Optional[int] = None


class ReorderChapters(BaseModel):
    chapter_ids: List[str]  # Ordered list of chapter IDs


class LegalFooterUpdate(BaseModel):
    text_ar: str
    text_en: str


# ============================================================
# LEGAL FOOTER (STAS ONLY)
# ============================================================

DEFAULT_LEGAL_FOOTER_AR = """هذا النظام معتمد مسبقًا من الإدارة العليا للشركة، ويُعد المرجع التنظيمي الداخلي المعمول به.
يتم نشره عبر هذا النظام لأغراض الحوكمة والتوثيق فقط.
تحتفظ الشركة بكامل حقوقها النظامية والتنظيمية في تفسيره وتعديله وتطبيقه وفق ما تراه مناسبًا دون إخلال بالأنظمة المعمول بها في المملكة العربية السعودية."""

DEFAULT_LEGAL_FOOTER_EN = """This governance system has been previously approved by the Company's senior management and constitutes the official internal regulatory framework.
Its publication within this system is for governance and documentation purposes only.
The Company reserves all legal and regulatory rights to interpret, amend, and enforce it in accordance with the applicable laws of the Kingdom of Saudi Arabia."""


@router.get("/legal-footer")
async def get_legal_footer(user=Depends(get_current_user)):
    """Get the legal footer text"""
    footer = await db.settings.find_one({"type": "policy_legal_footer"}, {"_id": 0})
    if not footer:
        return {
            "type": "policy_legal_footer",
            "text_ar": DEFAULT_LEGAL_FOOTER_AR,
            "text_en": DEFAULT_LEGAL_FOOTER_EN,
            "updated_at": None,
            "updated_by": None
        }
    return footer


@router.put("/legal-footer")
async def update_legal_footer(req: LegalFooterUpdate, user=Depends(get_current_user)):
    """Update legal footer - STAS ONLY"""
    if user.get('role') != 'stas' and user.get('username') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه تعديل التذييل القانوني")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_data = {
        "type": "policy_legal_footer",
        "text_ar": req.text_ar,
        "text_en": req.text_en,
        "updated_at": now,
        "updated_by": user.get('user_id'),
        "updated_by_name": user.get('full_name', 'STAS')
    }
    
    await db.settings.update_one(
        {"type": "policy_legal_footer"},
        {"$set": update_data},
        upsert=True
    )
    
    return await db.settings.find_one({"type": "policy_legal_footer"}, {"_id": 0})


# ============================================================
# POLICY SYSTEMS
# ============================================================

@router.get("/systems")
async def get_policy_systems(user=Depends(get_current_user)):
    """Get all policy systems with chapter counts"""
    systems = [
        {
            "id": "public",
            "name": "Public System",
            "name_ar": "النظام العام",
            "description_ar": "السياسات والإجراءات العامة",
            "description_en": "General policies and procedures"
        },
        {
            "id": "private",
            "name": "Private System",
            "name_ar": "النظام الخاص",
            "description_ar": "الإطار التنظيمي الداخلي الرسمي",
            "description_en": "Official internal regulatory framework"
        }
    ]
    
    # Add chapter counts
    for system in systems:
        # For employees, only count published chapters
        role = user.get('role')
        is_admin = role in ['stas', 'sultan', 'naif'] or user.get('username') in ['stas', 'sultan', 'naif']
        
        if is_admin:
            count = await db.policy_chapters.count_documents({"system_id": system["id"]})
            published_count = await db.policy_chapters.count_documents({
                "system_id": system["id"],
                "status": "published"
            })
        else:
            count = await db.policy_chapters.count_documents({
                "system_id": system["id"],
                "status": "published"
            })
            published_count = count
        
        system["total_chapters"] = count
        system["published_chapters"] = published_count
    
    return systems


# ============================================================
# CHAPTERS
# ============================================================

@router.get("/chapters/{system_id}")
async def get_chapters(system_id: str, user=Depends(get_current_user)):
    """Get all chapters for a system"""
    if system_id not in ["public", "private"]:
        raise HTTPException(status_code=400, detail="نظام غير صالح")
    
    role = user.get('role')
    is_admin = role in ['stas', 'sultan', 'naif'] or user.get('username') in ['stas', 'sultan', 'naif']
    
    query = {"system_id": system_id}
    
    # Employees can only see published chapters
    if not is_admin:
        query["status"] = "published"
    
    chapters = await db.policy_chapters.find(
        query,
        {"_id": 0}
    ).sort("order_index", 1).to_list(500)
    
    return chapters


@router.get("/chapter/{chapter_id}")
async def get_chapter(chapter_id: str, user=Depends(get_current_user)):
    """Get a single chapter"""
    chapter = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    role = user.get('role')
    is_admin = role in ['stas', 'sultan', 'naif'] or user.get('username') in ['stas', 'sultan', 'naif']
    
    # Employees can only see published chapters
    if not is_admin and chapter.get('status') != 'published':
        raise HTTPException(status_code=403, detail="هذا الفصل غير منشور")
    
    return chapter


@router.post("/chapters")
async def create_chapter(req: ChapterCreate, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """Create a new chapter - Draft status by default"""
    if req.system_id not in ["public", "private"]:
        raise HTTPException(status_code=400, detail="نظام غير صالح")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get next order index
    if req.order_index is None:
        max_order = await db.policy_chapters.find_one(
            {"system_id": req.system_id},
            sort=[("order_index", -1)]
        )
        req.order_index = (max_order.get("order_index", 0) + 1) if max_order else 1
    
    chapter = {
        "id": str(uuid.uuid4()),
        "system_id": req.system_id,
        "title": req.title,
        "title_ar": req.title_ar,
        "content": req.content,
        "order_index": req.order_index,
        "status": "draft",
        "version": 1,
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "updated_by": user.get('user_id'),
        "updated_by_name": user.get('full_name', ''),
        "updated_at": now,
        "published_by": None,
        "published_by_name": None,
        "published_at": None
    }
    
    await db.policy_chapters.insert_one(chapter)
    chapter.pop('_id', None)
    
    return chapter


@router.put("/chapter/{chapter_id}")
async def update_chapter(
    chapter_id: str,
    req: ChapterUpdate,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """
    Update a chapter
    - Only draft chapters can be edited directly
    - Published chapters require creating a new draft version
    """
    chapter = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # If published, create a new draft version
    if chapter.get('status') == 'published':
        # Archive the published version
        await db.policy_chapters.update_one(
            {"id": chapter_id},
            {"$set": {
                "status": "archived",
                "archived_at": now
            }}
        )
        
        # Create new draft version
        new_chapter = {
            "id": str(uuid.uuid4()),
            "system_id": chapter['system_id'],
            "title": req.title if req.title else chapter['title'],
            "title_ar": req.title_ar if req.title_ar else chapter['title_ar'],
            "content": req.content if req.content else chapter['content'],
            "order_index": req.order_index if req.order_index else chapter['order_index'],
            "status": "draft",
            "version": chapter.get('version', 1) + 1,
            "previous_version_id": chapter_id,
            "created_by": chapter['created_by'],
            "created_by_name": chapter.get('created_by_name', ''),
            "created_at": chapter['created_at'],
            "updated_by": user.get('user_id'),
            "updated_by_name": user.get('full_name', ''),
            "updated_at": now,
            "published_by": None,
            "published_by_name": None,
            "published_at": None
        }
        
        await db.policy_chapters.insert_one(new_chapter)
        new_chapter.pop('_id', None)
        
        return {
            "message": "تم إنشاء نسخة مسودة جديدة",
            "chapter": new_chapter,
            "action": "new_draft_created"
        }
    
    # Update draft directly
    update_data = {
        "updated_by": user.get('user_id'),
        "updated_by_name": user.get('full_name', ''),
        "updated_at": now
    }
    
    if req.title is not None:
        update_data["title"] = req.title
    if req.title_ar is not None:
        update_data["title_ar"] = req.title_ar
    if req.content is not None:
        update_data["content"] = req.content
    if req.order_index is not None:
        update_data["order_index"] = req.order_index
    
    await db.policy_chapters.update_one(
        {"id": chapter_id},
        {"$set": update_data}
    )
    
    updated = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    return updated


@router.post("/chapter/{chapter_id}/publish")
async def publish_chapter(
    chapter_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """Publish a draft chapter"""
    chapter = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    if chapter.get('status') == 'published':
        raise HTTPException(status_code=400, detail="الفصل منشور بالفعل")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.policy_chapters.update_one(
        {"id": chapter_id},
        {"$set": {
            "status": "published",
            "published_by": user.get('user_id'),
            "published_by_name": user.get('full_name', ''),
            "published_at": now,
            "updated_at": now
        }}
    )
    
    updated = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    return {
        "message": "تم نشر الفصل بنجاح",
        "chapter": updated
    }


@router.post("/chapter/{chapter_id}/unpublish")
async def unpublish_chapter(
    chapter_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """Revert published chapter to draft"""
    chapter = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    if chapter.get('status') != 'published':
        raise HTTPException(status_code=400, detail="الفصل ليس منشوراً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.policy_chapters.update_one(
        {"id": chapter_id},
        {"$set": {
            "status": "draft",
            "updated_by": user.get('user_id'),
            "updated_by_name": user.get('full_name', ''),
            "updated_at": now
        }}
    )
    
    updated = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    return {
        "message": "تم إلغاء نشر الفصل",
        "chapter": updated
    }


@router.post("/chapters/reorder")
async def reorder_chapters(
    req: ReorderChapters,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """Reorder chapters by providing ordered list of IDs"""
    now = datetime.now(timezone.utc).isoformat()
    
    for index, chapter_id in enumerate(req.chapter_ids):
        await db.policy_chapters.update_one(
            {"id": chapter_id},
            {"$set": {
                "order_index": index + 1,
                "updated_at": now
            }}
        )
    
    return {"message": "تم إعادة ترتيب الفصول", "count": len(req.chapter_ids)}


@router.delete("/chapter/{chapter_id}")
async def delete_chapter(
    chapter_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """Delete a chapter (draft only, or STAS can delete any)"""
    chapter = await db.policy_chapters.find_one({"id": chapter_id}, {"_id": 0})
    
    if not chapter:
        raise HTTPException(status_code=404, detail="الفصل غير موجود")
    
    # Only STAS can delete published chapters
    is_stas = user.get('role') == 'stas' or user.get('username') == 'stas'
    
    if chapter.get('status') == 'published' and not is_stas:
        raise HTTPException(
            status_code=403,
            detail="لا يمكن حذف فصل منشور. قم بإلغاء النشر أولاً أو تواصل مع STAS"
        )
    
    await db.policy_chapters.delete_one({"id": chapter_id})
    
    return {"message": "تم حذف الفصل", "chapter_id": chapter_id}


# ============================================================
# STATISTICS
# ============================================================

@router.get("/stats")
async def get_policy_stats(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """Get policy statistics"""
    public_total = await db.policy_chapters.count_documents({"system_id": "public"})
    public_published = await db.policy_chapters.count_documents({
        "system_id": "public",
        "status": "published"
    })
    
    private_total = await db.policy_chapters.count_documents({"system_id": "private"})
    private_published = await db.policy_chapters.count_documents({
        "system_id": "private",
        "status": "published"
    })
    
    return {
        "public": {
            "total": public_total,
            "published": public_published,
            "draft": public_total - public_published
        },
        "private": {
            "total": private_total,
            "published": private_published,
            "draft": private_total - private_published
        },
        "total": {
            "chapters": public_total + private_total,
            "published": public_published + private_published,
            "draft": (public_total + private_total) - (public_published + private_published)
        }
    }
