from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import os
import uuid
import base64

# Import Services
from services.leave_service import get_employee_leave_summary
from services.attendance_service import get_employee_attendance_summary, get_unsettled_absences
from services.service_calculator import get_employee_service_info
from services.hr_policy import (
    calculate_pro_rata_entitlement,
    get_employee_annual_policy,
    get_status_for_viewer,
    get_employee_active_transactions,
    format_datetime_riyadh
)

router = APIRouter(prefix="/api/employees", tags=["employees"])


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    full_name_ar: Optional[str] = None
    is_active: Optional[bool] = None
    department: Optional[str] = None
    department_ar: Optional[str] = None
    position: Optional[str] = None
    position_ar: Optional[str] = None
    # بيانات الإقامة
    iqama_number: Optional[str] = None  # رقم الإقامة
    iqama_expiry_date: Optional[str] = None  # تاريخ انتهاء الإقامة YYYY-MM-DD
    nationality: Optional[str] = None  # الجنسية


class SupervisorAssignment(BaseModel):
    supervisor_id: Optional[str] = None


@router.get("")
async def list_employees(user=Depends(get_current_user)):
    role = user.get('role')
    
    # تحديد الحقول المطلوبة
    fields = {
        "_id": 0, "id": 1, "employee_number": 1, "full_name": 1, "full_name_ar": 1, 
        "department": 1, "department_ar": 1, "position": 1, "position_ar": 1, 
        "is_active": 1, "status": 1, "email": 1, "phone": 1, "code": 1, 
        "supervisor_id": 1, "user_id": 1, "photo_url": 1, "hire_date": 1, 
        "start_date": 1, "created_at": 1,
        # حقول الإقامة
        "iqama_number": 1, "iqama_expiry_date": 1, "nationality": 1
    }
    
    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if emp:
            emp = await _add_experience_years(emp)
        return [emp] if emp else []
    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        reports = await db.employees.find(
            {"$or": [{"id": emp['id']}, {"supervisor_id": emp['id']}]}, 
            fields
        ).to_list(100)
        # إضافة سنوات الخبرة لكل موظف
        reports = [await _add_experience_years(e) for e in reports]
        return reports
    else:
        employees = await db.employees.find({}, fields).to_list(500)
        # إضافة سنوات الخبرة لكل موظف
        employees = [await _add_experience_years(e) for e in employees]
        return employees


async def _add_experience_years(emp: dict) -> dict:
    """إضافة سنوات الخبرة للموظف بناءً على hire_date أو start_date من العقد"""
    if not emp:
        return emp
    
    # محاولة الحصول على تاريخ التعيين
    hire_date = emp.get('hire_date') or emp.get('start_date')
    
    # إذا لم يوجد، نحاول من العقد
    if not hire_date:
        contract = await db.contracts_v2.find_one(
            {"employee_id": emp.get('id'), "status": {"$in": ["active", "active_renewed"]}},
            {"_id": 0, "start_date": 1}
        )
        if contract:
            hire_date = contract.get('start_date')
    
    # حساب سنوات الخبرة
    if hire_date:
        try:
            from datetime import datetime
            if isinstance(hire_date, str):
                hire_dt = datetime.strptime(hire_date[:10], "%Y-%m-%d")
            else:
                hire_dt = hire_date
            
            today = datetime.now()
            years = (today - hire_dt).days / 365.25
            emp['experience_years'] = round(years, 1)
            emp['years_of_service'] = int(years)
        except:
            emp['experience_years'] = 0
            emp['years_of_service'] = 0
    else:
        emp['experience_years'] = 0
        emp['years_of_service'] = 0
    
    return emp


@router.get("/{employee_id}")
async def get_employee(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    role = user.get('role')
    # السماح للمدراء والـ CEO بالاطلاع على بيانات الموظفين
    if role in ['stas', 'sultan', 'naif', 'mohammed', 'supervisor']:
        return emp
    # الموظف العادي يرى بياناته فقط
    if role == 'employee':
        own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not own or own['id'] != employee_id:
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول")
    return emp


@router.patch("/{employee_id}")
async def update_employee(employee_id: str, update: EmployeeUpdate, user=Depends(get_current_user)):
    """تحديث بيانات الموظف - STAS أو الموظف نفسه لبياناته الشخصية"""
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من الصلاحيات
    is_admin = user.get('role') in ['stas', 'sultan', 'naif']
    is_self = user.get('employee_id') == employee_id
    
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="غير مصرح لك بتعديل بيانات هذا الموظف")
    
    # الموظف العادي يمكنه فقط تعديل الاسم والبريد
    allowed_fields_for_self = {'full_name', 'full_name_ar', 'email', 'phone'}
    
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد تحديثات")
    
    # تصفية الحقول للموظف غير المسؤول
    if is_self and not is_admin:
        updates = {k: v for k, v in updates.items() if k in allowed_fields_for_self}
        if not updates:
            raise HTTPException(status_code=400, detail="لا يمكنك تعديل هذه الحقول")
    
    await db.employees.update_one({"id": employee_id}, {"$set": updates})
    if 'full_name' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name": updates['full_name']}})
        # تحديث الاسم في العقود أيضاً
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"employee_name": updates['full_name']}}
        )
        # تحديث الاسم في المعاملات
        await db.transactions.update_many(
            {"data.employee_id": employee_id},
            {"$set": {"data.employee_name": updates['full_name']}}
        )
    if 'full_name_ar' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name_ar": updates['full_name_ar']}})
        # تحديث الاسم العربي في العقود أيضاً
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"employee_name_ar": updates['full_name_ar']}}
        )
        # تحديث الاسم العربي في المعاملات
        await db.transactions.update_many(
            {"data.employee_id": employee_id},
            {"$set": {"data.employee_name_ar": updates['full_name_ar']}}
        )
    if 'department' in updates:
        # تحديث القسم في العقود
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"department": updates['department']}}
        )
        # تحديث القسم في المعاملات
        await db.transactions.update_many(
            {"data.employee_id": employee_id},
            {"$set": {"data.department": updates['department']}}
        )
        # تحديث القسم في سجلات الحضور الشهرية
        await db.monthly_hours.update_many(
            {"employee_id": employee_id},
            {"$set": {"department": updates['department']}}
        )
    if 'department_ar' in updates:
        # تحديث القسم العربي في كل مكان
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"department_ar": updates['department_ar']}}
        )
        await db.transactions.update_many(
            {"data.employee_id": employee_id},
            {"$set": {"data.department_ar": updates['department_ar']}}
        )
    if 'position' in updates:
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"position": updates['position']}}
        )
    if 'position_ar' in updates:
        await db.contracts_v2.update_many(
            {"employee_id": employee_id},
            {"$set": {"position_ar": updates['position_ar']}}
        )
    if 'is_active' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"is_active": updates['is_active']}})
    updated = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    return updated


@router.get("/{employee_id}/profile360")
async def get_profile_360(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    role = user.get('role')
    # السماح للمدراء والـ CEO بالاطلاع على بيانات الموظفين
    if role not in ['stas', 'sultan', 'naif', 'mohammed', 'supervisor']:
        if role == 'employee':
            own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
            if not own or own['id'] != employee_id:
                raise HTTPException(status_code=403, detail="غير مصرح بالوصول")

    leave_entries = await db.leave_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    leave_balance = {}
    for e in leave_entries:
        lt = e['leave_type']
        if lt not in leave_balance:
            leave_balance[lt] = 0
        leave_balance[lt] += e['days'] if e['type'] == 'credit' else -e['days']

    finance_entries = await db.finance_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    attendance_entries = await db.attendance_ledger.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("timestamp", -1).to_list(50)
    warning_entries = await db.warning_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    asset_entries = await db.asset_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(100)
    transactions = await db.transactions.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)

    return {
        "employee": emp,
        "leave_balance": leave_balance,
        "leave_ledger": leave_entries[-20:],
        "finance_ledger": finance_entries[-20:],
        "attendance_ledger": attendance_entries,
        "warning_ledger": warning_entries,
        "asset_ledger": asset_entries,
        "transactions": transactions
    }


@router.get("/{employee_id}/leave-balance")
async def get_leave_balance_endpoint(employee_id: str, user=Depends(get_current_user)):
    entries = await db.leave_ledger.find({"employee_id": employee_id}, {"_id": 0}).to_list(1000)
    balance = {}
    for e in entries:
        lt = e['leave_type']
        if lt not in balance:
            balance[lt] = 0
        balance[lt] += e['days'] if e['type'] == 'credit' else -e['days']
    return balance


# ==================== SUPERVISOR ASSIGNMENT ====================

@router.put("/{employee_id}/supervisor")
async def assign_supervisor(
    employee_id: str, 
    body: SupervisorAssignment,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """
    تعيين المشرف المباشر للموظف
    الطلبات ستمر للمشرف أولاً
    """
    # التحقق من وجود الموظف
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إذا supervisor_id فارغ أو None - إزالة المشرف
    if not body.supervisor_id:
        await db.employees.update_one(
            {"id": employee_id},
            {
                "$unset": {"supervisor_id": "", "supervisor_name": "", "supervisor_name_ar": ""},
                "$set": {"supervisor_updated_at": now, "supervisor_updated_by": user['user_id']}
            }
        )
        return {"message": "تم إزالة المشرف بنجاح", "employee_id": employee_id}
    
    # التحقق من وجود المشرف
    supervisor = await db.employees.find_one({"id": body.supervisor_id})
    if not supervisor:
        raise HTTPException(status_code=404, detail="المشرف غير موجود")
    
    # التأكد أن المشرف ليس هو نفس الموظف
    if employee_id == body.supervisor_id:
        raise HTTPException(status_code=400, detail="لا يمكن تعيين الموظف كمشرف لنفسه")
    
    # تحديث الموظف
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "supervisor_id": body.supervisor_id,
            "supervisor_name": supervisor.get('full_name', ''),
            "supervisor_name_ar": supervisor.get('full_name_ar', ''),
            "supervisor_updated_at": now,
            "supervisor_updated_by": user['user_id']
        }}
    )
    
    return {
        "message": "تم تعيين المشرف بنجاح",
        "employee_id": employee_id,
        "supervisor_id": body.supervisor_id,
        "supervisor_name": supervisor.get('full_name_ar', supervisor.get('full_name', ''))
    }


@router.delete("/{employee_id}/supervisor")
async def remove_supervisor(employee_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """إزالة المشرف المباشر"""
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$unset": {"supervisor_id": "", "supervisor_name": "", "supervisor_name_ar": ""}}
    )
    
    return {"message": "تم إزالة المشرف بنجاح"}


class BulkSupervisorAssign(BaseModel):
    supervisor_id: str
    employee_ids: list


@router.put("/bulk-supervisor")
async def assign_bulk_supervisor(
    body: BulkSupervisorAssign, 
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """
    تعيين موظفين متعددين تحت مشرف واحد
    
    - يزيل المشرف من الموظفين السابقين (غير المحددين)
    - يعيّن المشرف للموظفين الجدد
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # التحقق من وجود المشرف
    supervisor = await db.employees.find_one({"id": body.supervisor_id})
    if not supervisor:
        raise HTTPException(status_code=404, detail="المشرف غير موجود")
    
    # إزالة المشرف من الموظفين السابقين (غير المحددين في القائمة الجديدة)
    await db.employees.update_many(
        {
            "supervisor_id": body.supervisor_id,
            "id": {"$nin": body.employee_ids}
        },
        {"$unset": {"supervisor_id": "", "supervisor_name": "", "supervisor_name_ar": ""}}
    )
    
    # تعيين المشرف للموظفين الجدد
    updated = 0
    for emp_id in body.employee_ids:
        # التأكد أن الموظف ليس هو المشرف نفسه
        if emp_id == body.supervisor_id:
            continue
        
        result = await db.employees.update_one(
            {"id": emp_id},
            {"$set": {
                "supervisor_id": body.supervisor_id,
                "supervisor_name": supervisor.get('full_name', ''),
                "supervisor_name_ar": supervisor.get('full_name_ar', ''),
                "supervisor_updated_at": now,
                "supervisor_updated_by": user['user_id']
            }}
        )
        if result.modified_count > 0:
            updated += 1
    
    return {
        "success": True,
        "message": f"تم تعيين {updated} موظف تحت المشرف {supervisor.get('full_name_ar', '')}",
        "supervisor_id": body.supervisor_id,
        "assigned_count": len(body.employee_ids),
        "updated_count": updated
    }


# ==================== ASSIGNED LOCATIONS ====================

@router.get("/{employee_id}/assigned-locations")
async def get_employee_assigned_locations(employee_id: str, user=Depends(get_current_user)):
    """
    جلب جميع مواقع العمل المعينة للموظف
    يُستخدم في صفحة الحضور لاختيار موقع التبصيم
    """
    # التحقق من الصلاحيات
    role = user.get('role')
    is_admin = role in ['stas', 'sultan', 'naif']
    is_self = user.get('employee_id') == employee_id
    
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="غير مصرح بالوصول")
    
    # جلب المواقع المعينة للموظف
    locations = await db.work_locations.find(
        {"assigned_employees": employee_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    return locations


# ==================== DELETE EMPLOYEE ====================

@router.delete("/{employee_id}/permanent")
async def delete_employee_permanent(employee_id: str, user=Depends(require_roles('stas'))):
    """
    🗑️ حذف موظف نهائياً من الجذور - STAS فقط
    
    يحذف:
    - سجل الموظف
    - العقود
    - سجلات الحضور
    - سجلات الإجازات
    - المعاملات
    - المستخدم المرتبط
    - كل شيء متعلق بهذا الموظف
    
    ⚠️ هذا الإجراء لا يمكن التراجع عنه!
    """
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    emp_name = emp.get('full_name') or emp.get('name_ar') or emp.get('name') or employee_id
    
    deleted_counts = {}
    
    # 1. حذف العقود
    r = await db.contracts.delete_many({"employee_id": employee_id})
    deleted_counts['contracts'] = r.deleted_count
    
    r = await db.contracts_v2.delete_many({"employee_id": employee_id})
    deleted_counts['contracts_v2'] = r.deleted_count
    
    # 2. حذف سجلات الحضور
    r = await db.attendance_ledger.delete_many({"employee_id": employee_id})
    deleted_counts['attendance_ledger'] = r.deleted_count
    
    # 3. حذف الحالة اليومية
    r = await db.daily_status.delete_many({"employee_id": employee_id})
    deleted_counts['daily_status'] = r.deleted_count
    
    # 4. حذف سجلات الإجازات
    r = await db.leave_ledger.delete_many({"employee_id": employee_id})
    deleted_counts['leave_ledger'] = r.deleted_count
    
    # 5. حذف المعاملات
    r = await db.transactions.delete_many({"employee_id": employee_id})
    deleted_counts['transactions'] = r.deleted_count
    
    # 6. حذف الخصومات
    r = await db.penalties.delete_many({"employee_id": employee_id})
    deleted_counts['penalties'] = r.deleted_count
    
    # 7. حذف الأجهزة المسجلة
    r = await db.employee_devices.delete_many({"employee_id": employee_id})
    deleted_counts['employee_devices'] = r.deleted_count
    
    # 8. حذف جلسات الدخول
    r = await db.login_sessions.delete_many({"employee_id": employee_id})
    deleted_counts['login_sessions'] = r.deleted_count
    
    # 9. حذف المستخدم
    r = await db.users.delete_many({"employee_id": employee_id})
    deleted_counts['users'] = r.deleted_count
    
    # 10. حذف الموظف نفسه
    r = await db.employees.delete_one({"id": employee_id})
    deleted_counts['employees'] = r.deleted_count
    
    # تسجيل عملية الحذف
    await db.audit_log.insert_one({
        "action": "permanent_delete_employee",
        "employee_id": employee_id,
        "employee_name": emp_name,
        "deleted_by": user['user_id'],
        "deleted_counts": deleted_counts,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": f"تم حذف الموظف '{emp_name}' نهائياً",
        "employee_id": employee_id,
        "deleted_counts": deleted_counts
    }


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, user=Depends(require_roles('stas'))):
    """
    حذف موظف - STAS فقط
    الشروط:
    1. يجب عدم وجود عقد نشط
    2. يجب عدم وجود عقد (يعني حذف الموظف الذي أُضيف بالخطأ)
    أو إنهاء العقد أولاً ثم يمكن الحذف
    """
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من العقود
    active_contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "active"
    })
    
    if active_contract:
        raise HTTPException(
            status_code=400, 
            detail="لا يمكن حذف موظف لديه عقد نشط. يجب إنهاء العقد أولاً من صفحة إدارة العقود"
        )
    
    # حذف المستخدم إن وجد
    await db.users.delete_many({"employee_id": employee_id})
    
    # حذف الموظف
    await db.employees.delete_one({"id": employee_id})
    
    return {
        "message": "تم حذف الموظف بنجاح",
        "employee_id": employee_id
    }


# ==================== EMPLOYEE COMPREHENSIVE SUMMARY ====================

@router.get("/{employee_id}/summary")
async def get_employee_summary(employee_id: str, user=Depends(get_current_user)):
    """
    ملخص شامل للموظف - محدث HR Policy
    
    للموظف:
    - الحضور/الانصراف
    - رصيد الإجازة السنوية فقط (Pro-Rata)
    - الخصومات والإنذارات الخاصة به
    
    للإدارة:
    - كل البيانات + الحقول الجاهزة للربط
    """
    role = user.get('role')
    viewer_is_admin = role in ['sultan', 'naif', 'stas', 'mohammed', 'ceo', 'admin']
    
    if role == 'employee':
        own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not own or own['id'] != employee_id:
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول")
    
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # 1. العقد الحالي
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": {"$in": ["active", "terminated"]}
    }, {"_id": 0})
    
    # 2. معلومات الخدمة
    service_info = await get_employee_service_info(employee_id)
    
    # 3. سياسة الإجازة السنوية (21/30)
    policy = await get_employee_annual_policy(employee_id)
    
    # 4. رصيد الإجازة Pro-Rata
    pro_rata = await calculate_pro_rata_entitlement(employee_id)
    
    # 5. ملخص الحضور
    attendance_summary = await get_employee_attendance_summary(employee_id)
    
    # 6. حالة حضور اليوم - من daily_status للحصول على الحالة الحقيقية
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # أولاً نجلب حالة اليوم من daily_status
    today_daily_status = await db.daily_status.find_one({
        "employee_id": employee_id,
        "date": today
    }, {"_id": 0})
    
    # ثم نجلب وقت الحضور من attendance_ledger
    today_attendance = await db.attendance_ledger.find_one({
        "employee_id": employee_id,
        "date": today,
        "type": "check_in"
    })
    
    # التحقق من الإجازات النشطة من جدول transactions
    active_leave = await db.transactions.find_one({
        "$or": [
            {"employee_id": employee_id},
            {"data.employee_id": employee_id}
        ],
        "type": {"$regex": "leave", "$options": "i"},
        "status": "executed",
        "data.start_date": {"$lte": today},
        "data.end_date": {"$gte": today}
    }, {"_id": 0, "type": 1, "data.start_date": 1, "data.end_date": 1})
    
    # التحقق من المهمات النشطة
    active_mission = await db.transactions.find_one({
        "$or": [
            {"employee_id": employee_id},
            {"data.employee_id": employee_id}
        ],
        "type": {"$regex": "mission|assignment", "$options": "i"},
        "status": "executed",
        "data.start_date": {"$lte": today},
        "data.end_date": {"$gte": today}
    }, {"_id": 0, "type": 1})
    
    # التحقق من العطل الرسمية
    holiday_today = await db.holidays.find_one({
        "date": today,
        "is_active": {"$ne": False}
    }, {"_id": 0})
    
    # التحقق من عطلة نهاية الأسبوع
    from datetime import datetime as dt
    day_of_week = dt.strptime(today, "%Y-%m-%d").weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    is_weekend = day_of_week == 4  # Friday
    
    # تحديد حالة اليوم بالترتيب الصحيح
    today_status = 'not_checked_in'
    today_status_ar = 'لم يسجل'
    
    # 1. أولاً: التحقق من الإجازة المعتمدة
    if active_leave:
        leave_type = active_leave.get('type', '')
        if 'admin' in leave_type.lower():
            today_status = 'leave'
            today_status_ar = 'إجازة إدارية'
        elif 'sick' in leave_type.lower():
            today_status = 'leave'
            today_status_ar = 'إجازة مرضية'
        elif 'emergency' in leave_type.lower():
            today_status = 'leave'
            today_status_ar = 'إجازة طارئة'
        else:
            today_status = 'leave'
            today_status_ar = 'إجازة'
    
    # 2. ثانياً: التحقق من المهمة
    elif active_mission:
        today_status = 'mission'
        today_status_ar = 'في مهمة'
    
    # 3. ثالثاً: التحقق من العطلة الرسمية
    elif holiday_today:
        today_status = 'holiday'
        today_status_ar = 'عطلة رسمية'
    
    # 4. رابعاً: التحقق من عطلة نهاية الأسبوع
    elif is_weekend:
        today_status = 'weekend'
        today_status_ar = 'عطلة أسبوعية'
    
    # 5. خامساً: التحقق من daily_status
    elif today_daily_status:
        final_status = today_daily_status.get('final_status', '')
        if final_status == 'ABSENT':
            today_status = 'absent'
            today_status_ar = 'غائب'
        elif final_status in ('ON_LEAVE', 'LEAVE', 'ON_ADMIN_LEAVE'):
            today_status = 'leave'
            today_status_ar = today_daily_status.get('decision_reason_ar', 'إجازة') or 'إجازة'
        elif final_status == 'HOLIDAY':
            today_status = 'holiday'
            today_status_ar = 'عطلة رسمية'
        elif final_status == 'WEEKEND':
            today_status = 'weekend'
            today_status_ar = 'عطلة أسبوعية'
        elif final_status in ('ON_MISSION', 'MISSION'):
            today_status = 'mission'
            today_status_ar = 'في مهمة'
        elif 'LATE' in final_status:
            today_status = 'late'
            today_status_ar = 'متأخر'
        elif final_status in ('PRESENT', 'PRESENT_FULL', 'PRESENT_EARLY_LEAVE'):
            today_status = 'present'
            today_status_ar = 'حاضر'
        else:
            today_status = 'present' if today_attendance else 'not_checked_in'
            today_status_ar = 'حاضر' if today_attendance else 'لم يسجل'
    
    # 6. سادساً: التحقق من البصمة فقط
    elif today_attendance:
        today_status = 'present'
        today_status_ar = 'حاضر'
    
    # وقت الحضور
    check_in_time = None
    check_out_time = None
    late_minutes_today = 0
    decision_reason_ar = None
    
    # أولاً: من daily_status (التعديل الإداري)
    if today_daily_status:
        check_in_time = today_daily_status.get('check_in_time') or today_daily_status.get('check_in')
        check_out_time = today_daily_status.get('check_out_time') or today_daily_status.get('check_out')
        late_minutes_today = today_daily_status.get('late_minutes', 0) or 0
        decision_reason_ar = today_daily_status.get('decision_reason_ar', '')
        
        # تنسيق الوقت إذا كان timestamp
        if check_in_time and 'T' in str(check_in_time):
            check_in_time = str(check_in_time).split('T')[1][:5]
        if check_out_time and 'T' in str(check_out_time):
            check_out_time = str(check_out_time).split('T')[1][:5]
    
    # ثانياً: من attendance_ledger (البصمة الفعلية)
    if not check_in_time and today_attendance:
        check_in_time = today_attendance.get('time', today_attendance.get('timestamp', ''))
        if check_in_time and 'T' in check_in_time:
            check_in_time = check_in_time.split('T')[1][:5]
    
    # Get check_out from attendance_ledger if not found
    if not check_out_time:
        today_checkout = await db.attendance_ledger.find_one({
            "employee_id": employee_id,
            "date": today,
            "type": "check_out"
        }, {"_id": 0, "timestamp": 1, "time": 1})
        if today_checkout:
            check_out_time = today_checkout.get('time', today_checkout.get('timestamp', ''))
            if check_out_time and 'T' in check_out_time:
                check_out_time = check_out_time.split('T')[1][:5]
    
    # 7. بيانات الشهر الحالي (للجميع)
    month_start = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")
    month_end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # إحصائيات الحضور الشهرية (تأخير، غياب)
    month_attendance = await db.daily_status.find({
        "employee_id": employee_id,
        "date": {"$gte": month_start, "$lte": month_end}
    }, {"_id": 0}).to_list(31)
    
    late_count = sum(1 for a in month_attendance if a.get('is_late') or 'LATE' in str(a.get('final_status', '')))
    absent_count = sum(1 for a in month_attendance if a.get('final_status') == 'ABSENT')
    total_late_minutes = sum(a.get('late_minutes', 0) or 0 for a in month_attendance)
    monthly_hours = round(sum((a.get('actual_hours') or a.get('worked_hours') or 0) for a in month_attendance), 1)
    
    # المعاملات المعلقة للموظف
    pending_txs = await db.transactions.count_documents({
        "data.employee_id": employee_id,
        "status": {"$regex": "^pending"}
    })
    
    # الخصومات المنفذة هذا الشهر (للموظف أيضاً)
    month_deductions = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit",
        "created_at": {"$gte": month_start}
    }, {"_id": 0}).sort("created_at", -1).to_list(10)
    
    deductions_for_employee = []
    for d in month_deductions[:3]:
        deductions_for_employee.append({
            "amount": d.get('amount', 0),
            "reason": d.get('note', d.get('description', '')),
            "reason_ar": d.get('note', d.get('description', '')),
            "date": d.get('created_at', '')[:10] if d.get('created_at') else ''
        })
    
    # الإنذارات (للموظف أيضاً)
    warnings = await db.warnings.find({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0}).sort("created_at", -1).to_list(5)
    
    warnings_for_employee = []
    for w in warnings[:3]:
        warnings_for_employee.append({
            "level": w.get('level', 1),
            "reason": w.get('reason', ''),
            "reason_ar": w.get('reason_ar', w.get('reason', '')),
            "date": w.get('created_at', '')[:10] if w.get('created_at') else ''
        })
    
    # بيانات الموظف الشاملة (للجميع)
    # حساب ساعات النقص من daily_status
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    month_statuses = await db.daily_status.find({
        "employee_id": employee_id,
        "date": {"$regex": f"^{current_month}"}
    }, {"_id": 0}).to_list(100)
    
    total_late_minutes_month = sum(s.get("late_minutes", 0) for s in month_statuses)
    total_early_leave_minutes = sum(s.get("early_leave_minutes", 0) for s in month_statuses)
    total_deficit_minutes = total_late_minutes_month + total_early_leave_minutes
    deficit_hours = round(total_deficit_minutes / 60, 2)
    
    # === حساب الساعات المطلوبة شهرياً بشكل ديناميكي ===
    # احتساب أيام العمل الفعلية (بدون الجمعة والسبت والعطل الرسمية)
    from calendar import monthrange
    now = datetime.now(timezone.utc)
    _, days_in_month = monthrange(now.year, now.month)
    
    # جلب موقع العمل للحصول على ساعات الدوام
    work_location = None
    if emp.get('work_location_id'):
        work_location = await db.work_locations.find_one(
            {"id": emp['work_location_id'], "is_active": True},
            {"_id": 0, "daily_hours": 1, "work_days": 1}
        )
    if not work_location:
        work_location = await db.work_locations.find_one(
            {"assigned_employees": employee_id, "is_active": True},
            {"_id": 0, "daily_hours": 1, "work_days": 1}
        )
    
    daily_hours = work_location.get('daily_hours', 8) if work_location else 8
    work_days_config = work_location.get('work_days', {}) if work_location else {}
    
    # === التحقق من وضع رمضان ===
    ramadan_settings = await db.settings.find_one({"type": "ramadan_mode"}, {"_id": 0})
    is_ramadan_active = False
    if ramadan_settings:
        is_active = ramadan_settings.get('is_active', False)
        start_date = ramadan_settings.get('start_date', '')
        end_date = ramadan_settings.get('end_date', '')
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        if is_active and start_date and end_date:
            if start_date <= today <= end_date:
                is_ramadan_active = True
                # استخدام ساعات رمضان من موقع العمل أو الافتراضي (6 ساعات)
                daily_hours = work_location.get('ramadan_daily_hours', 6) if work_location else 6
    
    # جلب العطل الرسمية لهذا الشهر
    month_holidays = await db.holidays.find({
        "date": {"$regex": f"^{current_month}"},
        "is_active": {"$ne": False}
    }, {"_id": 0, "date": 1}).to_list(50)
    holiday_dates = {h['date'] for h in month_holidays}
    
    # حساب أيام العمل الفعلية
    work_days_count = 0
    for day in range(1, days_in_month + 1):
        date_str = f"{current_month}-{day:02d}"
        date_obj = datetime(now.year, now.month, day)
        day_of_week = date_obj.weekday()  # 0=Monday, 4=Friday, 5=Saturday
        
        # تخطي العطل الرسمية
        if date_str in holiday_dates:
            continue
        
        # فحص إذا كان يوم عمل (من إعدادات الموقع أو الافتراضي)
        day_names = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday"}
        day_name = day_names[day_of_week]
        
        if work_days_config:
            is_work_day = work_days_config.get(day_name, True)
        else:
            # الافتراضي: الجمعة والسبت عطلة
            is_work_day = day_of_week not in [4, 5]
        
        if is_work_day:
            work_days_count += 1
    
    required_monthly_hours = work_days_count * daily_hours
    
    # === رصيد الخروج المبكر (ساعات الاستئذان) ===
    # الأولوية: 1) من العقد (monthly_permission_hours)  2) من الإعدادات العامة  3) الافتراضي (3 ساعات)
    monthly_early_leave_balance = 3  # الافتراضي
    
    # أولاً: من العقد
    if contract:
        # يُسمى في العقد "monthly_permission_hours" أو "early_leave_balance"
        contract_balance = contract.get('monthly_permission_hours') or contract.get('early_leave_balance')
        if contract_balance is not None:
            monthly_early_leave_balance = contract_balance
    else:
        # ثانياً: من الإعدادات العامة
        early_leave_settings = await db.settings.find_one(
            {"type": "early_leave_balance"},
            {"_id": 0}
        )
        if early_leave_settings:
            monthly_early_leave_balance = early_leave_settings.get('monthly_hours', 3)
    
    # حساب الخروج المبكر المستخدم هذا الشهر (من طلبات الخروج المبكر والاستئذان المعتمدة)
    early_leave_requests = await db.transactions.find({
        "$or": [
            {"employee_id": employee_id},
            {"data.employee_id": employee_id}
        ],
        "type": {"$in": ["early_leave", "early_leave_request", "early_departure", "permission", "استئذان"]},
        "status": "executed",
        "data.date": {"$regex": f"^{current_month}"},
        "data.deduct_from_balance": {"$ne": False}  # فقط الطلبات التي تُخصم من الرصيد
    }, {"_id": 0, "data.hours": 1, "data.minutes": 1, "data.duration_minutes": 1}).to_list(100)
    
    used_early_leave_minutes = 0
    for req in early_leave_requests:
        data = req.get('data', {})
        hours = data.get('hours', 0) or 0
        minutes = data.get('minutes', 0) or data.get('duration_minutes', 0) or 0
        used_early_leave_minutes += (hours * 60) + minutes
    
    used_early_leave_hours = round(used_early_leave_minutes / 60, 2)
    remaining_early_leave_balance = max(0, monthly_early_leave_balance - used_early_leave_hours)
    
    employee_summary = {
        "employee": emp,
        "contract": contract,
        "service_info": service_info,
        "attendance": {
            "today_status": today_status,
            "today_status_ar": today_status_ar,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "late_minutes": late_minutes_today,
            "decision_reason_ar": decision_reason_ar,
            "monthly_hours": monthly_hours,
            "required_monthly_hours": required_monthly_hours,
            "remaining_hours": max(0, required_monthly_hours - monthly_hours),
            "deficit_hours": deficit_hours,
            "deficit_minutes": total_deficit_minutes,
            "late_minutes_month": total_late_minutes_month,
            "early_leave_minutes": total_early_leave_minutes,
            "work_days_in_month": work_days_count,
            "daily_hours": daily_hours,
            "is_ramadan_active": is_ramadan_active,
            "hours_until_deduction": max(0, 8 - deficit_hours),
            "days_to_deduct": round(deficit_hours / 8, 2) if deficit_hours >= 8 else 0
        },
        "early_leave_balance": {
            "monthly_allowance": monthly_early_leave_balance,
            "used_hours": used_early_leave_hours,
            "remaining_hours": remaining_early_leave_balance,
            "used_minutes": used_early_leave_minutes
        },
        "annual_leave": {
            "balance": round(pro_rata.get('available_balance', 0), 2),
            "policy_days": policy['days'],
            "policy_source_ar": policy['source_ar']
        },
        "leave_details": {
            "balance": round(pro_rata.get('available_balance', 0), 2),
            "entitlement": policy['days'],
            "earned_to_date": round(pro_rata.get('earned_to_date', 0), 2),
            "used": pro_rata.get('used_executed', 0)
        },
        "pending_transactions": pending_txs,
        "attendance_issues": {
            "late_count": late_count,
            "absent_count": absent_count,
            "total_late_minutes": total_late_minutes
        },
        "deductions": deductions_for_employee,
        "warnings": warnings_for_employee,
        "timestamp": format_datetime_riyadh(datetime.now(timezone.utc).isoformat())
    }
    
    # بيانات إضافية للإدارة فقط
    if viewer_is_admin:
        # المشرف
        supervisor = None
        if emp.get('supervisor_id'):
            supervisor = await db.employees.find_one(
                {"id": emp['supervisor_id']}, 
                {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1}
            )
        
        # الغياب غير المسوى
        unsettled_absences = await get_unsettled_absences(employee_id)
        
        # الخصومات الكاملة
        deductions = await db.finance_ledger.find({
            "employee_id": employee_id,
            "type": "debit",
            "settled": {"$ne": True}
        }, {"_id": 0}).to_list(100)
        total_deductions = sum(d.get('amount', 0) for d in deductions)
        
        # السلف النشطة
        loans = await db.finance_ledger.find({
            "employee_id": employee_id,
            "code": "LOAN",
            "settled": {"$ne": True}
        }, {"_id": 0}).to_list(100)
        total_loans = sum(loan.get('amount', 0) for loan in loans)
        
        # العهد النشطة
        custody = await db.custody_ledger.find({
            "employee_id": employee_id,
            "status": "active"
        }, {"_id": 0}).to_list(100)
        
        # المعاملات النشطة
        active_transactions = await get_employee_active_transactions(employee_id)
        
        employee_summary.update({
            "supervisor": supervisor,
            "attendance_details": {
                "summary_30_days": attendance_summary,
                "unsettled_absences": len(unsettled_absences),
                "unsettled_details": unsettled_absences[:5]
            },
            "finance": {
                "pending_deductions": total_deductions,
                "deductions_count": len(deductions),
                "pending_loans": total_loans,
                "loans_count": len(loans)
            },
            "custody": {
                "active_count": len(custody),
                "items": [c.get('item_name', '') for c in custody]
            },
            "active_transactions": {
                "count": len(active_transactions),
                "types": list(set(t.get('type', '') for t in active_transactions)),
                "ref_nos": [t.get('ref_no', '') for t in active_transactions]
            }
        })
    
    return employee_summary



# ==================== EMPLOYEE PHOTO MANAGEMENT ====================

UPLOAD_DIR = "uploads/photos"
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/{employee_id}/photo")
async def upload_employee_photo(
    employee_id: str,
    photo: UploadFile = File(...),
    user=Depends(require_roles('stas'))
):
    """
    رفع صورة الموظف - STAS فقط
    """
    # التحقق من وجود الموظف
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من نوع الملف
    if not photo.filename:
        raise HTTPException(status_code=400, detail="اسم الملف غير موجود")
    
    file_ext = os.path.splitext(photo.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # قراءة المحتوى والتحقق من الحجم
    content = await photo.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="حجم الصورة يجب أن يكون أقل من 5 ميجابايت")
    
    # إنشاء مجلد الرفع
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # حذف الصورة القديمة إن وجدت
    old_photo = emp.get('photo_filename')
    if old_photo:
        old_path = os.path.join(UPLOAD_DIR, old_photo)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    
    # إنشاء اسم ملف فريد
    filename = f"{employee_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # حفظ الملف
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # تحديث بيانات الموظف مع URL الصورة
    photo_url = f"/api/employees/{employee_id}/photo-file"
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "photo_filename": filename,
            "photo_url": photo_url,
            "photo_updated_at": datetime.now(timezone.utc).isoformat(),
            "photo_updated_by": user['user_id']
        }}
    )
    
    return {
        "message": "تم رفع الصورة بنجاح",
        "photo_url": photo_url
    }


@router.get("/{employee_id}/photo-file")
async def get_employee_photo_file(employee_id: str):
    """
    الحصول على ملف صورة الموظف
    """
    from fastapi.responses import FileResponse
    
    emp = await db.employees.find_one({"id": employee_id}, {"photo_filename": 1})
    if not emp or not emp.get('photo_filename'):
        raise HTTPException(status_code=404, detail="الصورة غير موجودة")
    
    filepath = os.path.join(UPLOAD_DIR, emp['photo_filename'])
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="ملف الصورة غير موجود")
    
    return FileResponse(filepath)


@router.delete("/{employee_id}/photo")
async def delete_employee_photo(
    employee_id: str,
    user=Depends(require_roles('stas'))
):
    """
    حذف صورة الموظف - STAS فقط
    """
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # حذف الملف
    old_photo = emp.get('photo_filename')
    if old_photo:
        old_path = os.path.join(UPLOAD_DIR, old_photo)
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    
    # تحديث بيانات الموظف
    await db.employees.update_one(
        {"id": employee_id},
        {"$unset": {
            "photo_filename": "",
            "photo_url": ""
        },
        "$set": {
            "photo_deleted_at": datetime.now(timezone.utc).isoformat(),
            "photo_deleted_by": user['user_id']
        }}
    )
    
    return {"message": "تم حذف الصورة بنجاح"}
