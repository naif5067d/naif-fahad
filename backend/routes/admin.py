"""
Admin Routes - إدارة النظام
============================================================
- تغيير سياسة الإجازة السنوية (21/30)
- ترحيل الإجازات (بقرار إداري)
- تنبيهات الأرصدة
- إعادة تعيين البيانات
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import require_roles
from datetime import datetime, timezone
from services.hr_policy import (
    set_annual_policy_override,
    generate_balance_alerts,
    check_carryover_eligibility
)
import uuid

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============================================================
# MODELS
# ============================================================

class AnnualPolicyChange(BaseModel):
    employee_id: str
    days: int  # 21 أو 30 فقط
    reason: Optional[str] = None


class LeaveCarryover(BaseModel):
    employee_id: str
    days: float
    from_year: int
    to_year: int
    reason: str


class ResetBalancesRequest(BaseModel):
    confirm: bool = False


# ============================================================
# سياسة الإجازة السنوية (21/30)
# ============================================================

@router.post("/annual-policy")
async def change_annual_policy(
    req: AnnualPolicyChange,
    user=Depends(require_roles('stas'))
):
    """
    تغيير سياسة الإجازة السنوية للموظف
    يتطلب: STAS
    القيم المسموحة: 21 أو 30 يوم فقط
    """
    if req.days not in [21, 30]:
        raise HTTPException(status_code=400, detail="القيمة يجب أن تكون 21 أو 30 يوم فقط")
    
    # التحقق من وجود الموظف
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    result = await set_annual_policy_override(
        employee_id=req.employee_id,
        days=req.days,
        approved_by=user['user_id'],
        reason=req.reason
    )
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result.get('message_ar'))
    
    return result


@router.get("/annual-policy/{employee_id}")
async def get_annual_policy(employee_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """
    الحصول على سياسة الإجازة السنوية للموظف
    """
    from services.hr_policy import get_employee_annual_policy
    
    policy = await get_employee_annual_policy(employee_id)
    return policy


# ============================================================
# ترحيل الإجازات (بقرار إداري)
# ============================================================

@router.post("/leave-carryover")
async def create_leave_carryover(
    req: LeaveCarryover,
    user=Depends(require_roles('stas'))
):
    """
    إنشاء قرار ترحيل إجازات
    يتطلب: STAS
    
    ملاحظة: لا ترحيل تلقائي - هذا استثناء بقرار إداري
    """
    # التحقق من وجود الموظف
    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    carryover = {
        "id": str(uuid.uuid4()),
        "employee_id": req.employee_id,
        "override_type": "leave_carryover",
        "value": req.days,
        "from_year": req.from_year,
        "to_year": req.to_year,
        "reason": req.reason,
        "approved_by": user['user_id'],
        "is_active": True,
        "created_at": now
    }
    
    await db.admin_overrides.insert_one(carryover)
    carryover.pop("_id", None)
    
    # إضافة الرصيد المُرحّل إلى leave_ledger
    await db.leave_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": req.employee_id,
        "leave_type": "annual",
        "type": "credit",
        "days": req.days,
        "reason": f"ترحيل من {req.from_year} إلى {req.to_year}",
        "source": "carryover",
        "carryover_id": carryover['id'],
        "date": f"{req.to_year}-01-01",
        "created_at": now,
        "created_by": user['user_id']
    })
    
    return {
        "message_ar": f"تم ترحيل {req.days} يوم من {req.from_year} إلى {req.to_year}",
        "carryover": carryover
    }


# ============================================================
# تنبيهات الأرصدة
# ============================================================

@router.get("/balance-alerts")
async def get_balance_alerts(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """
    الحصول على تنبيهات الأرصدة
    - موظفون مع عقود تنتهي قريباً ولديهم رصيد
    - نهاية السنة مع أرصدة متبقية
    """
    alerts = await generate_balance_alerts()
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# إعادة تعيين البيانات
# ============================================================

@router.post("/reset-balances")
async def reset_all_balances(
    req: ResetBalancesRequest,
    user=Depends(require_roles('stas'))
):
    """
    إعادة تعيين جميع الأرصدة والمعاملات
    خطير! يتطلب تأكيد
    """
    if not req.confirm:
        raise HTTPException(status_code=400, detail="يجب تأكيد العملية")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # حذف leave_ledger
    leave_result = await db.leave_ledger.delete_many({})
    
    # حذف المعاملات
    tx_result = await db.transactions.delete_many({})
    
    # إعادة تعيين العدادات
    await db.counters.update_one(
        {"name": "transaction"},
        {"$set": {"seq": 0}},
        upsert=True
    )
    
    return {
        "message_ar": "تم إعادة تعيين جميع الأرصدة والمعاملات",
        "deleted": {
            "leave_ledger": leave_result.deleted_count,
            "transactions": tx_result.deleted_count
        },
        "timestamp": now
    }


@router.post("/reset-test-data")
async def reset_test_data(user=Depends(require_roles('stas'))):
    """
    حذف بيانات الاختبار فقط (TEST-)
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # حذف موظفين الاختبار
    emp_result = await db.employees.delete_many({"employee_number": {"$regex": "^TEST-"}})
    
    # حذف المستخدمين المرتبطين
    user_result = await db.users.delete_many({"employee_id": {"$regex": "^TEST-"}})
    
    # حذف العقود
    contract_result = await db.contracts_v2.delete_many({"employee_code": {"$regex": "^TEST-"}})
    
    return {
        "message_ar": "تم حذف بيانات الاختبار",
        "deleted": {
            "employees": emp_result.deleted_count,
            "users": user_result.deleted_count,
            "contracts": contract_result.deleted_count
        },
        "timestamp": now
    }


# ============================================================
# إعادة تعيين كلمة مرور STAS (للطوارئ)
# ============================================================

class ResetStasPasswordRequest(BaseModel):
    emergency_key: str

@router.post("/emergency-reset-stas-password")
async def emergency_reset_stas_password(body: ResetStasPasswordRequest):
    """
    إعادة تعيين كلمة مرور STAS للطوارئ
    كلمة المرور الجديدة: 123456
    """
    from utils.auth import hash_password
    
    # مفتاح الطوارئ
    if body.emergency_key != "EMERGENCY_STAS_2026":
        raise HTTPException(status_code=403, detail="مفتاح غير صحيح")
    
    # البحث عن مستخدم stas
    stas_user = await db.users.find_one({"username": "stas"})
    
    if not stas_user:
        raise HTTPException(status_code=404, detail="مستخدم stas غير موجود")
    
    # تشفير كلمة المرور الجديدة
    new_hash = hash_password("123456")
    
    # تحديث كلمة المرور
    await db.users.update_one(
        {"username": "stas"},
        {"$set": {"password_hash": new_hash}}
    )
    
    return {
        "message_ar": "تم إعادة تعيين كلمة مرور STAS بنجاح",
        "message_en": "STAS password has been reset successfully",
        "username": "stas",
        "new_password": "123456",
        "warning": "يرجى تغيير كلمة المرور بعد تسجيل الدخول"
    }


# ============================================================
# إعادة تهيئة قاعدة البيانات بالكامل (للنشر الأولي)
# ============================================================

class FullResetRequest(BaseModel):
    secret_key: str
    confirm: bool = False

@router.post("/full-reset-for-production")
async def full_reset_for_production(body: FullResetRequest):
    """
    إعادة تهيئة قاعدة البيانات بالكامل للنشر الأولي
    تحذير: هذا سيحذف جميع البيانات!
    
    يتطلب مفتاح سري من environment variable
    """
    import os
    
    # المفتاح السري من environment variable (أكثر أماناً)
    expected_key = os.environ.get('RESET_SECRET_KEY', '')
    
    # إذا لم يكن المفتاح موجوداً في البيئة، الـ endpoint معطل
    if not expected_key:
        raise HTTPException(
            status_code=403, 
            detail="هذا الـ endpoint معطل. يجب تعيين RESET_SECRET_KEY في environment variables"
        )
    
    # التحقق من المفتاح السري
    if body.secret_key != expected_key:
        raise HTTPException(status_code=403, detail="مفتاح سري غير صحيح")
    
    if not body.confirm:
        raise HTTPException(status_code=400, detail="يجب تأكيد العملية")
    
    from seed import seed_database
    
    now = datetime.now(timezone.utc).isoformat()
    
    # حذف جميع البيانات
    collections_to_clear = [
        'users', 'employees', 'contracts', 'contracts_v2',
        'transactions', 'leave_ledger', 'attendance',
        'settings', 'counters', 'public_holidays', 'finance_codes',
        'custody_items', 'financial_custody', 'announcements',
        'devices', 'login_sessions', 'deduction_log', 'tasks'
    ]
    
    deleted_counts = {}
    for coll_name in collections_to_clear:
        try:
            result = await db[coll_name].delete_many({})
            deleted_counts[coll_name] = result.deleted_count
        except Exception as e:
            deleted_counts[coll_name] = f"error: {str(e)}"
    
    # إعادة تهيئة البيانات الأساسية
    result = await seed_database(db)
    
    return {
        "message_ar": "تم إعادة تهيئة قاعدة البيانات بنجاح",
        "message_en": "Database has been fully reset and reseeded",
        "deleted": deleted_counts,
        "seed_result": result,
        "timestamp": now,
        "note": "كلمة المرور لجميع المستخدمين: 123456",
        "warning": "يُنصح بإزالة RESET_SECRET_KEY من environment variables بعد الاستخدام"
    }

