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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user, require_roles
import uuid
import io
import qrcode
import base64
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

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
    يستثني: ستاس، محمد، صلاح، نايف (أدوار إدارية فقط - ليسوا موظفين)
    المشرف يرى فقط الموظفين المسؤولين عنهم
    """
    # الموظفون المستثنون من الحضور (أدوار إدارية فقط)
    EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF', 'EMP-004']
    
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
    يستثني: ستاس، محمد، صلاح، نايف (أدوار إدارية فقط)
    
    المشرف يرى فقط الموظفين المسؤولين عنهم
    """
    # الموظفون المستثنون من الحضور (أدوار إدارية فقط)
    EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF', 'EMP-004']
    
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
    
    # جلب الإجازات النشطة لجميع الموظفين في هذا التاريخ
    active_leaves = await db.transactions.find({
        "$or": [
            {"employee_id": {"$in": emp_ids}},
            {"data.employee_id": {"$in": emp_ids}}
        ],
        "type": {"$regex": "leave", "$options": "i"},
        "status": "executed",
        "data.start_date": {"$lte": target_date},
        "data.end_date": {"$gte": target_date}
    }, {"_id": 0, "employee_id": 1, "data.employee_id": 1, "type": 1}).to_list(500)
    
    leave_map = {}
    for l in active_leaves:
        emp_id = l.get('employee_id') or l.get('data', {}).get('employee_id')
        if emp_id:
            leave_map[emp_id] = l.get('type', 'leave')
    
    # جلب المهمات النشطة
    active_missions = await db.transactions.find({
        "$or": [
            {"employee_id": {"$in": emp_ids}},
            {"data.employee_id": {"$in": emp_ids}}
        ],
        "type": {"$regex": "mission|assignment", "$options": "i"},
        "status": "executed",
        "data.start_date": {"$lte": target_date},
        "data.end_date": {"$gte": target_date}
    }, {"_id": 0, "employee_id": 1, "data.employee_id": 1}).to_list(500)
    
    mission_map = {}
    for m in active_missions:
        emp_id = m.get('employee_id') or m.get('data', {}).get('employee_id')
        if emp_id:
            mission_map[emp_id] = True
    
    # التحقق من العطلة الرسمية
    holiday_today = await db.holidays.find_one({
        "date": target_date,
        "is_active": {"$ne": False}
    }, {"_id": 0})
    
    # التحقق من عطلة نهاية الأسبوع
    from datetime import datetime as dt
    day_of_week = dt.strptime(target_date, "%Y-%m-%d").weekday()
    is_weekend = day_of_week == 4  # Friday
    
    # بناء النتيجة
    result = []
    for emp_id, emp in emp_map.items():
        status_data = status_map.get(emp_id, {})
        attend_data = attendance_map.get(emp_id, {})
        
        # جلب موقع العمل
        work_loc_id = emp.get('work_location_id', '')
        work_loc = location_map.get(work_loc_id, {})
        
        # تحديد الحالة بالترتيب الصحيح
        final_status = 'NOT_REGISTERED'
        status_ar = 'لم يُسجل'
        decision_reason = status_data.get('decision_reason_ar', '')
        
        # 1. التحقق من الإجازة المعتمدة أولاً
        if emp_id in leave_map:
            leave_type = leave_map[emp_id]
            final_status = 'ON_LEAVE'
            if 'admin' in leave_type.lower():
                status_ar = 'إجازة إدارية'
            elif 'sick' in leave_type.lower():
                status_ar = 'إجازة مرضية'
            elif 'emergency' in leave_type.lower():
                status_ar = 'إجازة طارئة'
            else:
                status_ar = 'إجازة'
        
        # 2. التحقق من المهمة
        elif emp_id in mission_map:
            final_status = 'ON_MISSION'
            status_ar = 'في مهمة'
        
        # 3. التحقق من العطلة الرسمية
        elif holiday_today:
            final_status = 'HOLIDAY'
            status_ar = 'عطلة رسمية'
        
        # 4. التحقق من عطلة نهاية الأسبوع
        elif is_weekend:
            final_status = 'WEEKEND'
            status_ar = 'عطلة أسبوعية'
        
        # 5. التحقق من daily_status
        elif status_data:
            final_status = status_data.get('final_status', 'NOT_PROCESSED')
            status_ar = status_data.get('status_ar', 'لم يُحلل')
            decision_reason = status_data.get('decision_reason_ar', '')
            
            # إذا لم يُحلل بعد
            if final_status == 'NOT_PROCESSED':
                if attend_data.get('check_in'):
                    final_status = 'PRESENT'
                    status_ar = 'حاضر (غير مؤكد)'
                else:
                    final_status = 'NOT_REGISTERED'
                    status_ar = 'لم يُسجل'
        
        # 6. التحقق من البصمة فقط
        elif attend_data.get('check_in'):
            final_status = 'PRESENT'
            status_ar = 'حاضر'
        
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
            "decision_reason_ar": decision_reason,
            "check_in_time": attend_data.get('check_in'),
            "check_out_time": attend_data.get('check_out'),
            "late_minutes": status_data.get('late_minutes', 0) if status_data else 0,
            "early_leave_minutes": status_data.get('early_leave_minutes', 0) if status_data else 0,
            "actual_hours": status_data.get('actual_hours', 0) if status_data else 0,
            "daily_status_id": status_data.get('id') if status_data else None,
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
        'ON_MISSION': 'مهمة خارجية',
        'PERMISSION': 'استئذان',
        'GIFT_LEAVE': 'إجازة مكافأة',
        'EXEMPTED': 'إعفاء'
    }
    
    # معالجة خاصة لإجازة المكافأة والإعفاء
    is_gift_leave = body.new_status == 'GIFT_LEAVE'
    is_exemption = body.new_status == 'EXEMPTED'
    final_status_to_save = 'ON_ADMIN_LEAVE' if is_gift_leave else body.new_status
    
    correction = {
        "from_status": daily.get('final_status') if daily else 'UNKNOWN',
        "to_status": body.new_status,
        "reason": body.reason,
        "corrected_by": user['user_id'],
        "corrected_by_name": user.get('full_name', user['user_id']),
        "corrected_at": now,
        "check_in_time": body.check_in_time,
        "check_out_time": body.check_out_time,
        "is_gift_leave": is_gift_leave,
        "is_exemption": is_exemption
    }
    
    # تحديد السبب المعروض
    reason_text = body.reason
    if is_gift_leave:
        reason_text = f"⭐ إجازة مكافأة من {user.get('full_name', '')}: {body.reason}"
    elif is_exemption:
        reason_text = f"✓ إعفاء إداري من {user.get('full_name', '')}: {body.reason}"
    else:
        reason_text = f"تعديل إداري: {body.reason}"
    
    # === حساب ساعات العمل بناءً على الحالة ===
    # الحالات التي تُحتسب لها ساعات عمل كاملة
    counted_statuses = ['PRESENT', 'LATE', 'ON_MISSION', 'PERMISSION']
    # الحالات التي لا تُحتسب لها ساعات
    non_counted_statuses = ['ABSENT', 'EXEMPTED', 'ON_LEAVE', 'ON_ADMIN_LEAVE', 'GIFT_LEAVE', 'NOT_REGISTERED', 'EXCUSED']
    
    # جلب ساعات الدوام اليومية
    daily_hours = 8.0  # افتراضي
    
    # التحقق من رمضان
    ramadan_settings = await db.settings.find_one({"type": "ramadan_mode"}, {"_id": 0})
    is_ramadan = False
    if ramadan_settings:
        is_active = ramadan_settings.get('is_active', False)
        start_date = ramadan_settings.get('start_date', '')
        end_date = ramadan_settings.get('end_date', '')
        if is_active and start_date and end_date:
            if start_date <= date <= end_date:
                is_ramadan = True
                daily_hours = 6.0
    
    # جلب ساعات من موقع العمل إن وجد
    if emp.get('work_location_id'):
        work_loc = await db.work_locations.find_one({"id": emp['work_location_id']}, {"_id": 0})
        if work_loc:
            if is_ramadan:
                daily_hours = work_loc.get('ramadan_daily_hours', 6.0)
            else:
                daily_hours = work_loc.get('daily_hours', 8.0)
    
    # تحديد الساعات المحتسبة
    actual_hours = daily_hours if body.new_status in counted_statuses else 0.0
    
    # === تحديد أوقات الدخول والخروج ===
    # إذا كانت الحالة "حاضر" أو "متأخر"، نضع أوقات الدوام الرسمية
    work_start = "08:00"
    work_end = "16:00"
    
    # جلب أوقات العمل من الموقع
    if emp.get('work_location_id'):
        work_loc = await db.work_locations.find_one({"id": emp['work_location_id']}, {"_id": 0})
        if work_loc:
            if is_ramadan:
                work_start = work_loc.get('ramadan_work_start', '09:00')
                work_end = work_loc.get('ramadan_work_end', '15:00')
            else:
                work_start = work_loc.get('work_start', '08:00')
                work_end = work_loc.get('work_end', '16:00')
    elif is_ramadan:
        work_start = "09:00"
        work_end = "15:00"
    
    # تحديد أوقات الدخول والخروج بناءً على الحالة
    if body.new_status in counted_statuses:
        # حالات الحضور: نضع أوقات الدوام
        final_check_in = body.check_in_time or (daily.get('check_in_time') if daily else None) or work_start
        final_check_out = body.check_out_time or (daily.get('check_out_time') if daily else None) or work_end
    else:
        # حالات الغياب/الإجازة: لا أوقات
        final_check_in = None
        final_check_out = None
    
    await db.daily_status.update_one(
        {"employee_id": employee_id, "date": date},
        {
            "$set": {
                "final_status": final_status_to_save,
                "status_ar": status_ar_map.get(body.new_status, body.new_status),
                "decision_reason_ar": reason_text,
                "decision_source": "exemption" if is_exemption else ("gift_leave" if is_gift_leave else "manual_correction"),
                "is_gift_leave": is_gift_leave,
                "is_exemption": is_exemption,
                "check_in_time": final_check_in,
                "check_out_time": final_check_out,
                # ساعات العمل المحتسبة
                "actual_hours": actual_hours,
                "worked_hours": actual_hours,
                "required_hours": daily_hours,
                # تصفير دقائق التأخير للحالات المناسبة
                "late_minutes": 0 if body.new_status in ['PRESENT', 'EXEMPTED', 'GIFT_LEAVE', 'ON_LEAVE', 'ON_MISSION', 'EXCUSED'] else (daily.get('late_minutes', 0) if daily else 0),
                "early_leave_minutes": 0 if body.new_status in ['PRESENT', 'EXEMPTED', 'GIFT_LEAVE', 'ON_LEAVE', 'ON_MISSION', 'EXCUSED'] else (daily.get('early_leave_minutes', 0) if daily else 0),
                "updated_at": now,
                "updated_by": user['user_id']
            },
            "$push": {
                "corrections": correction
            }
        },
        upsert=True
    )
    
    # إذا كان إعفاء، نسجله كمعاملة
    if is_exemption:
        exemption_tx = {
            "id": str(uuid.uuid4()),
            "ref_no": f"EX-{date.replace('-', '')}-{employee_id[-4:]}",
            "type": "exemption",
            "status": "executed",
            "employee_id": employee_id,
            "data": {
                "employee_id": employee_id,
                "employee_name_ar": emp.get('full_name_ar', ''),
                "employee_name_en": emp.get('full_name', ''),
                "date": date,
                "reason": body.reason,
                "original_status": daily.get('final_status', 'UNKNOWN') if daily else 'UNKNOWN',
                "exemption_type": "administrative",
                "is_exemption": True
            },
            "created_at": now,
            "created_by": user['user_id'],
            "approved_by": user['user_id'],
            "approved_by_name": user.get('full_name', ''),
            "executed_at": now,
            "executed_by": user['user_id']
        }
        await db.transactions.insert_one(exemption_tx)
    
    # إذا كانت إجازة مكافأة، نسجلها كمعاملة حتى تظهر في النظام بالكامل
    if is_gift_leave:
        gift_leave_tx = {
            "id": str(uuid.uuid4()),
            "ref_no": f"GL-{date.replace('-', '')}-{employee_id[-4:]}",
            "type": "gift_leave",
            "status": "executed",
            "employee_id": employee_id,
            "data": {
                "employee_id": employee_id,
                "employee_name_ar": emp.get('full_name_ar', ''),
                "employee_name_en": emp.get('full_name', ''),
                "start_date": date,
                "end_date": date,
                "days": 1,
                "reason": body.reason,
                "leave_type": "gift_leave",
                "is_gift": True,
                "does_not_deduct_balance": True
            },
            "created_at": now,
            "created_by": user['user_id'],
            "approved_by": user['user_id'],
            "approved_by_name": user.get('full_name', ''),
            "executed_at": now,
            "executed_by": user['user_id']
        }
        await db.transactions.insert_one(gift_leave_tx)
    
    # حفظ في أرشيف STAS السنوي (قرارات سلطان المباشرة)
    year = date[:4]
    archive_entry = {
        "id": str(uuid.uuid4()),
        "year": year,
        "type": "gift_leave" if is_gift_leave else "direct_correction",
        "employee_id": employee_id,
        "employee_name_ar": emp.get('full_name_ar', ''),
        "date": date,
        "original_status": daily.get('final_status', 'UNKNOWN') if daily else 'UNKNOWN',
        "final_status": final_status_to_save,
        "reason": body.reason,
        "is_gift_leave": is_gift_leave,
        "decided_by": user['user_id'],
        "decided_by_name": user.get('full_name_ar', user.get('full_name', '')),
        "decided_at": now,
        "archived_at": now
    }
    await db.stas_annual_archive.insert_one(archive_entry)
    
    # إرسال إشعار للموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        title_ar = "إجازة مكافأة ⭐" if is_gift_leave else "تحديث حالة الحضور"
        message_ar = f"تم منحك إجازة مكافأة ليوم {date}" if is_gift_leave else f"تم تعديل حالتك ليوم {date} إلى: {status_ar_map.get(body.new_status, body.new_status)}"
        
        await create_notification(
            recipient_id=employee_id,
            notification_type=NotificationType.INFO,
            title="Gift Leave Granted" if is_gift_leave else "Attendance Status Updated",
            title_ar=title_ar,
            message=f"You have been granted a gift leave for {date}" if is_gift_leave else f"Your attendance status for {date} has been updated",
            message_ar=message_ar,
            priority=NotificationPriority.NORMAL,
            recipient_role="employee",
            reference_type="gift_leave" if is_gift_leave else "daily_status",
            reference_url="/attendance"
        )
    except Exception as e:
        # Don't fail if notification fails
        pass
    
    return {
        "success": True,
        "message": f"تم تعديل حالة {emp.get('full_name_ar', '')} إلى {status_ar_map.get(body.new_status, body.new_status)}",
        "correction": correction,
        "archived": True
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



# ==================== التحضير اليدوي للمشرفين ====================

class ManualCheckInRequest(BaseModel):
    """طلب تسجيل حضور يدوي من المشرف"""
    employee_id: str
    check_type: str  # check_in or check_out
    time: Optional[str] = None  # HH:MM format, defaults to now
    reason: str
    supervisor_acknowledgment: bool = False


@router.post("/manual-attendance")
async def supervisor_manual_attendance(
    body: ManualCheckInRequest,
    user=Depends(require_roles('supervisor'))
):
    """
    التحضير اليدوي للمشرفين - تسجيل حضور/انصراف يدوي لموظف
    
    ⚠️ القواعد:
    1. المشرف يمكنه تسجيل حضور/انصراف لموظفيه فقط
    2. النظام الآلي (GPS/البصمة) له الأولوية دائماً
    3. إذا وُجد تسجيل آلي، لا يمكن إضافة تسجيل يدوي
    4. يحتاج إقرار المشرف بتحمل المسؤولية
    """
    # التحقق من إقرار المشرف
    if not body.supervisor_acknowledgment:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "ACKNOWLEDGMENT_REQUIRED",
                "message_ar": f"عزيزي {user.get('full_name_ar', 'المشرف')}، تسجيل الحضور يدوياً يعني تحملك لمسؤوليته. يرجى تأكيد الإقرار.",
                "message_en": f"Dear {user.get('full_name', 'Supervisor')}, manual check-in/out means you take responsibility. Please confirm acknowledgment."
            }
        )
    
    # التحقق من أن الموظف تحت إشراف هذا المشرف
    emp = await db.employees.find_one({
        "id": body.employee_id,
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
    
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    
    # التحقق من عدم وجود تسجيل آلي لهذا اليوم
    existing_auto = await db.attendance_ledger.find_one({
        "employee_id": body.employee_id,
        "date": today,
        "type": body.check_type,
        "source": {"$in": ["gps", "biometric", "auto"]}
    }, {"_id": 0})
    
    if existing_auto:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "AUTO_RECORD_EXISTS",
                "message_ar": f"يوجد تسجيل آلي {'دخول' if body.check_type == 'check_in' else 'خروج'} لهذا الموظف اليوم. النظام الآلي له الأولوية.",
                "message_en": f"An automatic {body.check_type.replace('_', ' ')} record exists for this employee today. Automatic system has priority."
            }
        )
    
    # تحديد الوقت
    if body.time:
        timestamp = f"{today}T{body.time}:00"
    else:
        timestamp = now.isoformat()
    
    # إنشاء سجل الحضور اليدوي
    attendance_record = {
        "id": str(uuid.uuid4()),
        "employee_id": body.employee_id,
        "date": today,
        "type": body.check_type,
        "timestamp": timestamp,
        "source": "manual_supervisor",
        "supervisor_id": user.get('employee_id'),
        "supervisor_name_ar": user.get('full_name_ar', user.get('full_name', '')),
        "supervisor_user_id": user['user_id'],
        "reason": body.reason,
        "created_at": now.isoformat()
    }
    
    await db.attendance_ledger.insert_one(attendance_record)
    
    # إرسال إشعار للموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        check_type_ar = "دخول" if body.check_type == "check_in" else "خروج"
        
        await create_notification(
            recipient_id=body.employee_id,
            notification_type=NotificationType.INFO,
            title="Manual Attendance Recorded",
            title_ar="تسجيل حضور يدوي",
            message=f"Your supervisor recorded your {body.check_type.replace('_', ' ')} for today",
            message_ar=f"سجّل مشرفك {user.get('full_name_ar', '')} {check_type_ar} لك اليوم",
            priority=NotificationPriority.NORMAL,
            recipient_role="employee",
            reference_type="manual_attendance"
        )
    except:
        pass
    
    return {
        "success": True,
        "message_ar": f"تم تسجيل ال{check_type_ar} يدوياً بنجاح لـ {emp.get('full_name_ar', '')}",
        "message_en": f"Manual {body.check_type.replace('_', ' ')} recorded successfully for {emp.get('full_name', '')}",
        "record_id": attendance_record['id'],
        "timestamp": timestamp
    }


@router.get("/my-team-attendance")
async def get_supervisor_team_attendance(
    date: str = None,
    user=Depends(require_roles('supervisor'))
):
    """
    حالة حضور فريق المشرف اليوم - للتحضير اليدوي
    
    يُظهر حالة كل موظف وما إذا كان يمكن تسجيل حضور/انصراف يدوي له
    """
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    supervisor_employee_id = user.get('employee_id')
    
    # جلب موظفي هذا المشرف
    employees = await db.employees.find(
        {
            "supervisor_id": supervisor_employee_id,
            "is_active": {"$ne": False}
        },
        {"_id": 0}
    ).to_list(100)
    
    if not employees:
        return []
    
    emp_ids = [e['id'] for e in employees]
    emp_map = {e['id']: e for e in employees}
    
    # جلب سجلات الحضور لهذا اليوم
    attendance = await db.attendance_ledger.find(
        {"employee_id": {"$in": emp_ids}, "date": target_date},
        {"_id": 0}
    ).to_list(500)
    
    # تجميع حسب الموظف
    attendance_map = {}
    for a in attendance:
        emp_id = a['employee_id']
        if emp_id not in attendance_map:
            attendance_map[emp_id] = {
                "check_in": None,
                "check_out": None,
                "check_in_source": None,
                "check_out_source": None
            }
        if a['type'] == 'check_in':
            attendance_map[emp_id]['check_in'] = a['timestamp']
            attendance_map[emp_id]['check_in_source'] = a.get('source', 'auto')
        elif a['type'] == 'check_out':
            attendance_map[emp_id]['check_out'] = a['timestamp']
            attendance_map[emp_id]['check_out_source'] = a.get('source', 'auto')
    
    result = []
    for emp_id, emp in emp_map.items():
        att = attendance_map.get(emp_id, {})
        
        check_in = att.get('check_in')
        check_out = att.get('check_out')
        check_in_source = att.get('check_in_source')
        check_out_source = att.get('check_out_source')
        
        # يمكن تسجيل دخول يدوي فقط إذا لم يكن هناك تسجيل آلي
        can_manual_check_in = not check_in or check_in_source == 'manual_supervisor'
        can_manual_check_out = not check_out or check_out_source == 'manual_supervisor'
        
        result.append({
            "employee_id": emp_id,
            "employee_name": emp.get('full_name', ''),
            "employee_name_ar": emp.get('full_name_ar', ''),
            "employee_number": emp.get('employee_number', ''),
            "job_title_ar": emp.get('job_title_ar', emp.get('job_title', '')),
            "date": target_date,
            "check_in": check_in,
            "check_out": check_out,
            "check_in_source": check_in_source,
            "check_out_source": check_out_source,
            "can_manual_check_in": can_manual_check_in,
            "can_manual_check_out": can_manual_check_out
        })
    
    return result



# ==================== طباعة تقارير الحضور مع QR Code ====================

def generate_qr_code(data: str, size: int = 80) -> bytes:
    """إنشاء QR Code للتقرير"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


def arabic_text(text: str) -> str:
    """تحويل النص العربي للعرض الصحيح في PDF"""
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except:
        return str(text)


def register_arabic_font():
    """تسجيل الخط العربي"""
    import os
    font_paths = [
        "/app/backend/fonts/Amiri-Regular.ttf",
        "/app/backend/fonts/NotoNaskhArabic-Regular.ttf",
        "/app/backend/fonts/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont('Arabic', path))
                return 'Arabic'
            except:
                continue
    return 'Helvetica'


@router.get("/print-report")
async def print_attendance_report(
    period: str = "daily",  # daily, weekly, monthly, yearly
    date: str = None,
    month: str = None,
    year: str = None,
    employee_id: str = None,  # موظف واحد (legacy)
    employee_ids: str = None,  # قائمة موظفين مفصولة بفاصلة (جديد)
    start_date: str = None,  # من تاريخ (جديد)
    end_date: str = None,  # إلى تاريخ (جديد)
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor'))
):
    """
    طباعة تقرير الحضور PDF مع ترويسة رسمية و QR Code
    
    - period: daily/weekly/monthly/yearly
    - date: للتقرير اليومي (YYYY-MM-DD)
    - month: للتقرير الشهري (YYYY-MM)
    - year: للتقرير السنوي (YYYY)
    - employee_id: لموظف واحد (اختياري)
    - employee_ids: قائمة موظفين مفصولة بفاصلة "EMP-001,EMP-002"
    - start_date/end_date: الفترة المخصصة
    """
    # تحديد التواريخ
    now = datetime.now(timezone.utc)
    
    # إذا تم تحديد start_date و end_date مخصصة، استخدمها
    if start_date and end_date:
        period_title_ar = f"تقرير الحضور - من {start_date} إلى {end_date}"
    elif period == "daily":
        target_date = date or now.strftime("%Y-%m-%d")
        start_date = target_date
        end_date = target_date
        period_title_ar = f"تقرير الحضور اليومي - {target_date}"
    elif period == "weekly":
        target_date = date or now.strftime("%Y-%m-%d")
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        # حساب بداية ونهاية الأسبوع
        day_of_week = dt.weekday()
        days_from_sunday = (day_of_week + 1) % 7
        week_start = dt - timedelta(days=days_from_sunday)
        week_end = week_start + timedelta(days=6)
        start_date = week_start.strftime("%Y-%m-%d")
        end_date = week_end.strftime("%Y-%m-%d")
        period_title_ar = f"تقرير الحضور الأسبوعي - من {start_date} إلى {end_date}"
    elif period == "monthly":
        target_month = month or now.strftime("%Y-%m")
        start_date = f"{target_month}-01"
        # حساب آخر يوم في الشهر
        year_num, month_num = map(int, target_month.split('-'))
        if month_num == 12:
            next_month = datetime(year_num + 1, 1, 1)
        else:
            next_month = datetime(year_num, month_num + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        end_date = f"{target_month}-{last_day:02d}"
        period_title_ar = f"تقرير الحضور الشهري - {target_month}"
    else:  # yearly
        target_year = year or str(now.year)
        start_date = f"{target_year}-01-01"
        end_date = f"{target_year}-12-31"
        period_title_ar = f"تقرير الحضور السنوي - {target_year}"
    
    # جلب بيانات الشركة للترويسة
    branding = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    if not branding:
        branding = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي"
        }
    
    # بناء فلتر الموظفين
    EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']
    emp_filter = {
        "is_active": {"$ne": False},
        "id": {"$nin": EXEMPT_EMPLOYEE_IDS}
    }
    
    # تحديد الموظفين المطلوبين
    if employee_ids:
        # قائمة موظفين متعددين
        selected_ids = [eid.strip() for eid in employee_ids.split(',') if eid.strip()]
        emp_filter["id"] = {"$in": selected_ids}
    elif employee_id:
        # موظف واحد (legacy)
        emp_filter["id"] = employee_id
    elif user.get('role') == 'supervisor':
        emp_filter["supervisor_id"] = user.get('employee_id')
    
    # جلب الموظفين
    employees = await db.employees.find(
        emp_filter,
        {"_id": 0, "id": 1, "full_name_ar": 1, "full_name": 1, "employee_number": 1, "department": 1, "department_ar": 1}
    ).to_list(500)
    
    emp_map = {e['id']: e for e in employees}
    emp_ids = list(emp_map.keys())
    
    # جلب السجلات اليومية
    daily_statuses = await db.daily_status.find(
        {
            "employee_id": {"$in": emp_ids},
            "date": {"$gte": start_date, "$lte": end_date}
        },
        {"_id": 0}
    ).to_list(50000)
    
    # جلب البصمات
    attendance = await db.attendance_ledger.find(
        {
            "employee_id": {"$in": emp_ids},
            "date": {"$gte": start_date, "$lte": end_date}
        },
        {"_id": 0}
    ).to_list(50000)
    
    # تجميع البيانات
    attendance_map = {}
    for a in attendance:
        key = f"{a['employee_id']}_{a['date']}"
        if key not in attendance_map:
            attendance_map[key] = {"check_in": None, "check_out": None}
        if a['type'] == 'check_in':
            attendance_map[key]['check_in'] = a.get('timestamp', '')
        elif a['type'] == 'check_out':
            attendance_map[key]['check_out'] = a.get('timestamp', '')
    
    status_map = {}
    for s in daily_statuses:
        key = f"{s['employee_id']}_{s['date']}"
        status_map[key] = s
    
    # إنشاء PDF
    buffer = io.BytesIO()
    
    # استخدام الصفحة الأفقية للجداول الكبيرة
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # تسجيل الخط العربي
    font_name = register_arabic_font()
    
    # الأنماط
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleArabic',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    header_style = ParagraphStyle(
        'HeaderArabic',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    elements = []
    
    # إنشاء QR Code للتتبع
    report_id = str(uuid.uuid4())[:8]
    qr_data = f"ATT-{period.upper()}-{start_date}-{report_id}"
    qr_bytes = generate_qr_code(qr_data, 60)
    qr_image = Image(io.BytesIO(qr_bytes), width=50, height=50)
    
    # ترويسة مع الشعار و QR
    header_data = [
        [
            qr_image,
            Paragraph(arabic_text(branding.get('company_name_ar', 'شركة دار الكود')), title_style),
            Paragraph(arabic_text(f"رقم التقرير: {report_id}"), header_style)
        ],
        [
            '',
            Paragraph(arabic_text(period_title_ar), header_style),
            Paragraph(f"{now.strftime('%Y-%m-%d %H:%M')} :{arabic_text('تاريخ الطباعة')}", header_style)
        ]
    ]
    
    header_table = Table(header_data, colWidths=[60, 500, 150])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 0), (0, 1)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))
    
    # ترجمات الحالات
    status_ar_map = {
        'PRESENT': arabic_text('حاضر'),
        'ABSENT': arabic_text('غائب'),
        'LATE': arabic_text('متأخر'),
        'ON_LEAVE': arabic_text('إجازة'),
        'ON_ADMIN_LEAVE': arabic_text('إجازة إدارية'),
        'WEEKEND': arabic_text('عطلة'),
        'HOLIDAY': arabic_text('عطلة رسمية'),
        'ON_MISSION': arabic_text('مهمة'),
        'NOT_REGISTERED': arabic_text('لم يسجل'),
        'NOT_PROCESSED': arabic_text('غير محلل'),
        'EARLY_LEAVE': arabic_text('خروج مبكر'),
        'PERMISSION': arabic_text('استئذان')
    }
    
    # === تنسيق جديد: جدول منفصل لكل موظف ===
    
    # ترتيب الموظفين
    sorted_employees = sorted(employees, key=lambda x: x.get('full_name_ar', ''))
    
    # إنشاء قائمة جميع التواريخ في الفترة
    all_dates = []
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    while current_date <= end_dt:
        all_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)
    
    # أسماء الأيام بالعربي
    day_names_ar = ['الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
    
    # أنماط جدول كل موظف
    emp_title_style = ParagraphStyle(
        'EmpTitle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=14,
        alignment=TA_RIGHT,
        textColor=colors.white,
        spaceAfter=5
    )
    
    # لكل موظف: إنشاء جدول منفصل
    for emp_index, emp in enumerate(sorted_employees, 1):
        emp_id = emp['id']
        emp_name = emp.get('full_name_ar', emp.get('full_name', ''))
        emp_number = emp.get('employee_number', '')
        
        # عنوان الموظف
        emp_header = Table(
            [[Paragraph(arabic_text(f"{emp_index}. {emp_name} - {emp_number}"), emp_title_style)]],
            colWidths=[700]
        )
        emp_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1e3a5f')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        elements.append(emp_header)
        
        # جدول بيانات الموظف
        table_header = [
            arabic_text('#'),
            arabic_text('التاريخ'),
            arabic_text('اليوم'),
            arabic_text('الدخول'),
            arabic_text('الخروج'),
            arabic_text('موقع البصمة'),
            arabic_text('الحالة'),
            arabic_text('التأخير'),
            arabic_text('ملاحظات / سبب التعديل')
        ]
        table_data = [table_header]
        
        total_late = 0
        present_count = 0
        absent_count = 0
        
        for day_idx, date_str in enumerate(all_dates, 1):
            key = f"{emp_id}_{date_str}"
            status_data = status_map.get(key, {})
            attend_data = attendance_map.get(key, {})
            
            final_status = status_data.get('final_status', 'NOT_REGISTERED')
            
            # حساب الإحصائيات
            if final_status in ['PRESENT', 'LATE', 'ON_MISSION', 'EARLY_LEAVE', 'PERMISSION']:
                present_count += 1
            elif final_status == 'ABSENT':
                absent_count += 1
            
            # تنسيق الوقت
            check_in = status_data.get('check_in_time', attend_data.get('check_in', ''))
            check_out = status_data.get('check_out_time', attend_data.get('check_out', ''))
            if check_in and 'T' in str(check_in):
                check_in = str(check_in).split('T')[1][:5]
            elif check_in:
                check_in = str(check_in)[:5]
            if check_out and 'T' in str(check_out):
                check_out = str(check_out).split('T')[1][:5]
            elif check_out:
                check_out = str(check_out)[:5]
            
            # التأخير
            late_min = status_data.get('late_minutes', 0) or 0
            if final_status not in ['ON_MISSION', 'ON_LEAVE', 'ON_ADMIN_LEAVE', 'HOLIDAY', 'WEEKEND', 'PERMISSION']:
                total_late += late_min
            
            # موقع البصمة
            work_location = status_data.get('work_location_name_ar', status_data.get('work_location', '')) or ''
            
            # الملاحظات (سبب التعديل)
            note = status_data.get('decision_reason_ar', '') or ''
            source = status_data.get('decision_source', '')
            modified_by = status_data.get('modified_by', '')
            if modified_by or source == 'manual_correction':
                note = f"تعديل: {note}" if note else "تعديل إداري"
            
            # اسم اليوم
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            day_name = day_names_ar[dt.weekday()]
            
            table_data.append([
                str(day_idx),
                date_str,
                arabic_text(day_name),
                check_in or '-',
                check_out or '-',
                arabic_text(work_location[:15]) if work_location else '-',
                status_ar_map.get(final_status, final_status),
                arabic_text(f"{late_min} د") if late_min > 0 else '-',
                arabic_text(note[:40]) if note else '-'
            ])
        
        # صف الملخص
        table_data.append([
            '',
            arabic_text('الملخص'),
            '',
            '',
            '',
            '',
            arabic_text(f"حضور: {present_count} | غياب: {absent_count}"),
            arabic_text(f"{total_late} د") if total_late > 0 else '-',
            arabic_text(f"خصم: {total_late/480:.2f} يوم") if total_late > 480 else ''
        ])
        
        # إنشاء الجدول
        col_widths = [25, 70, 55, 45, 45, 80, 60, 50, 150]
        emp_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        emp_table.setStyle(TableStyle([
            # ترويسة
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90d9')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            # صف الملخص
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f4f8')),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            # تلوين حسب الحالة
        ]))
        
        # تلوين صفوف الغياب باللون الأحمر الفاتح
        for row_idx, row in enumerate(table_data[1:-1], 1):
            status_text = row[6] if len(row) > 6 else ''
            if status_text == arabic_text('غائب'):
                emp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#ffebee'))
                ]))
            elif status_text == arabic_text('متأخر'):
                emp_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#fff8e1'))
                ]))
        
        elements.append(emp_table)
        elements.append(Spacer(1, 20))
        
        # فاصل صفحة بعد كل موظف (إذا كان هناك موظفين آخرين)
        if emp_index < len(sorted_employees):
            elements.append(PageBreak())
    
    # تذييل
            late_count = 0
            leave_count = 0
            mission_count = 0
            total_late_min = 0
            
            for s in daily_statuses:
                if s.get('employee_id') != emp_id:
                    continue
                
                status = s.get('final_status', '')
                if status in ['PRESENT', 'EARLY_LEAVE']:
                    present += 1
                elif status == 'LATE':
                    present += 1
                    late_count += 1
                    total_late_min += s.get('late_minutes', 0)
                elif status == 'ABSENT':
                    absent += 1
                elif status in ['ON_LEAVE', 'ON_ADMIN_LEAVE']:
                    leave_count += 1
                elif status == 'ON_MISSION':
                    mission_count += 1
            
            table_data.append([
                str(idx),
                arabic_text(emp.get('full_name_ar', emp.get('full_name', ''))[:25]),
                emp.get('employee_number', ''),
                str(present),
                str(absent),
                str(late_count),
                str(leave_count),
                str(mission_count),
                arabic_text(f"{total_late_min} د") if total_late_min > 0 else '-'
            ])
    
    # إنشاء الجدول
    col_widths = None
    if period == "daily":
        # زيادة عرض الملاحظات لعرض التعليق كامل
        col_widths = [25, 120, 50, 60, 50, 50, 40, 200]
    elif period == "weekly":
        col_widths = [25, 90] + [40]*7 + [35, 35]
    else:
        col_widths = [25, 120, 50, 40, 40, 40, 40, 40, 60]
    
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 8),  # خط أصغر للعنوان
        ('FONTSIZE', (0, 1), (-1, -1), 7),  # خط أصغر للبيانات
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        # Data rows
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        # الملاحظات بمحاذاة لليمين
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
    ]))
    
    elements.append(table)
    
    # تذييل
    elements.append(Spacer(1, 20))
    footer_text = arabic_text("تم إنشاء هذا التقرير آلياً من نظام إدارة الموارد البشرية") + f" | {qr_data}"
    footer_para = Paragraph(footer_text, header_style)
    elements.append(footer_para)
    
    # بناء PDF
    doc.build(elements)
    
    buffer.seek(0)
    
    # تحديد اسم الملف
    filename = f"attendance_{period}_{start_date}_{report_id}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "X-Report-ID": report_id,
            "X-QR-Code": qr_data
        }
    )


@router.get("/print-employee-report/{employee_id}")
async def print_employee_attendance_report(
    employee_id: str,
    period: str = "monthly",
    month: str = None,
    year: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'supervisor', 'employee'))
):
    """
    طباعة تقرير حضور موظف محدد مع QR Code
    """
    # التحقق من الصلاحيات
    if user.get('role') == 'employee':
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp or emp['id'] != employee_id:
            raise HTTPException(status_code=403, detail="غير مصرح بالوصول")
    
    return await print_attendance_report(
        period=period,
        month=month,
        year=year,
        employee_id=employee_id,
        user=user
    )


# ==================== نظام تعويض التأخيرات والخروج المبكر ====================

class CompensationDecision(BaseModel):
    action: str  # 'compensate' or 'exempt'
    reason: str
    compensate_with_date: Optional[str] = None  # تاريخ اليوم الذي يعوض به


@router.get("/compensation-requests")
async def get_compensation_requests(
    month: str = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    جلب قائمة الموظفين الذين لديهم عجز في الساعات (تأخيرات/غيابات) للتعويض
    """
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    employees = await db.employees.find(
        {"status": "active", "is_hidden": {"$ne": True}},
        {"_id": 0}
    ).to_list(100)
    
    compensation_list = []
    
    for emp in employees:
        # جلب حالات الشهر
        statuses = await db.daily_status.find({
            "employee_id": emp['id'],
            "date": {"$regex": f"^{month}"}
        }, {"_id": 0}).to_list(100)
        
        # حساب العجز
        total_late_minutes = 0
        total_absent_days = 0
        late_days = []
        absent_days = []
        outside_hours_days = []  # أيام العمل خارج الدوام
        
        for s in statuses:
            status = s.get('final_status', '')
            late_min = s.get('late_minutes', 0) or 0
            date = s.get('date', '')
            
            if status == 'LATE' and late_min > 0:
                total_late_minutes += late_min
                late_days.append({
                    "date": date,
                    "late_minutes": late_min,
                    "check_in_time": s.get('check_in_time', '')
                })
            elif status == 'ABSENT':
                total_absent_days += 1
                absent_days.append({"date": date})
            elif status == 'OUTSIDE_HOURS':
                # يوم عمل خارج ساعات الدوام (يمكن استخدامه للتعويض)
                outside_hours_days.append({
                    "date": date,
                    "check_in_time": s.get('check_in_time', ''),
                    "check_out_time": s.get('check_out_time', ''),
                    "worked_hours": s.get('worked_hours', 0)
                })
        
        # إذا كان هناك عجز، نضيفه للقائمة
        if total_late_minutes > 0 or total_absent_days > 0:
            compensation_list.append({
                "employee_id": emp['id'],
                "employee_name_ar": emp.get('full_name_ar', ''),
                "employee_name_en": emp.get('full_name', ''),
                "employee_number": emp.get('employee_number', ''),
                "total_late_minutes": total_late_minutes,
                "total_late_hours": round(total_late_minutes / 60, 2),
                "total_absent_days": total_absent_days,
                "late_days": late_days,
                "absent_days": absent_days,
                "outside_hours_days": outside_hours_days,  # أيام متاحة للتعويض
                "can_compensate": len(outside_hours_days) > 0
            })
    
    return {
        "month": month,
        "employees": compensation_list
    }


@router.post("/compensate/{employee_id}/{date}")
async def compensate_attendance(
    employee_id: str,
    date: str,
    body: CompensationDecision,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    تعويض غياب أو تأخير موظف
    - action: 'compensate' = تحويل اليوم إلى حضور (التعويض بيوم عمل إضافي)
    - action: 'exempt' = إعفاء إداري (لا يُحتسب كغياب)
    """
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    daily = await db.daily_status.find_one(
        {"employee_id": employee_id, "date": date},
        {"_id": 0}
    )
    
    now = datetime.now(timezone.utc).isoformat()
    original_status = daily.get('final_status', 'UNKNOWN') if daily else 'UNKNOWN'
    
    if body.action == 'compensate':
        # تحويل إلى حضور (مع توثيق التعويض)
        new_status = 'PRESENT'
        reason_text = f"✓ تم التعويض بواسطة {user.get('full_name', '')}: {body.reason}"
        if body.compensate_with_date:
            reason_text += f" (عُوّض بتاريخ {body.compensate_with_date})"
    elif body.action == 'exempt':
        # إعفاء إداري
        new_status = 'EXEMPTED'
        reason_text = f"✓ إعفاء إداري من {user.get('full_name', '')}: {body.reason}"
    else:
        raise HTTPException(status_code=400, detail="إجراء غير صالح")
    
    # تحديث الحالة
    correction = {
        "from_status": original_status,
        "to_status": new_status,
        "action": body.action,
        "reason": body.reason,
        "compensate_with_date": body.compensate_with_date,
        "corrected_by": user['user_id'],
        "corrected_by_name": user.get('full_name', ''),
        "corrected_at": now,
        "is_compensation": body.action == 'compensate',
        "is_exemption": body.action == 'exempt'
    }
    
    await db.daily_status.update_one(
        {"employee_id": employee_id, "date": date},
        {
            "$set": {
                "final_status": new_status,
                "status_ar": "حاضر" if body.action == 'compensate' else "إعفاء",
                "decision_reason_ar": reason_text,
                "decision_source": body.action,
                "is_compensation": body.action == 'compensate',
                "is_exemption": body.action == 'exempt',
                "late_minutes": 0 if body.action in ['compensate', 'exempt'] else (daily.get('late_minutes', 0) if daily else 0),
                "updated_at": now,
                "updated_by": user['user_id']
            },
            "$push": {"corrections": correction}
        },
        upsert=True
    )
    
    # تسجيل المعاملة
    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": f"CMP-{date.replace('-', '')}-{employee_id[-4:]}",
        "type": "compensation" if body.action == 'compensate' else "exemption",
        "status": "executed",
        "employee_id": employee_id,
        "data": {
            "employee_id": employee_id,
            "employee_name_ar": emp.get('full_name_ar', ''),
            "date": date,
            "original_status": original_status,
            "new_status": new_status,
            "action": body.action,
            "reason": body.reason,
            "compensate_with_date": body.compensate_with_date
        },
        "created_at": now,
        "executed_at": now,
        "executed_by": user['user_id'],
        "executed_by_name": user.get('full_name', '')
    }
    await db.transactions.insert_one(tx)
    
    return {
        "success": True,
        "message": f"تم {'التعويض' if body.action == 'compensate' else 'الإعفاء'} بنجاح",
        "employee_name": emp.get('full_name_ar', ''),
        "date": date,
        "from_status": original_status,
        "to_status": new_status
    }


# ==================== إدارة رصيد الخروج المبكر ====================

class EarlyLeaveRequest(BaseModel):
    date: str
    from_time: str
    to_time: str
    reason: str
    deduct_from_balance: bool = True  # هل تُخصم من الرصيد؟


@router.post("/early-leave-request")
async def create_early_leave_request(
    body: EarlyLeaveRequest,
    user=Depends(get_current_user)
):
    """
    إنشاء طلب خروج مبكر (للموظف)
    """
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # حساب مدة الخروج المبكر
    try:
        from_dt = datetime.strptime(body.from_time, "%H:%M")
        to_dt = datetime.strptime(body.to_time, "%H:%M")
        duration_minutes = (to_dt - from_dt).seconds // 60
        duration_hours = round(duration_minutes / 60, 2)
    except:
        raise HTTPException(status_code=400, detail="صيغة الوقت غير صحيحة")
    
    # التحقق من الرصيد إذا كان الخصم مطلوباً
    if body.deduct_from_balance:
        current_month = body.date[:7]
        
        # جلب الإعدادات
        settings = await db.settings.find_one({"type": "early_leave_balance"}, {"_id": 0})
        monthly_allowance = settings.get('monthly_hours', 3) if settings else 3
        
        # حساب المستخدم
        used_requests = await db.transactions.find({
            "$or": [
                {"employee_id": emp['id']},
                {"data.employee_id": emp['id']}
            ],
            "type": {"$in": ["early_leave", "early_leave_request"]},
            "status": "executed",
            "data.date": {"$regex": f"^{current_month}"},
            "data.deduct_from_balance": True
        }, {"_id": 0, "data.hours": 1, "data.minutes": 1}).to_list(50)
        
        used_minutes = sum(
            (r.get('data', {}).get('hours', 0) or 0) * 60 + (r.get('data', {}).get('minutes', 0) or 0)
            for r in used_requests
        )
        remaining_minutes = (monthly_allowance * 60) - used_minutes
        
        if duration_minutes > remaining_minutes:
            return {
                "success": False,
                "error": "insufficient_balance",
                "message_ar": f"الرصيد المتبقي ({round(remaining_minutes/60, 2)} ساعة) لا يكفي",
                "remaining_hours": round(remaining_minutes / 60, 2),
                "requested_hours": duration_hours
            }
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إنشاء الطلب
    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": f"EL-{body.date.replace('-', '')}-{emp['id'][-4:]}",
        "type": "early_leave_request",
        "category": "attendance",
        "status": "pending_ops",
        "current_stage": "ops",
        "workflow": ["ops", "stas"],
        "employee_id": emp['id'],
        "employee_name": emp.get('full_name', ''),
        "employee_name_ar": emp.get('full_name_ar', ''),
        "data": {
            "employee_id": emp['id'],
            "date": body.date,
            "from_time": body.from_time,
            "to_time": body.to_time,
            "hours": int(duration_minutes // 60),
            "minutes": int(duration_minutes % 60),
            "reason": body.reason,
            "deduct_from_balance": body.deduct_from_balance
        },
        "created_at": now,
        "created_by": user['user_id'],
        "timeline": [{
            "action": "created",
            "actor_id": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": "طلب خروج مبكر"
        }],
        "approval_chain": []
    }
    
    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    
    return {
        "success": True,
        "message": "تم إرسال طلب الخروج المبكر",
        "transaction": tx
    }


@router.post("/early-leave-execute/{transaction_id}")
async def execute_early_leave(
    transaction_id: str,
    deduct_from_balance: bool = True,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    تنفيذ طلب خروج مبكر مع خيار الخصم من الرصيد أو الإعفاء
    """
    tx = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="الطلب غير موجود")
    
    if tx.get('type') != 'early_leave_request':
        raise HTTPException(status_code=400, detail="هذا ليس طلب خروج مبكر")
    
    if tx.get('status') == 'executed':
        raise HTTPException(status_code=400, detail="تم تنفيذ الطلب مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث الطلب
    await db.transactions.update_one(
        {"id": transaction_id},
        {
            "$set": {
                "status": "executed",
                "current_stage": "executed",
                "executed_at": now,
                "executed_by": user['user_id'],
                "executed_by_name": user.get('full_name', ''),
                "data.deduct_from_balance": deduct_from_balance
            },
            "$push": {
                "timeline": {
                    "action": "executed",
                    "actor_id": user['user_id'],
                    "actor_name": user.get('full_name', ''),
                    "timestamp": now,
                    "note": f"تم التنفيذ {'مع الخصم من الرصيد' if deduct_from_balance else 'بدون خصم (إعفاء)'}"
                }
            }
        }
    )
    
    return {
        "success": True,
        "message": f"تم تنفيذ الطلب {'مع الخصم' if deduct_from_balance else 'كإعفاء'}",
        "deducted": deduct_from_balance
    }
