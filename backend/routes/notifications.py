"""
Notifications API - Contract Expiration & Leave Carryover Alerts
إشعارات انتهاء العقود وترحيل الإجازات
"""

from fastapi import APIRouter, HTTPException, Depends
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel

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
    
    # البحث عن العقود النشطة التي لها تاريخ انتهاء
    pipeline = [
        {
            "$match": {
                "status": "active",
                "end_date": {"$ne": None}
            }
        },
        {
            "$addFields": {
                "end_date_parsed": {"$dateFromString": {"dateString": "$end_date"}}
            }
        },
        {
            "$match": {
                "end_date_parsed": {
                    "$lte": datetime.combine(cutoff_date, datetime.min.time()),
                    "$gte": datetime.combine(today, datetime.min.time())
                }
            }
        },
        {
            "$sort": {"end_date_parsed": 1}
        },
        {
            "$project": {"_id": 0}
        }
    ]
    
    expiring_contracts = await db.contracts_v2.aggregate(pipeline).to_list(100)
    
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
    
    # العقود المنتهية خلال 3 أشهر
    pipeline = [
        {
            "$match": {
                "status": "active",
                "end_date": {"$ne": None}
            }
        },
        {
            "$addFields": {
                "end_date_parsed": {"$dateFromString": {"dateString": "$end_date"}}
            }
        },
        {
            "$match": {
                "end_date_parsed": {
                    "$lte": datetime.combine(cutoff_date, datetime.min.time()),
                    "$gte": datetime.combine(today, datetime.min.time())
                }
            }
        },
        {"$project": {"_id": 0}}
    ]
    
    expiring_contracts = await db.contracts_v2.aggregate(pipeline).to_list(100)
    
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
