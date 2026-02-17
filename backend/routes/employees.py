from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone

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
    position: Optional[str] = None


class SupervisorAssignment(BaseModel):
    supervisor_id: Optional[str] = None


@router.get("")
async def list_employees(user=Depends(get_current_user)):
    role = user.get('role')
    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        return [emp] if emp else []
    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        reports = await db.employees.find(
            {"$or": [{"id": emp['id']}, {"supervisor_id": emp['id']}]}, {"_id": 0}
        ).to_list(100)
        return reports
    else:
        return await db.employees.find({}, {"_id": 0}).to_list(500)


@router.get("/{employee_id}")
async def get_employee(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    role = user.get('role')
    if role == 'employee':
        own = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not own or own['id'] != employee_id:
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول")
    return emp


@router.patch("/{employee_id}")
async def update_employee(employee_id: str, update: EmployeeUpdate, user=Depends(require_roles('stas'))):
    emp = await db.employees.find_one({"id": employee_id})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="لا توجد تحديثات")
    await db.employees.update_one({"id": employee_id}, {"$set": updates})
    if 'full_name' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name": updates['full_name']}})
    if 'full_name_ar' in updates:
        await db.users.update_one({"employee_id": employee_id}, {"$set": {"full_name_ar": updates['full_name_ar']}})
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


# ==================== DELETE EMPLOYEE ====================

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
    ملخص شامل للموظف - يعرض في صفحة الموظفين
    - العقد الحالي
    - المشرف
    - رصيد الإجازات
    - نسبة الاستهلاك
    - حالة الحضور
    - الغياب
    - الخصومات
    """
    role = user.get('role')
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
    
    # 2. معلومات الخدمة (من Service Layer)
    service_info = await get_employee_service_info(employee_id)
    
    # 3. ملخص الإجازات (من Service Layer)
    leave_summary = await get_employee_leave_summary(employee_id)
    
    # 4. ملخص الحضور (آخر 30 يوم)
    attendance_summary = await get_employee_attendance_summary(employee_id)
    
    # 5. الغياب غير المسوى
    unsettled_absences = await get_unsettled_absences(employee_id)
    
    # 6. المشرف
    supervisor = None
    if emp.get('supervisor_id'):
        supervisor = await db.employees.find_one(
            {"id": emp['supervisor_id']}, 
            {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1}
        )
    
    # 7. الخصومات (من finance_ledger)
    deductions = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit",
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    total_deductions = sum(d.get('amount', 0) for d in deductions)
    
    # 8. آخر حركة مالية
    last_finance = await db.finance_ledger.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("date", -1).limit(1).to_list(1)
    
    # 9. حالة حضور اليوم
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_attendance = await db.attendance_ledger.find_one({
        "employee_id": employee_id,
        "date": today,
        "type": "check_in"
    })
    
    return {
        "employee": emp,
        "contract": contract,
        "service_info": service_info,
        "supervisor": supervisor,
        "leave": {
            "balances": leave_summary.get('balances', {}),
            "annual": leave_summary.get('annual_leave', {}),
            "sick": leave_summary.get('sick_leave', {})
        },
        "attendance": {
            "summary_30_days": attendance_summary,
            "unsettled_absences": len(unsettled_absences),
            "today_status": "present" if today_attendance else "not_checked_in"
        },
        "finance": {
            "pending_deductions": total_deductions,
            "deductions_count": len(deductions),
            "last_activity": last_finance[0] if last_finance else None
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
