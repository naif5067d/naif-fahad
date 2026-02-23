"""
Admin Routes - إدارة النظام
============================================================
- تغيير سياسة الإجازة السنوية (21/30)
- ترحيل الإجازات (بقرار إداري)
- تنبيهات الأرصدة
- إعادة تعيين البيانات
- التزامن التلقائي
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
from services.auto_sync import auto_sync_database, force_full_sync
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
    إعادة تعيين أو إنشاء مستخدم STAS للطوارئ
    اسم المستخدم: stas506
    كلمة المرور: 654321
    
    إذا لم يكن المستخدم موجوداً، سيتم إنشاؤه
    """
    from utils.auth import hash_password
    import uuid as uuid_module
    
    # مفتاح الطوارئ
    if body.emergency_key != "EMERGENCY_STAS_2026":
        raise HTTPException(status_code=403, detail="مفتاح غير صحيح")
    
    # تشفير كلمة المرور
    new_hash = hash_password("654321")
    now = datetime.now(timezone.utc).isoformat()
    
    # البحث عن أي مستخدم stas
    stas_user = await db.users.find_one({
        "$or": [
            {"username": "stas"},
            {"username": "stas506"},
            {"role": "stas"}
        ]
    })
    
    if stas_user:
        # تحديث المستخدم الموجود
        await db.users.update_one(
            {"_id": stas_user["_id"]},
            {"$set": {
                "username": "stas506",
                "password_hash": new_hash,
                "is_active": True
            }}
        )
        action = "updated"
    else:
        # إنشاء مستخدم جديد
        new_user = {
            "id": str(uuid_module.uuid5(uuid_module.NAMESPACE_DNS, "stas506")),
            "username": "stas506",
            "password_hash": new_hash,
            "full_name": "STAS",
            "full_name_ar": "ستاس",
            "role": "stas",
            "email": "stas@daralcode.com",
            "is_active": True,
            "employee_id": "EMP-STAS",
            "created_at": now
        }
        await db.users.insert_one(new_user)
        action = "created"
    
    return {
        "message_ar": f"تم {'تحديث' if action == 'updated' else 'إنشاء'} مستخدم STAS بنجاح",
        "message_en": f"STAS user has been {action} successfully",
        "username": "stas506",
        "password": "654321",
        "action": action
    }


# ============================================================
# إصلاح إعدادات الشركة (إزالة دار الأركان)
# ============================================================

@router.post("/fix-company-branding")
async def fix_company_branding(body: ResetStasPasswordRequest):
    """
    إصلاح إعدادات الشركة - تغيير دار الأركان إلى دار الكود
    """
    if body.emergency_key != "EMERGENCY_STAS_2026":
        raise HTTPException(status_code=403, detail="مفتاح غير صحيح")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث إعدادات الشركة
    await db.company_settings.update_one(
        {"key": "login_page"},
        {"$set": {
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "company_name_en": "DAR AL CODE",
            "welcome_text_ar": "أنتم الدار ونحن الكود",
            "welcome_text_en": "You are the Home, We are the Code",
            "updated_at": now
        }},
        upsert=True
    )
    
    return {
        "message_ar": "تم تحديث إعدادات الشركة بنجاح - أصبح الاسم: دار الكود",
        "message_en": "Company branding updated - Now: DAR AL CODE",
        "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
        "company_name_en": "DAR AL CODE"
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


# ============================================================
# إعادة تعيين النظام من تاريخ محدد (حذف البيانات القديمة)
# ============================================================

class SystemResetFromDateRequest(BaseModel):
    reset_date: str  # YYYY-MM-DD - التاريخ الذي يبدأ منه النظام
    emergency_key: str
    confirm: bool = False


@router.post("/system-reset-from-date")
async def system_reset_from_date(body: SystemResetFromDateRequest):
    """
    إعادة تعيين النظام من تاريخ محدد
    
    يحذف:
    - سجلات الحضور (daily_status) قبل التاريخ
    - سجلات البصمة (attendance_ledger) قبل التاريخ
    - العقوبات (penalties) قبل التاريخ
    - المعاملات المالية (transactions, finance_entries) قبل التاريخ
    - طلبات الإجازات (leave_requests) قبل التاريخ
    - سجلات الإجازات (leave_ledger) قبل التاريخ
    
    يُبقي:
    - الموظفين
    - العقود
    - بطاقات مواقع العمل
    - إعدادات الشركة
    """
    # التحقق من مفتاح الطوارئ
    if body.emergency_key != "EMERGENCY_STAS_2026":
        raise HTTPException(status_code=403, detail="مفتاح غير صحيح")
    
    if not body.confirm:
        raise HTTPException(status_code=400, detail="يجب تأكيد العملية (confirm: true)")
    
    reset_date = body.reset_date
    now = datetime.now(timezone.utc).isoformat()
    
    deleted_counts = {}
    
    # 1. حذف سجلات الحضور اليومية قبل التاريخ
    result = await db.daily_status.delete_many({"date": {"$lt": reset_date}})
    deleted_counts["daily_status"] = result.deleted_count
    
    # 2. حذف سجلات البصمة قبل التاريخ
    result = await db.attendance_ledger.delete_many({"date": {"$lt": reset_date}})
    deleted_counts["attendance_ledger"] = result.deleted_count
    
    # 3. حذف العقوبات قبل التاريخ
    result = await db.penalties.delete_many({
        "$or": [
            {"date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["penalties"] = result.deleted_count
    
    # 4. حذف المعاملات المالية قبل التاريخ
    result = await db.transactions.delete_many({
        "$or": [
            {"date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["transactions"] = result.deleted_count
    
    # 5. حذف قيود المالية قبل التاريخ
    result = await db.finance_entries.delete_many({
        "$or": [
            {"date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["finance_entries"] = result.deleted_count
    
    # 6. حذف طلبات الإجازات قبل التاريخ
    result = await db.leave_requests.delete_many({
        "$or": [
            {"start_date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["leave_requests"] = result.deleted_count
    
    # 7. حذف سجلات الإجازات قبل التاريخ
    result = await db.leave_ledger.delete_many({
        "$or": [
            {"date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["leave_ledger"] = result.deleted_count
    
    # 8. حذف سجلات الغياب غير المسوى قبل التاريخ
    result = await db.unsettled_absences.delete_many({"date": {"$lt": reset_date}})
    deleted_counts["unsettled_absences"] = result.deleted_count
    
    # 9. حذف سجلات الخصم قبل التاريخ
    result = await db.deduction_log.delete_many({
        "$or": [
            {"date": {"$lt": reset_date}},
            {"created_at": {"$lt": reset_date}}
        ]
    })
    deleted_counts["deduction_log"] = result.deleted_count
    
    # 10. حذف الساعات الشهرية قبل الشهر
    reset_month = reset_date[:7]  # YYYY-MM
    result = await db.monthly_hours.delete_many({"month": {"$lt": reset_month}})
    deleted_counts["monthly_hours"] = result.deleted_count
    
    # حساب إجمالي المحذوفات
    total_deleted = sum(v for v in deleted_counts.values() if isinstance(v, int))
    
    # سجل التدقيق
    await db.audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "action": "system_reset_from_date",
        "reset_date": reset_date,
        "deleted_counts": deleted_counts,
        "total_deleted": total_deleted,
        "created_at": now,
        "note": "إعادة تعيين النظام - كل ما قبل هذا التاريخ يُعتبر تجربة"
    })
    
    return {
        "success": True,
        "message_ar": f"تم إعادة تعيين النظام بنجاح. البيانات قبل {reset_date} تم حذفها",
        "message_en": f"System reset successful. Data before {reset_date} has been deleted",
        "reset_date": reset_date,
        "deleted": deleted_counts,
        "total_deleted": total_deleted,
        "kept": ["employees", "contracts_v2", "work_locations", "settings", "users"],
        "timestamp": now
    }

