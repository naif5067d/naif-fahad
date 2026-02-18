"""
Notifications API - نظام الإشعارات الشامل
جميع الإشعارات في التطبيق: معاملات، خصومات، حضور، إنذارات، عقود
"""

from fastapi import APIRouter, HTTPException, Depends
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel

# استيراد خدمة الإشعارات
from services.notification_service import (
    get_user_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    get_unread_count
)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class LeaveCarryoverRequest(BaseModel):
    employee_id: str
    days_to_carryover: float
    note: Optional[str] = None


@router.get("/expiring-contracts")
async def get_expiring_contracts(
    days_ahead: int = 90,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    الحصول على العقود التي ستنتهي خلال فترة محددة (افتراضياً 90 يوم = 3 أشهر)
    
    Returns:
    - employees: قائمة الموظفين مع تفاصيل العقد ورصيد الإجازات
    - summary: إحصائيات
    """
    today = datetime.now(timezone.utc).date()
    cutoff_date = today + timedelta(days=days_ahead)
    today_str = today.strftime('%Y-%m-%d')
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    
    # البحث عن العقود النشطة التي لها تاريخ انتهاء (غير فارغ)
    query = {
        "status": "active",
        "end_date": {
            "$nin": [None, ""],
            "$lte": cutoff_str,
            "$gte": today_str
        }
    }
    
    expiring_contracts = await db.contracts_v2.find(
        query, {"_id": 0}
    ).sort("end_date", 1).to_list(100)
    
    # إضافة بيانات رصيد الإجازات لكل موظف
    result = []
    for contract in expiring_contracts:
        employee_id = contract.get('employee_id')
        
        # حساب رصيد الإجازات
        leave_entries = await db.leave_ledger.find(
            {"employee_id": employee_id, "leave_type": "annual"},
            {"_id": 0}
        ).to_list(1000)
        
        leave_balance = 0
        for entry in leave_entries:
            if entry.get('type') == 'credit':
                leave_balance += entry.get('days', 0)
            else:
                leave_balance -= entry.get('days', 0)
        
        # حساب الأيام المتبقية حتى انتهاء العقد
        end_date = datetime.strptime(contract['end_date'], '%Y-%m-%d').date()
        days_remaining = (end_date - today).days
        
        # تحديد مستوى الإلحاح
        if days_remaining <= 30:
            urgency = 'critical'
            urgency_ar = 'حرج'
        elif days_remaining <= 60:
            urgency = 'high'
            urgency_ar = 'مرتفع'
        else:
            urgency = 'medium'
            urgency_ar = 'متوسط'
        
        result.append({
            "contract": contract,
            "employee_id": employee_id,
            "employee_name": contract.get('employee_name'),
            "employee_name_ar": contract.get('employee_name_ar'),
            "employee_code": contract.get('employee_code'),
            "end_date": contract['end_date'],
            "days_remaining": days_remaining,
            "leave_balance": round(leave_balance, 2),
            "urgency": urgency,
            "urgency_ar": urgency_ar,
            "department": contract.get('department'),
            "department_ar": contract.get('department_ar'),
            "job_title": contract.get('job_title'),
            "job_title_ar": contract.get('job_title_ar')
        })
    
    # إحصائيات
    summary = {
        "total": len(result),
        "critical": len([r for r in result if r['urgency'] == 'critical']),
        "high": len([r for r in result if r['urgency'] == 'high']),
        "medium": len([r for r in result if r['urgency'] == 'medium']),
        "total_leave_balance": round(sum(r['leave_balance'] for r in result), 2)
    }
    
    return {
        "employees": result,
        "summary": summary
    }


@router.get("/header-alerts")
async def get_header_alerts(user=Depends(get_current_user)):
    """
    الحصول على التنبيهات للعرض في Header (أيقونة الجرس)
    يظهر فقط للأدوار: sultan, naif, stas
    """
    role = user.get('role')
    
    # فقط الأدوار المحددة ترى الإشعارات
    if role not in ['sultan', 'naif', 'stas']:
        return {"alerts": [], "count": 0}
    
    alerts = []
    today = datetime.now(timezone.utc).date()
    cutoff_date = today + timedelta(days=90)
    today_str = today.strftime('%Y-%m-%d')
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    
    # العقود المنتهية خلال 3 أشهر
    query = {
        "status": "active",
        "end_date": {
            "$nin": [None, ""],
            "$lte": cutoff_str,
            "$gte": today_str
        }
    }
    
    expiring_contracts = await db.contracts_v2.find(
        query, {"_id": 0}
    ).to_list(100)
    
    for contract in expiring_contracts:
        end_date = datetime.strptime(contract['end_date'], '%Y-%m-%d').date()
        days_remaining = (end_date - today).days
        
        if days_remaining <= 30:
            alert_type = 'critical'
        elif days_remaining <= 60:
            alert_type = 'warning'
        else:
            alert_type = 'info'
        
        alerts.append({
            "id": f"contract-expiry-{contract.get('id')}",
            "type": alert_type,
            "category": "contract_expiry",
            "employee_id": contract.get('employee_id'),
            "employee_name": contract.get('employee_name'),
            "employee_name_ar": contract.get('employee_name_ar'),
            "employee_code": contract.get('employee_code'),
            "message_en": f"Contract expires in {days_remaining} days",
            "message_ar": f"ينتهي العقد خلال {days_remaining} يوم",
            "days_remaining": days_remaining,
            "end_date": contract['end_date'],
            "contract_id": contract.get('id'),
            "contract_serial": contract.get('contract_serial')
        })
    
    # ترتيب حسب الأولوية (الأقرب أولاً)
    alerts.sort(key=lambda x: x['days_remaining'])
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "critical_count": len([a for a in alerts if a['type'] == 'critical']),
        "warning_count": len([a for a in alerts if a['type'] == 'warning'])
    }


@router.post("/leave-carryover")
async def carryover_leave(
    req: LeaveCarryoverRequest,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    ترحيل الإجازات للموظف
    متاح لـ: Sultan, Naif, STAS
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # التحقق من وجود الموظف
    employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من وجود عقد نشط
    contract = await db.contracts_v2.find_one({
        "employee_id": req.employee_id,
        "status": "active"
    }, {"_id": 0})
    
    if not contract:
        raise HTTPException(status_code=400, detail="لا يوجد عقد نشط للموظف")
    
    # حساب رصيد الإجازات الحالي
    leave_entries = await db.leave_ledger.find(
        {"employee_id": req.employee_id, "leave_type": "annual"},
        {"_id": 0}
    ).to_list(1000)
    
    current_balance = 0
    for entry in leave_entries:
        if entry.get('type') == 'credit':
            current_balance += entry.get('days', 0)
        else:
            current_balance -= entry.get('days', 0)
    
    # التحقق من أن الأيام المرحلة لا تتجاوز الرصيد
    if req.days_to_carryover > current_balance:
        raise HTTPException(
            status_code=400, 
            detail=f"لا يمكن ترحيل أكثر من الرصيد الحالي ({round(current_balance, 2)} يوم)"
        )
    
    if req.days_to_carryover <= 0:
        raise HTTPException(status_code=400, detail="يجب أن يكون عدد الأيام موجباً")
    
    # إنشاء قيد الترحيل
    import uuid
    carryover_entry = {
        "id": str(uuid.uuid4()),
        "employee_id": req.employee_id,
        "leave_type": "annual",
        "type": "carryover",
        "days": req.days_to_carryover,
        "note": req.note or f"ترحيل إجازات - Carried over by {user.get('full_name', user.get('role'))}",
        "created_by": user['user_id'],
        "created_by_name": user.get('full_name', user.get('role')),
        "created_at": now,
        "year_from": datetime.now().year - 1,
        "year_to": datetime.now().year
    }
    
    await db.leave_ledger.insert_one(carryover_entry)
    carryover_entry.pop('_id', None)
    
    # سجل في audit log
    audit_entry = {
        "id": str(uuid.uuid4()),
        "action": "leave_carryover",
        "employee_id": req.employee_id,
        "employee_name": employee.get('full_name'),
        "employee_name_ar": employee.get('full_name_ar'),
        "days": req.days_to_carryover,
        "actor_id": user['user_id'],
        "actor_name": user.get('full_name', user.get('role')),
        "note": req.note,
        "timestamp": now
    }
    await db.audit_log.insert_one(audit_entry)
    
    return {
        "message": f"تم ترحيل {req.days_to_carryover} يوم بنجاح",
        "entry": carryover_entry,
        "new_balance": round(current_balance, 2)  # الرصيد لا يتغير، فقط يُسجل
    }


@router.get("/leave-carryover-history/{employee_id}")
async def get_carryover_history(
    employee_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    سجل ترحيلات الإجازات للموظف
    """
    history = await db.leave_ledger.find(
        {"employee_id": employee_id, "type": "carryover"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return history



# ============================================================
# نظام الإشعارات الشامل
# ============================================================

@router.get("/my")
async def get_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    user=Depends(get_current_user)
):
    """
    جلب إشعارات المستخدم الحالي
    يعمل لجميع الأدوار
    """
    user_id = user['user_id']
    
    # جلب الإشعارات الموجهة للمستخدم مباشرة أو لدوره
    query = {
        "$or": [
            {"recipient_id": user_id},
            {"recipient_role": user.get('role')}
        ]
    }
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    # عدد غير المقروءة
    unread_count = await db.notifications.count_documents({
        "$or": [
            {"recipient_id": user_id},
            {"recipient_role": user.get('role')}
        ],
        "is_read": False
    })
    
    return {
        "notifications": notifications,
        "unread_count": unread_count,
        "total": len(notifications)
    }


@router.get("/unread-count")
async def get_my_unread_count(user=Depends(get_current_user)):
    """
    عدد الإشعارات غير المقروءة
    يُستخدم لتحديث أيقونة الجرس
    """
    user_id = user['user_id']
    
    count = await db.notifications.count_documents({
        "$or": [
            {"recipient_id": user_id},
            {"recipient_role": user.get('role')}
        ],
        "is_read": False
    })
    
    # جلب أحدث 3 إشعارات للـ preview
    recent = await db.notifications.find(
        {
            "$or": [
                {"recipient_id": user_id},
                {"recipient_role": user.get('role')}
            ],
            "is_read": False
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(3)
    
    return {
        "count": count,
        "has_critical": any(n.get('priority') == 'critical' for n in recent),
        "recent_preview": recent
    }


@router.patch("/{notification_id}/read")
async def mark_as_read(notification_id: str, user=Depends(get_current_user)):
    """
    تحديد إشعار كمقروء
    """
    user_id = user['user_id']
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.notifications.update_one(
        {
            "id": notification_id,
            "$or": [
                {"recipient_id": user_id},
                {"recipient_role": user.get('role')}
            ]
        },
        {"$set": {"is_read": True, "read_at": now}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")
    
    return {"message": "تم تحديد الإشعار كمقروء"}


@router.post("/mark-all-read")
async def mark_all_as_read(user=Depends(get_current_user)):
    """
    تحديد جميع الإشعارات كمقروءة
    """
    user_id = user['user_id']
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.notifications.update_many(
        {
            "$or": [
                {"recipient_id": user_id},
                {"recipient_role": user.get('role')}
            ],
            "is_read": False
        },
        {"$set": {"is_read": True, "read_at": now}}
    )
    
    return {
        "message": "تم تحديد جميع الإشعارات كمقروءة",
        "count": result.modified_count
    }


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user=Depends(get_current_user)):
    """
    حذف إشعار
    """
    user_id = user['user_id']
    
    result = await db.notifications.delete_one({
        "id": notification_id,
        "$or": [
            {"recipient_id": user_id},
            {"recipient_role": user.get('role')}
        ]
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="الإشعار غير موجود")
    
    return {"message": "تم حذف الإشعار"}


# ============================================================
# الجرس الشامل - Header Bell
# ============================================================

@router.get("/bell")
async def get_bell_notifications(user=Depends(get_current_user)):
    """
    جلب بيانات الجرس الشامل
    يجمع جميع أنواع الإشعارات للمستخدم
    """
    user_id = user['user_id']
    role = user.get('role')
    is_admin = role in ['sultan', 'naif', 'stas', 'mohammed', 'salah']
    
    result = {
        "notifications": [],
        "unread_count": 0,
        "has_critical": False,
        "categories": {}
    }
    
    # 1. الإشعارات المخزنة (تدعم البنية القديمة والجديدة)
    stored_notifications = await db.notifications.find(
        {
            "$or": [
                {"recipient_id": user_id},
                {"recipient_role": role}
            ]
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(30)
    
    # تحويل الإشعارات القديمة للبنية الجديدة
    for notif in stored_notifications:
        # التحقق من حالة القراءة (البنية القديمة تستخدم 'read' والجديدة 'is_read')
        is_read = notif.get('is_read', notif.get('read', False))
        
        formatted = {
            "id": notif.get('id'),
            "notification_type": notif.get('notification_type', notif.get('type', 'system')),
            "title": notif.get('title', notif.get('message_en', 'Notification')),
            "title_ar": notif.get('title_ar', notif.get('message_ar', 'إشعار')),
            "message": notif.get('message', notif.get('message_en', '')),
            "message_ar": notif.get('message_ar', ''),
            "priority": notif.get('priority', 'normal'),
            "icon": notif.get('icon', 'Bell'),
            "color": notif.get('color', '#6B7280'),
            "reference_type": notif.get('reference_type', ''),
            "reference_id": notif.get('reference_id', notif.get('transaction_id', '')),
            "reference_url": notif.get('reference_url', ''),
            "is_read": is_read,
            "created_at": notif.get('created_at', '')
        }
        result["notifications"].append(formatted)
        
        if not is_read:
            result["unread_count"] += 1
    
    # 2. للإدارة: المعاملات المعلقة
    if is_admin:
        stage_map = {
            'sultan': ['pending_ops', 'pending_ceo'],
            'naif': ['pending_ops'],
            'stas': ['pending_stas'],
            'mohammed': ['pending_ceo'],
            'salah': ['pending_finance']
        }
        
        pending_statuses = stage_map.get(role, [])
        if pending_statuses:
            pending_txs = await db.transactions.find(
                {"status": {"$in": pending_statuses}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(10)
            
            for tx in pending_txs:
                # تحقق من عدم وجود إشعار مكرر
                if not any(n.get('reference_id') == tx.get('id') and n.get('notification_type') == 'transaction_pending' for n in result["notifications"]):
                    result["notifications"].append({
                        "id": f"pending-tx-{tx.get('id')}",
                        "notification_type": "transaction_pending",
                        "title": "Pending approval",
                        "title_ar": "بانتظار موافقتك",
                        "message": f"Ref: {tx.get('ref_no')}",
                        "message_ar": f"المرجع: {tx.get('ref_no')}",
                        "priority": "high",
                        "icon": "FileText",
                        "color": "#F97316",
                        "reference_type": "transaction",
                        "reference_id": tx.get('id'),
                        "reference_url": f"/transactions/{tx.get('id')}",
                        "is_read": False,
                        "is_live": True,
                        "created_at": tx.get('created_at')
                    })
                    result["unread_count"] += 1
    
    # 3. للإدارة: تنبيهات العقود (أقل من 30 يوم)
    if is_admin and role in ['sultan', 'naif', 'stas']:
        today = datetime.now(timezone.utc).date()
        cutoff_date = today + timedelta(days=30)
        today_str = today.strftime('%Y-%m-%d')
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        expiring = await db.contracts_v2.find({
            "status": "active",
            "end_date": {"$ne": None, "$ne": "", "$lte": cutoff_str, "$gte": today_str}
        }, {"_id": 0}).to_list(5)
        
        for contract in expiring:
            end_date = datetime.strptime(contract['end_date'], '%Y-%m-%d').date()
            days_remaining = (end_date - today).days
            
            if not any(n.get('reference_id') == contract.get('id') and 'contract' in n.get('notification_type', '') for n in result["notifications"]):
                result["notifications"].append({
                    "id": f"contract-exp-{contract.get('id')}",
                    "notification_type": "contract_expiring",
                    "title": f"Contract expires in {days_remaining} days",
                    "title_ar": f"عقد ينتهي خلال {days_remaining} يوم",
                    "message": contract.get('employee_name_ar', contract.get('employee_name', '')),
                    "message_ar": contract.get('employee_name_ar', contract.get('employee_name', '')),
                    "priority": "critical" if days_remaining <= 7 else "high",
                    "icon": "FileWarning",
                    "color": "#EF4444" if days_remaining <= 7 else "#F59E0B",
                    "reference_type": "contract",
                    "reference_id": contract.get('id'),
                    "reference_url": "/contracts-management",
                    "is_read": False,
                    "is_live": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"days_remaining": days_remaining}
                })
                if days_remaining <= 7:
                    result["has_critical"] = True
                result["unread_count"] += 1
    
    # ترتيب حسب التاريخ
    result["notifications"].sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # تصنيف الإشعارات
    for notif in result["notifications"]:
        cat = notif.get('notification_type', 'other').split('_')[0]
        result["categories"][cat] = result["categories"].get(cat, 0) + 1
    
    # فحص الحرجة
    if any(n.get('priority') == 'critical' for n in result["notifications"][:10]):
        result["has_critical"] = True
    
    return result
