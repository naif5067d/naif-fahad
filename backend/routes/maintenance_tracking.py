"""
Maintenance Tracking - متابعة الصيانة الداخلية
بطاقات مرنة لمتابعة أي شيء بالصيانة
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import require_roles
import uuid

router = APIRouter(prefix="/api/maintenance-tracking", tags=["Maintenance Tracking"])

# ==================== MODELS ====================

class MaintenanceCardCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)  # إجباري
    asset_type: Optional[str] = None  # جهاز / سيارة / معدة / أخرى
    department: Optional[str] = None
    description: Optional[str] = None
    sent_date: Optional[str] = None  # تاريخ الإرسال
    expected_date: Optional[str] = None  # تاريخ متوقع للانتهاء
    invoice_number: Optional[str] = None
    cost: Optional[float] = None
    notes: Optional[str] = None

class MaintenanceCardUpdate(BaseModel):
    title: Optional[str] = None
    asset_type: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    sent_date: Optional[str] = None
    expected_date: Optional[str] = None
    invoice_number: Optional[str] = None
    cost: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # new, in_progress, ready, closed

# ==================== HELPER ====================

def check_delay(expected_date: str) -> dict:
    """التحقق من التأخير"""
    if not expected_date:
        return {"has_expected": False, "is_delayed": False, "days_remaining": None, "alert": None}
    
    try:
        expected = datetime.fromisoformat(expected_date.replace('Z', '+00:00'))
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = expected - now
        days = diff.days
        
        if days < 0:
            return {
                "has_expected": True,
                "is_delayed": True,
                "days_remaining": days,
                "alert": "متأخر",
                "alert_en": "Delayed"
            }
        elif days == 0:
            return {
                "has_expected": True,
                "is_delayed": False,
                "days_remaining": 0,
                "alert": "اليوم",
                "alert_en": "Today"
            }
        elif days == 1:
            return {
                "has_expected": True,
                "is_delayed": False,
                "days_remaining": 1,
                "alert": "غداً",
                "alert_en": "Tomorrow"
            }
        else:
            return {
                "has_expected": True,
                "is_delayed": False,
                "days_remaining": days,
                "alert": None
            }
    except Exception:
        return {"has_expected": False, "is_delayed": False, "days_remaining": None, "alert": None}

# ==================== ENDPOINTS ====================

@router.post("/create")
async def create_card(
    card: MaintenanceCardCreate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """إنشاء بطاقة صيانة جديدة"""
    now = datetime.now(timezone.utc).isoformat()
    
    new_card = {
        "id": str(uuid.uuid4()),
        "title": card.title,
        "asset_type": card.asset_type,
        "department": card.department,
        "description": card.description,
        "sent_date": card.sent_date,
        "expected_date": card.expected_date,
        "invoice_number": card.invoice_number,
        "cost": card.cost,
        "notes": card.notes,
        "status": "new",
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "updated_at": now
    }
    
    await db.maintenance_cards.insert_one(new_card)
    new_card.pop('_id', None)
    
    # إضافة معلومات التأخير
    new_card['delay_info'] = check_delay(card.expected_date)
    
    return {
        "success": True,
        "message_ar": "تم إنشاء البطاقة بنجاح",
        "message_en": "Card created successfully",
        "card": new_card
    }


@router.get("/all")
async def get_all_cards(
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """جلب جميع البطاقات"""
    query = {}
    if status:
        query["status"] = status
    
    cards = await db.maintenance_cards.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # إضافة معلومات التأخير لكل بطاقة
    for card in cards:
        card['delay_info'] = check_delay(card.get('expected_date'))
    
    return cards


@router.get("/alerts")
async def get_alerts(
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """جلب البطاقات التي تحتاج انتباه (متأخرة أو قريبة)"""
    # البطاقات غير المغلقة
    cards = await db.maintenance_cards.find(
        {"status": {"$ne": "closed"}},
        {"_id": 0}
    ).to_list(500)
    
    alerts = []
    for card in cards:
        delay_info = check_delay(card.get('expected_date'))
        if delay_info.get('alert'):
            card['delay_info'] = delay_info
            alerts.append(card)
    
    # ترتيب: المتأخرة أولاً
    alerts.sort(key=lambda x: x['delay_info'].get('days_remaining', 999))
    
    return alerts


@router.get("/{card_id}")
async def get_card(
    card_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """جلب بطاقة معينة"""
    card = await db.maintenance_cards.find_one({"id": card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="البطاقة غير موجودة")
    
    card['delay_info'] = check_delay(card.get('expected_date'))
    return card


@router.put("/{card_id}")
async def update_card(
    card_id: str,
    data: MaintenanceCardUpdate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """تحديث بطاقة"""
    card = await db.maintenance_cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="البطاقة غير موجودة")
    
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = user.get('user_id')
    
    await db.maintenance_cards.update_one(
        {"id": card_id},
        {"$set": update_data}
    )
    
    updated = await db.maintenance_cards.find_one({"id": card_id}, {"_id": 0})
    updated['delay_info'] = check_delay(updated.get('expected_date'))
    
    return {
        "success": True,
        "message_ar": "تم تحديث البطاقة",
        "message_en": "Card updated",
        "card": updated
    }


@router.patch("/{card_id}/status")
async def update_status(
    card_id: str,
    status: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """تغيير حالة البطاقة"""
    valid_statuses = ['new', 'in_progress', 'ready', 'closed']
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"الحالة غير صالحة. الحالات المتاحة: {valid_statuses}")
    
    card = await db.maintenance_cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="البطاقة غير موجودة")
    
    await db.maintenance_cards.update_one(
        {"id": card_id},
        {"$set": {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user.get('user_id')
        }}
    )
    
    status_labels = {
        'new': {'ar': 'جديد', 'en': 'New'},
        'in_progress': {'ar': 'تحت الصيانة', 'en': 'In Progress'},
        'ready': {'ar': 'جاهز للاستلام', 'en': 'Ready'},
        'closed': {'ar': 'مغلق', 'en': 'Closed'}
    }
    
    return {
        "success": True,
        "message_ar": f"تم تغيير الحالة إلى: {status_labels[status]['ar']}",
        "message_en": f"Status changed to: {status_labels[status]['en']}",
        "new_status": status
    }


@router.delete("/{card_id}")
async def delete_card(
    card_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """حذف بطاقة"""
    card = await db.maintenance_cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="البطاقة غير موجودة")
    
    await db.maintenance_cards.delete_one({"id": card_id})
    
    return {
        "success": True,
        "message_ar": "تم حذف البطاقة",
        "message_en": "Card deleted"
    }


@router.get("/stats/summary")
async def get_stats(
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """إحصائيات سريعة"""
    all_cards = await db.maintenance_cards.find({}, {"_id": 0}).to_list(1000)
    
    stats = {
        "total": len(all_cards),
        "new": len([c for c in all_cards if c.get('status') == 'new']),
        "in_progress": len([c for c in all_cards if c.get('status') == 'in_progress']),
        "ready": len([c for c in all_cards if c.get('status') == 'ready']),
        "closed": len([c for c in all_cards if c.get('status') == 'closed']),
        "delayed": 0,
        "total_cost": 0
    }
    
    for card in all_cards:
        if card.get('cost'):
            stats['total_cost'] += card['cost']
        delay_info = check_delay(card.get('expected_date'))
        if delay_info.get('is_delayed') and card.get('status') != 'closed':
            stats['delayed'] += 1
    
    return stats
