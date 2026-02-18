"""
Monthly Hours Service - خدمة حساب الساعات الشهرية

المعادلات:
required_hours = عدد أيام العمل × ساعات اليوم
actual_hours = مجموع ساعات الحضور الفعلية
permission_hours = ساعات الاستئذان المنفذة
late_minutes = دقائق التأخير
early_leave_minutes = دقائق الخروج المبكر
compensation_hours = ساعات البقاء الإضافي
net_hours = actual_hours + compensation_hours - required_hours

سياسة التعويض:
- كل ساعة بقاء إضافي = تعويض ساعة ناقصة
- لا يتم الخصم طالما net_hours >= 0
- ينتهي التعويض بنهاية الشهر فقط
- كل 8 ساعات نقص = يوم غياب
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from database import db
from models.daily_status import DailyStatusEnum


async def calculate_monthly_hours(employee_id: str, month: str) -> dict:
    """
    حساب الساعات الشهرية لموظف
    month: YYYY-MM
    """
    # جلب جميع السجلات اليومية للشهر
    daily_records = await db.daily_status.find({
        "employee_id": employee_id,
        "date": {"$regex": f"^{month}"}
    }, {"_id": 0}).to_list(100)
    
    # جلب بيانات الموظف
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    # جلب موقع العمل للحصول على ساعات العمل اليومية
    work_location = None
    if employee:
        loc_id = employee.get('work_location_id')
        if loc_id:
            work_location = await db.work_locations.find_one({"id": loc_id}, {"_id": 0})
    
    daily_hours = 8.0  # الافتراضي
    if work_location:
        daily_hours = work_location.get('daily_hours', 8.0)
    
    # حساب المجاميع
    working_days = 0
    present_days = 0
    absent_days = 0
    leave_days = 0
    holiday_days = 0
    mission_days = 0
    weekend_days = 0
    
    total_actual_hours = 0.0
    total_permission_hours = 0.0
    total_late_minutes = 0
    total_early_leave_minutes = 0
    
    daily_details = []
    
    for record in daily_records:
        status = record.get('final_status')
        
        detail = {
            "date": record.get('date'),
            "status": status,
            "status_ar": record.get('status_ar'),
            "actual_hours": record.get('actual_hours', 0),
            "late_minutes": record.get('late_minutes', 0),
            "early_leave_minutes": record.get('early_leave_minutes', 0),
            "permission_hours": record.get('permission_hours', 0)
        }
        daily_details.append(detail)
        
        if status in [DailyStatusEnum.HOLIDAY.value, DailyStatusEnum.WEEKEND.value]:
            if status == DailyStatusEnum.HOLIDAY.value:
                holiday_days += 1
            else:
                weekend_days += 1
            continue
        
        # يوم عمل
        working_days += 1
        
        if status == DailyStatusEnum.ABSENT.value:
            absent_days += 1
        elif status in [DailyStatusEnum.ON_LEAVE.value, DailyStatusEnum.ON_ADMIN_LEAVE.value]:
            leave_days += 1
        elif status == DailyStatusEnum.ON_MISSION.value:
            mission_days += 1
        else:
            # حضور (كامل أو جزئي)
            present_days += 1
            actual = record.get('actual_hours') or 0
            total_actual_hours += actual
            total_permission_hours += record.get('permission_hours', 0)
            total_late_minutes += record.get('late_minutes', 0)
            total_early_leave_minutes += record.get('early_leave_minutes', 0)
    
    # حساب الساعات المطلوبة
    required_hours = working_days * daily_hours
    
    # حساب ساعات التعويض (البقاء الإضافي)
    compensation_hours = 0.0
    for record in daily_records:
        actual = record.get('actual_hours') or 0
        required = record.get('required_hours') or daily_hours
        if actual > required:
            compensation_hours += (actual - required)
    
    # الحساب النهائي
    net_hours = total_actual_hours + compensation_hours - required_hours
    
    # حساب النقص والأيام
    deficit_hours = max(0, -net_hours)
    deficit_days = deficit_hours / 8.0 if deficit_hours > 0 else 0
    
    now = datetime.now(timezone.utc).isoformat()
    
    result = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "month": month,
        
        "required_hours": round(required_hours, 2),
        "actual_hours": round(total_actual_hours, 2),
        "permission_hours": round(total_permission_hours, 2),
        "late_minutes": total_late_minutes,
        "early_leave_minutes": total_early_leave_minutes,
        "compensation_hours": round(compensation_hours, 2),
        "net_hours": round(net_hours, 2),
        "deficit_hours": round(deficit_hours, 2),
        "deficit_days": round(deficit_days, 2),
        
        "working_days": working_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "leave_days": leave_days,
        "holiday_days": holiday_days,
        "mission_days": mission_days,
        
        "is_finalized": False,
        "created_at": now,
        "daily_details": daily_details
    }
    
    return result


async def calculate_and_save(employee_id: str, month: str) -> dict:
    """حساب وحفظ الساعات الشهرية"""
    result = await calculate_monthly_hours(employee_id, month)
    
    # حذف السجل القديم إن وجد
    await db.monthly_hours.delete_one({
        "employee_id": employee_id,
        "month": month
    })
    
    # حفظ السجل الجديد
    await db.monthly_hours.insert_one(result)
    result.pop('_id', None)
    
    return result


async def finalize_month(employee_id: str, month: str, user_id: str) -> dict:
    """إغلاق الشهر وإنشاء مقترحات الخصم إن وجدت"""
    from services.deduction_service import create_monthly_deduction_proposal
    
    # حساب الساعات
    monthly = await calculate_and_save(employee_id, month)
    
    # إغلاق الشهر
    now = datetime.now(timezone.utc).isoformat()
    await db.monthly_hours.update_one(
        {"employee_id": employee_id, "month": month},
        {"$set": {
            "is_finalized": True,
            "finalized_at": now,
            "finalized_by": user_id
        }}
    )
    
    # إنشاء مقترح خصم إذا كان هناك نقص
    if monthly['deficit_hours'] > 0:
        await create_monthly_deduction_proposal(employee_id, month, monthly)
    
    monthly['is_finalized'] = True
    monthly['finalized_at'] = now
    monthly['finalized_by'] = user_id
    
    return monthly


async def get_team_monthly_summary(month: str, supervisor_id: Optional[str] = None) -> List[dict]:
    """ملخص الساعات الشهرية للفريق"""
    query = {"month": month}
    
    records = await db.monthly_hours.find(query, {"_id": 0}).to_list(500)
    
    summaries = []
    for r in records:
        emp = await db.employees.find_one({"id": r['employee_id']}, {"_id": 0, "full_name": 1, "full_name_ar": 1})
        
        # تحديد الحالة
        if r['net_hours'] >= 0:
            status = "ok"
        elif r['deficit_days'] < 1:
            status = "warning"
        else:
            status = "critical"
        
        summaries.append({
            "employee_id": r['employee_id'],
            "employee_name": emp.get('full_name_ar', emp.get('full_name', '')) if emp else '',
            "month": month,
            "required_hours": r['required_hours'],
            "actual_hours": r['actual_hours'],
            "net_hours": r['net_hours'],
            "deficit_days": r['deficit_days'],
            "status": status
        })
    
    return summaries
