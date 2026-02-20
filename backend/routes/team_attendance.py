"""
Team Attendance Routes - الحضور والعقوبات

نظام صلاحيات التعديل:
─────────────────────────────────────
│ الدور     │ الصلاحيات                │
─────────────────────────────────────
│ المشرف    │ يطلب تعديل → ينتظر سلطان │
│ سلطان    │ موافقة/رفض → قرار نهائي  │
│ STAS     │ أرشيف سنوي للمراجعة      │
─────────────────────────────────────

سير العمل:
1. المشرف يطلب تعديل حالة موظف (مع تحذير المسؤولية)
2. الطلب يظهر لسلطان في قائمة "بانتظار الموافقة"
3. سلطان يوافق/يرفض/يعدل → قرار نهائي ونافذ
4. السجل يُحفظ في أرشيف STAS السنوي
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user, require_roles
import uuid

router = APIRouter(prefix="/api/team-attendance", tags=["Team Attendance"])


class StatusUpdateRequest(BaseModel):
    new_status: str  # PRESENT, ABSENT, ON_LEAVE, etc.
    reason: str
    check_in_time: Optional[str] = None  # HH:MM
    check_out_time: Optional[str] = None


class SupervisorCorrectionRequest(BaseModel):
    """طلب تعديل من المشرف"""
    new_status: str
    reason: str
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    supervisor_acknowledgment: bool = False  # إقرار المشرف بتحمل المسؤولية


class CorrectionDecisionRequest(BaseModel):
    """قرار سلطان على طلب التعديل"""
    action: str  # approve, reject, modify
    final_status: Optional[str] = None  # للتعديل
    decision_note: Optional[str] = None


@router.get("/summary")
async def get_team_summary(
    date: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    ملخص سريع لحضور الفريق
    يستثني: ستاس، محمد، صلاح، نايف (ليسوا موظفين)
    المشرف يرى فقط الموظفين المسؤولين عنهم
    """
    # الموظفون المستثنون من الحضور (ليسوا موظفين)
    EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-004', 'EMP-NAIF']
    
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # بناء فلتر الموظفين
    emp_filter = {
        "is_active": {"$ne": False},
        "id": {"$nin": EXEMPT_EMPLOYEE_IDS}
    }
    
    # إذا كان المستخدم مشرف، يرى فقط الموظفين التابعين له
    if user.get('role') == 'supervisor':
        emp_filter["supervisor_id"] = user.get('employee_id')
    
    # جلب الموظفين
    employees = await db.employees.find(
        emp_filter,
        {"_id": 0, "id": 1}
    ).to_list(500)
    
    emp_ids = [e['id'] for e in employees]
    total = len(emp_ids)
    
    # جلب السجلات اليومية
    statuses = await db.daily_status.find(
        {"employee_id": {"$in": emp_ids}, "date": target_date},
        {"_id": 0, "final_status": 1}
    ).to_list(500)
    
    # حساب الإحصائيات
    summary = {
        "date": target_date,
        "total": total,
        "present": 0,
        "absent": 0,
        "late": 0,
        "on_leave": 0,
        "weekend": 0,
        "holiday": 0,
        "not_processed": 0
    }
    
    processed_count = len(statuses)
    summary["not_processed"] = total - processed_count
    
    for s in statuses:
        status = s.get('final_status', '')
        if status in ['PRESENT', 'EARLY_LEAVE']:
            summary['present'] += 1
        elif status == 'ABSENT':
            summary['absent'] += 1
        elif status == 'LATE':
            summary['late'] += 1
            summary['present'] += 1  # المتأخر حاضر
        elif status in ['ON_LEAVE', 'ON_ADMIN_LEAVE']:
            summary['on_leave'] += 1
        elif status == 'WEEKEND':
            summary['weekend'] += 1
        elif status == 'HOLIDAY':
            summary['holiday'] += 1
    
    return summary


@router.get("/daily")
async def get_team_daily(
    date: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    جدول الحضور اليومي لجميع الموظفين
    يُظهر جميع الموظفين حتى لو لم يسجلوا بصمة
    يستثني: ستاس، محمد، صلاح، نايف (ليسوا موظفين)
    
    المشرف يرى فقط الموظفين المسؤولين عنهم
    """
    # الموظفون المستثنون من الحضور (ليسوا موظفين)
    EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-004', 'EMP-NAIF']
    
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # بناء فلتر الموظفين
    emp_filter = {
        "is_active": {"$ne": False},
        "id": {"$nin": EXEMPT_EMPLOYEE_IDS}
    }
    
    # إذا كان المستخدم مشرف، يرى فقط الموظفين التابعين له
    if user.get('role') == 'supervisor':
        emp_filter["supervisor_id"] = user.get('employee_id')
    
    # جلب الموظفين
    employees = await db.employees.find(
        emp_filter,
        {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1, "employee_number": 1, "department": 1, "job_title": 1, "job_title_ar": 1, "work_location_id": 1}
    ).to_list(500)
    
    emp_map = {e['id']: e for e in employees}
    emp_ids = list(emp_map.keys())
    
    # جلب مواقع العمل
    work_locations = await db.work_locations.find({}, {"_id": 0}).to_list(100)
    location_map = {loc.get('id', ''): loc for loc in work_locations}
    
    # جلب السجلات اليومية المحللة
    daily_statuses = await db.daily_status.find(
        {"employee_id": {"$in": emp_ids}, "date": target_date},
        {"_id": 0}
    ).to_list(500)
    
    status_map = {s['employee_id']: s for s in daily_statuses}
    
    # جلب البصمات
    attendance = await db.attendance_ledger.find(
        {"employee_id": {"$in": emp_ids}, "date": target_date},
        {"_id": 0}
    ).to_list(1000)
    
    # تجميع البصمات حسب الموظف
    attendance_map = {}
    for a in attendance:
        emp_id = a['employee_id']
        if emp_id not in attendance_map:
            attendance_map[emp_id] = {"check_in": None, "check_out": None}
        if a['type'] == 'check_in':
            attendance_map[emp_id]['check_in'] = a['timestamp']
        elif a['type'] == 'check_out':
            attendance_map[emp_id]['check_out'] = a['timestamp']
    
    # بناء النتيجة
    result = []
    for emp_id, emp in emp_map.items():
        status_data = status_map.get(emp_id, {})
        attend_data = attendance_map.get(emp_id, {})
        
        # جلب موقع العمل
        work_loc_id = emp.get('work_location_id', '')
        work_loc = location_map.get(work_loc_id, {})
        
        # تحديد الحالة
        final_status = status_data.get('final_status', 'NOT_PROCESSED')
        status_ar = status_data.get('status_ar', 'لم يُحلل')
        
        # إذا لم يُحلل بعد، نحدد حسب البصمة
        if final_status == 'NOT_PROCESSED':
            if attend_data.get('check_in'):
                final_status = 'PRESENT'
                status_ar = 'حاضر (غير مؤكد)'
            else:
                final_status = 'NOT_REGISTERED'
                status_ar = 'لم يُسجل'
        
        result.append({
            "employee_id": emp_id,
            "employee_name": emp.get('full_name', ''),
            "employee_name_ar": emp.get('full_name_ar', ''),
            "employee_number": emp.get('employee_number', ''),
            "department": emp.get('department', ''),
            "job_title": emp.get('job_title', ''),
            "job_title_ar": emp.get('job_title_ar', ''),
            "work_location_id": work_loc_id,
            "work_location_name": work_loc.get('name', 'Main Office'),
            "work_location_name_ar": work_loc.get('name_ar', 'المقر الرئيسي'),
            "date": target_date,
            "final_status": final_status,
            "status_ar": status_ar,
            "decision_reason_ar": status_data.get('decision_reason_ar', ''),
            "check_in_time": attend_data.get('check_in'),
            "check_out_time": attend_data.get('check_out'),
            "late_minutes": status_data.get('late_minutes', 0),
            "early_leave_minutes": status_data.get('early_leave_minutes', 0),
            "actual_hours": status_data.get('actual_hours', 0),
            "daily_status_id": status_data.get('id'),
            "can_edit": final_status not in ['WEEKEND', 'HOLIDAY'],
            "has_trace": 'trace_log' in status_data
        })
    
    # ترتيب حسب الحالة (الغائبون أولاً)
    status_order = {'ABSENT': 0, 'LATE': 1, 'NOT_REGISTERED': 2, 'UNKNOWN': 2, 'PRESENT': 3, 'ON_LEAVE': 4, 'WEEKEND': 5, 'HOLIDAY': 6}
    result.sort(key=lambda x: (status_order.get(x['final_status'], 99), x['employee_name_ar']))
    
    return result


@router.get("/weekly")
async def get_team_weekly(
    date: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    جدول الحضور الأسبوعي
    """
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    
    # حساب أيام الأسبوع (الأحد - الخميس)
    # في السعودية: الأحد = 0 (يوم العمل الأول)
    day_of_week = dt.weekday()  # Python: Monday=0, Sunday=6
    # نريد الأحد كأول يوم عمل
    # الأحد في Python = 6, نحسب الفرق
    if day_of_week == 6:  # الأحد
        days_from_sunday = 0
    else:
        days_from_sunday = day_of_week + 1
    
    week_start = dt - timedelta(days=days_from_sunday)
    week_end = week_start + timedelta(days=6)
    
    start_str = week_start.strftime("%Y-%m-%d")
    end_str = week_end.strftime("%Y-%m-%d")
    
    # جلب الموظفين
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "full_name_ar": 1, "employee_number": 1}
    ).to_list(500)
    
    emp_map = {e['id']: e for e in employees}
    emp_ids = list(emp_map.keys())
    
    # جلب السجلات اليومية للأسبوع
    statuses = await db.daily_status.find({
        "employee_id": {"$in": emp_ids},
        "date": {"$gte": start_str, "$lte": end_str}
    }, {"_id": 0}).to_list(5000)
    
    # تجميع حسب الموظف
    emp_weekly = {}
    for emp_id, emp in emp_map.items():
        emp_weekly[emp_id] = {
            "employee_id": emp_id,
            "employee_name_ar": emp.get('full_name_ar', ''),
            "employee_number": emp.get('employee_number', ''),
            "week_start": start_str,
            "week_end": end_str,
            "days": {},
            "total_present": 0,
            "total_absent": 0,
            "total_late": 0,
            "total_leave": 0,
            "total_late_minutes": 0
        }
    
    for s in statuses:
        emp_id = s['employee_id']
        date = s['date']
        status = s.get('final_status', 'UNKNOWN')
        
        if emp_id in emp_weekly:
            emp_weekly[emp_id]['days'][date] = {
                "status": status,
                "status_ar": s.get('status_ar', ''),
                "late_minutes": s.get('late_minutes', 0)
            }
            
            if status in ['PRESENT', 'EARLY_LEAVE']:
                emp_weekly[emp_id]['total_present'] += 1
            elif status == 'ABSENT':
                emp_weekly[emp_id]['total_absent'] += 1
            elif status == 'LATE':
                emp_weekly[emp_id]['total_late'] += 1
                emp_weekly[emp_id]['total_present'] += 1
                emp_weekly[emp_id]['total_late_minutes'] += s.get('late_minutes', 0)
            elif status in ['ON_LEAVE', 'ON_ADMIN_LEAVE']:
                emp_weekly[emp_id]['total_leave'] += 1
    
    return list(emp_weekly.values())


@router.get("/monthly")
async def get_team_monthly(
    month: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    ملخص الحضور الشهري
    """
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    month_start = f"{month}-01"
    dt = datetime.strptime(month_start, "%Y-%m-%d")
    if dt.month == 12:
        month_end = f"{dt.year + 1}-01-01"
    else:
        month_end = f"{dt.year}-{dt.month + 1:02d}-01"
    
    # جلب الموظفين
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "full_name_ar": 1, "employee_number": 1, "salary": 1}
    ).to_list(500)
    
    emp_map = {e['id']: e for e in employees}
    emp_ids = list(emp_map.keys())
    
    # جلب السجلات الشهرية
    statuses = await db.daily_status.find({
        "employee_id": {"$in": emp_ids},
        "date": {"$gte": month_start, "$lt": month_end}
    }, {"_id": 0}).to_list(10000)
    
    # تجميع حسب الموظف
    emp_monthly = {}
    for emp_id, emp in emp_map.items():
        salary = emp.get('salary', 0)
        emp_monthly[emp_id] = {
            "employee_id": emp_id,
            "employee_name_ar": emp.get('full_name_ar', ''),
            "employee_number": emp.get('employee_number', ''),
            "month": month,
            "salary": salary,
            "daily_wage": round(salary / 30, 2) if salary else 0,
            "total_present": 0,
            "total_absent": 0,
            "total_late": 0,
            "total_leave": 0,
            "total_late_minutes": 0,
            "total_early_leave_minutes": 0,
            "estimated_deduction": 0
        }
    
    for s in statuses:
        emp_id = s['employee_id']
        status = s.get('final_status', 'UNKNOWN')
        
        if emp_id in emp_monthly:
            if status in ['PRESENT', 'EARLY_LEAVE']:
                emp_monthly[emp_id]['total_present'] += 1
                emp_monthly[emp_id]['total_early_leave_minutes'] += s.get('early_leave_minutes', 0)
            elif status == 'ABSENT':
                emp_monthly[emp_id]['total_absent'] += 1
                # حساب الخصم المتوقع
                emp_monthly[emp_id]['estimated_deduction'] += emp_monthly[emp_id]['daily_wage']
            elif status == 'LATE':
                emp_monthly[emp_id]['total_late'] += 1
                emp_monthly[emp_id]['total_present'] += 1
                emp_monthly[emp_id]['total_late_minutes'] += s.get('late_minutes', 0)
            elif status in ['ON_LEAVE', 'ON_ADMIN_LEAVE']:
                emp_monthly[emp_id]['total_leave'] += 1
    
    # ترتيب حسب الغياب
    result = sorted(emp_monthly.values(), key=lambda x: (-x['total_absent'], -x['total_late']))
    return result


@router.post("/{employee_id}/update-status")
async def update_employee_status(
    employee_id: str,
    date: str,
    body: StatusUpdateRequest,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    تعديل حالة الموظف - سلطان/نايف/STAS فقط (قرار نهائي ونافذ)
    
    ⚠️ المشرف يستخدم /request-correction للطلب ثم ينتظر موافقة سلطان
    
    مثال: تحويل موظف من غائب إلى حاضر مع تسجيل السبب
    """
    # التحقق من الموظف
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # جلب السجل اليومي
    daily = await db.daily_status.find_one({
        "employee_id": employee_id,
        "date": date
    }, {"_id": 0})
    
    if not daily:
        # إنشاء سجل جديد
        from services.day_resolver_v2 import resolve_and_save_v2
        daily = await resolve_and_save_v2(employee_id, date)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث الحالة
    status_ar_map = {
        'PRESENT': 'حاضر',
        'ABSENT': 'غائب',
        'LATE': 'متأخر',
        'ON_LEAVE': 'إجازة',
        'EXCUSED': 'معذور',
        'ON_MISSION': 'مهمة خارجية'
    }
    
    correction = {
        "from_status": daily.get('final_status'),
        "to_status": body.new_status,
        "reason": body.reason,
        "corrected_by": user['user_id'],
        "corrected_by_name": user.get('full_name', user['user_id']),
        "corrected_at": now,
        "check_in_time": body.check_in_time,
        "check_out_time": body.check_out_time
    }
    
    await db.daily_status.update_one(
        {"employee_id": employee_id, "date": date},
        {
            "$set": {
                "final_status": body.new_status,
                "status_ar": status_ar_map.get(body.new_status, body.new_status),
                "decision_reason_ar": f"تم التعديل بواسطة {user.get('full_name', user['user_id'])}: {body.reason}",
                "decision_source": "manual_correction",
                "check_in_time": body.check_in_time or daily.get('check_in_time'),
                "check_out_time": body.check_out_time or daily.get('check_out_time'),
                "updated_at": now,
                "updated_by": user['user_id']
            },
            "$push": {
                "corrections": correction
            }
        },
        upsert=True
    )
    
    # إرسال إشعار للموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        await create_notification(
            recipient_id=employee_id,
            notification_type=NotificationType.INFO,
            title="Attendance Status Updated",
            title_ar="تحديث حالة الحضور",
            message=f"Your attendance status for {date} has been updated",
            message_ar=f"تم تعديل حالتك ليوم {date} إلى: {status_ar_map.get(body.new_status, body.new_status)}",
            priority=NotificationPriority.NORMAL,
            recipient_role="employee",
            reference_type="daily_status",
            reference_url="/attendance"
        )
    except Exception as e:
        # Don't fail if notification fails
        pass
    
    return {
        "success": True,
        "message": f"تم تعديل حالة {emp.get('full_name_ar', '')} إلى {status_ar_map.get(body.new_status, body.new_status)}",
        "correction": correction
    }


@router.get("/{employee_id}/trace/{date}")
async def get_employee_trace(
    employee_id: str,
    date: str,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    عرض العروق (Trace Evidence) لقرار الحضور
    """
    daily = await db.daily_status.find_one({
        "employee_id": employee_id,
        "date": date
    }, {"_id": 0})
    
    if not daily:
        # محاولة التحليل الآن
        from services.day_resolver_v2 import resolve_day_v2
        daily = await resolve_day_v2(employee_id, date)
    
    return daily



@router.get("/employee/{employee_id}")
async def get_employee_attendance(
    employee_id: str,
    period: str = Query(default="daily", description="daily, weekly, monthly, yearly"),
    date: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    الحصول على سجل حضور موظف محدد
    """
    from datetime import datetime, timedelta
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    if not month:
        month = datetime.now().strftime("%Y-%m")
    if not year:
        year = str(datetime.now().year)
    
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    result = {
        "employee_id": employee_id,
        "employee_name": emp.get("full_name", ""),
        "employee_name_ar": emp.get("full_name_ar", ""),
        "employee_number": emp.get("employee_number", ""),
        "period": period
    }
    
    if period == "daily":
        # Get daily records for selected date and surrounding days
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_date = (date_obj - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = date
        
        daily_records = await db.daily_status.find({
            "employee_id": employee_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }, {"_id": 0}).sort("date", -1).to_list(100)
        
        # Add can_edit flag
        for rec in daily_records:
            rec["can_edit"] = True
            rec["has_trace"] = True
        
        result["daily"] = daily_records
        
    elif period == "weekly":
        # Get weekly summary
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        week_start = (date_obj - timedelta(days=date_obj.weekday())).strftime("%Y-%m-%d")
        week_end = date
        
        daily_records = await db.daily_status.find({
            "employee_id": employee_id,
            "date": {"$gte": week_start, "$lte": week_end}
        }, {"_id": 0}).to_list(100)
        
        summary = {
            "employee_id": employee_id,
            "employee_name": emp.get("full_name", ""),
            "employee_name_ar": emp.get("full_name_ar", ""),
            "employee_number": emp.get("employee_number", ""),
            "total_present": sum(1 for r in daily_records if r.get("final_status") in ["PRESENT", "LATE", "EARLY_LEAVE"]),
            "total_absent": sum(1 for r in daily_records if r.get("final_status") == "ABSENT"),
            "total_late": sum(1 for r in daily_records if r.get("final_status") in ["LATE", "LATE_EXCUSED"]),
            "total_leave": sum(1 for r in daily_records if r.get("final_status") in ["ON_LEAVE", "ON_ADMIN_LEAVE"]),
            "total_late_minutes": sum(r.get("late_minutes", 0) for r in daily_records),
            "total_early_leave_minutes": sum(r.get("early_leave_minutes", 0) for r in daily_records)
        }
        result["weekly"] = summary
        result["daily"] = daily_records
        
    elif period == "monthly":
        # Get monthly summary
        month_start = f"{month}-01"
        # Calculate month end
        year_val, month_val = map(int, month.split("-"))
        if month_val == 12:
            month_end = f"{year_val + 1}-01-01"
        else:
            month_end = f"{year_val}-{month_val + 1:02d}-01"
        
        daily_records = await db.daily_status.find({
            "employee_id": employee_id,
            "date": {"$gte": month_start, "$lt": month_end}
        }, {"_id": 0}).sort("date", -1).to_list(100)
        
        total_absent = sum(1 for r in daily_records if r.get("final_status") == "ABSENT")
        total_late_minutes = sum(r.get("late_minutes", 0) for r in daily_records)
        total_early_leave_minutes = sum(r.get("early_leave_minutes", 0) for r in daily_records)
        
        # Calculate estimated deduction
        # Days deduction for absences
        absent_deduction = total_absent  # يوم لكل غياب
        # Minutes deduction (8 hours = 480 minutes = 1 day)
        total_deficit_minutes = total_late_minutes + total_early_leave_minutes
        deficit_days = total_deficit_minutes / 480  # كل 8 ساعات = يوم
        
        summary = {
            "employee_id": employee_id,
            "employee_name": emp.get("full_name", ""),
            "employee_name_ar": emp.get("full_name_ar", ""),
            "employee_number": emp.get("employee_number", ""),
            "total_present": sum(1 for r in daily_records if r.get("final_status") in ["PRESENT", "LATE", "EARLY_LEAVE"]),
            "total_absent": total_absent,
            "total_late": sum(1 for r in daily_records if r.get("final_status") in ["LATE", "LATE_EXCUSED"]),
            "total_leave": sum(1 for r in daily_records if r.get("final_status") in ["ON_LEAVE", "ON_ADMIN_LEAVE"]),
            "total_late_minutes": total_late_minutes,
            "total_early_leave_minutes": total_early_leave_minutes,
            "total_deficit_minutes": total_deficit_minutes,
            "deficit_days": round(deficit_days, 2),
            "estimated_deduction": 0  # Will be calculated based on salary
        }
        result["monthly"] = summary
        result["daily"] = daily_records
    
    return result



# ==================== نظام طلبات التعديل ====================

@router.post("/{employee_id}/request-correction/{date}")
async def supervisor_request_correction(
    employee_id: str,
    date: str,
    body: SupervisorCorrectionRequest,
    user=Depends(require_roles('supervisor'))
):
    """
    طلب تعديل من المشرف - يحتاج موافقة سلطان
    
    المشرف يطلب تعديل حالة موظف تحت إشرافه.
    الطلب يظهر لسلطان للموافقة/الرفض.
    """
    # التحقق من إقرار المشرف
    if not body.supervisor_acknowledgment:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "ACKNOWLEDGMENT_REQUIRED",
                "message_ar": f"عزيزي {user.get('full_name_ar', user.get('full_name', 'المشرف'))}، تعديلك للحالة يعني تحملك لمسؤوليتها. يرجى تأكيد الإقرار.",
                "message_en": f"Dear {user.get('full_name', 'Supervisor')}, modifying this status means you take responsibility for it. Please confirm acknowledgment."
            }
        )
    
    # التحقق من أن الموظف تحت إشراف هذا المشرف
    emp = await db.employees.find_one({
        "id": employee_id,
        "supervisor_id": user.get('employee_id')
    }, {"_id": 0})
    
    if not emp:
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "NOT_YOUR_EMPLOYEE",
                "message_ar": "هذا الموظف ليس تحت إشرافك",
                "message_en": "This employee is not under your supervision"
            }
        )
    
    # جلب السجل الحالي
    daily = await db.daily_status.find_one({
        "employee_id": employee_id,
        "date": date
    }, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إنشاء طلب التعديل
    correction_request = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name_ar": emp.get('full_name_ar', ''),
        "date": date,
        "original_status": daily.get('final_status', 'UNKNOWN') if daily else 'UNKNOWN',
        "requested_status": body.new_status,
        "reason": body.reason,
        "check_in_time": body.check_in_time,
        "check_out_time": body.check_out_time,
        "supervisor_id": user.get('employee_id'),
        "supervisor_name_ar": user.get('full_name_ar', user.get('full_name', '')),
        "supervisor_user_id": user['user_id'],
        "status": "pending",  # pending, approved, rejected, modified
        "created_at": now,
        "decision": None,
        "decided_by": None,
        "decided_at": None,
        "decision_note": None,
        "final_status": None  # الحالة النهائية بعد قرار سلطان
    }
    
    await db.attendance_corrections.insert_one(correction_request)
    
    # إرسال إشعار لسلطان
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        await create_notification(
            recipient_id="",
            notification_type=NotificationType.ACTION_REQUIRED,
            title="Attendance Correction Request",
            title_ar="طلب تعديل حضور",
            message=f"Supervisor {user.get('full_name', '')} requested correction for {emp.get('full_name_ar', '')}",
            message_ar=f"المشرف {user.get('full_name_ar', '')} يطلب تعديل حالة {emp.get('full_name_ar', '')} ليوم {date}",
            priority=NotificationPriority.HIGH,
            recipient_role="sultan",
            reference_type="attendance_correction",
            reference_id=correction_request['id'],
            reference_url="/team-attendance?tab=pending"
        )
    except:
        pass
    
    return {
        "success": True,
        "message_ar": "تم إرسال طلب التعديل لسلطان للموافقة",
        "message_en": "Correction request sent to Sultan for approval",
        "request_id": correction_request['id']
    }


@router.get("/pending-corrections")
async def get_pending_corrections(
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    طلبات التعديل المعلقة - لسلطان
    
    يعرض جميع طلبات التعديل من المشرفين بانتظار الموافقة
    """
    corrections = await db.attendance_corrections.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return corrections


@router.post("/correction/{correction_id}/decide")
async def decide_correction(
    correction_id: str,
    body: CorrectionDecisionRequest,
    user=Depends(require_roles('sultan'))
):
    """
    قرار سلطان على طلب التعديل - نهائي ونافذ
    
    الإجراءات:
    - approve: موافقة على الحالة المطلوبة
    - reject: رفض التعديل
    - modify: موافقة مع تعديل الحالة
    """
    if body.action not in ['approve', 'reject', 'modify']:
        raise HTTPException(status_code=400, detail="الإجراء غير صحيح")
    
    correction = await db.attendance_corrections.find_one(
        {"id": correction_id},
        {"_id": 0}
    )
    
    if not correction:
        raise HTTPException(status_code=404, detail="طلب التعديل غير موجود")
    
    if correction['status'] != 'pending':
        raise HTTPException(status_code=400, detail="تم اتخاذ قرار على هذا الطلب مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديد الحالة النهائية
    if body.action == 'approve':
        final_status = correction['requested_status']
        decision_status = 'approved'
    elif body.action == 'reject':
        final_status = correction['original_status']
        decision_status = 'rejected'
    else:  # modify
        if not body.final_status:
            raise HTTPException(status_code=400, detail="يجب تحديد الحالة النهائية عند التعديل")
        final_status = body.final_status
        decision_status = 'modified'
    
    status_ar_map = {
        'PRESENT': 'حاضر',
        'ABSENT': 'غائب',
        'LATE': 'متأخر',
        'ON_LEAVE': 'إجازة',
        'EXCUSED': 'معذور',
        'ON_MISSION': 'مهمة خارجية'
    }
    
    # تحديث طلب التعديل
    await db.attendance_corrections.update_one(
        {"id": correction_id},
        {"$set": {
            "status": decision_status,
            "decision": body.action,
            "decided_by": user['user_id'],
            "decided_by_name": user.get('full_name_ar', user.get('full_name', '')),
            "decided_at": now,
            "decision_note": body.decision_note,
            "final_status": final_status
        }}
    )
    
    # إذا تمت الموافقة أو التعديل، نطبق التغيير على daily_status
    if body.action in ['approve', 'modify']:
        await db.daily_status.update_one(
            {"employee_id": correction['employee_id'], "date": correction['date']},
            {
                "$set": {
                    "final_status": final_status,
                    "status_ar": status_ar_map.get(final_status, final_status),
                    "decision_reason_ar": f"قرار سلطان: {body.decision_note or 'موافقة على طلب المشرف'}",
                    "decision_source": "sultan_decision",
                    "check_in_time": correction.get('check_in_time'),
                    "check_out_time": correction.get('check_out_time'),
                    "updated_at": now,
                    "updated_by": user['user_id']
                },
                "$push": {
                    "corrections": {
                        "from_status": correction['original_status'],
                        "to_status": final_status,
                        "reason": f"قرار سلطان على طلب المشرف {correction['supervisor_name_ar']}: {body.decision_note or ''}",
                        "requested_by": correction['supervisor_user_id'],
                        "requested_by_name": correction['supervisor_name_ar'],
                        "corrected_by": user['user_id'],
                        "corrected_by_name": user.get('full_name_ar', ''),
                        "corrected_at": now
                    }
                }
            },
            upsert=True
        )
    
    # حفظ في أرشيف STAS السنوي
    year = correction['date'][:4]
    archive_entry = {
        "id": str(uuid.uuid4()),
        "year": year,
        "type": "attendance_correction",
        "correction_id": correction_id,
        "employee_id": correction['employee_id'],
        "employee_name_ar": correction['employee_name_ar'],
        "date": correction['date'],
        "original_status": correction['original_status'],
        "requested_status": correction['requested_status'],
        "final_status": final_status,
        "supervisor_id": correction['supervisor_id'],
        "supervisor_name_ar": correction['supervisor_name_ar'],
        "decision": body.action,
        "decision_note": body.decision_note,
        "decided_by": user['user_id'],
        "decided_by_name": user.get('full_name_ar', ''),
        "decided_at": now,
        "archived_at": now
    }
    await db.stas_annual_archive.insert_one(archive_entry)
    
    # إرسال إشعار للمشرف بالقرار
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        decision_text_ar = {
            'approve': 'تمت الموافقة',
            'reject': 'تم الرفض',
            'modify': 'تم التعديل'
        }
        
        await create_notification(
            recipient_id=correction['supervisor_id'],
            notification_type=NotificationType.INFO,
            title="Correction Decision",
            title_ar="قرار طلب التعديل",
            message=f"Sultan decided on your correction request: {body.action}",
            message_ar=f"{decision_text_ar.get(body.action, body.action)} على طلب تعديل حالة {correction['employee_name_ar']}",
            priority=NotificationPriority.NORMAL,
            recipient_role="supervisor",
            reference_type="attendance_correction",
            reference_id=correction_id
        )
        
        # إشعار للموظف أيضاً
        await create_notification(
            recipient_id=correction['employee_id'],
            notification_type=NotificationType.INFO,
            title="Attendance Status Updated",
            title_ar="تحديث حالة الحضور",
            message=f"Your attendance for {correction['date']} has been updated",
            message_ar=f"تم تعديل حالتك ليوم {correction['date']} إلى: {status_ar_map.get(final_status, final_status)}",
            priority=NotificationPriority.NORMAL,
            recipient_role="employee"
        )
    except:
        pass
    
    return {
        "success": True,
        "message_ar": f"تم {decision_text_ar.get(body.action, body.action)} طلب التعديل",
        "decision": body.action,
        "final_status": final_status,
        "archived": True
    }


@router.get("/stas-archive")
async def get_stas_archive(
    year: Optional[str] = None,
    type: Optional[str] = None,
    user=Depends(require_roles('stas'))
):
    """
    أرشيف STAS السنوي - للمراجعة
    
    يعرض جميع القرارات والتعديلات المحفوظة
    """
    if not year:
        year = str(datetime.now(timezone.utc).year)
    
    query = {"year": year}
    if type:
        query["type"] = type
    
    archive = await db.stas_annual_archive.find(
        query,
        {"_id": 0}
    ).sort("archived_at", -1).to_list(500)
    
    # إحصائيات
    stats = {
        "year": year,
        "total_entries": len(archive),
        "corrections_approved": sum(1 for a in archive if a.get('decision') == 'approve'),
        "corrections_rejected": sum(1 for a in archive if a.get('decision') == 'reject'),
        "corrections_modified": sum(1 for a in archive if a.get('decision') == 'modify')
    }
    
    return {
        "stats": stats,
        "entries": archive
    }


@router.get("/corrections-history/{employee_id}")
async def get_employee_corrections_history(
    employee_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    سجل تعديلات موظف معين
    """
    corrections = await db.attendance_corrections.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return corrections
