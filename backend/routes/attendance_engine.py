"""
Attendance Engine Routes - واجهات محرك الحضور والخصومات

يشمل:
- Day Resolver API (V2 with Trace Evidence)
- Monthly Hours API
- Deduction Proposals API
- Warning/Violation API
- Jobs API
- Team Attendance API
"""
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user, require_roles

# Services
from services.day_resolver_v2 import resolve_day_v2, resolve_and_save_v2, DayResolverV2
from services.monthly_hours_service import (
    calculate_monthly_hours, 
    calculate_and_save as calc_save_monthly,
    finalize_month,
    get_team_monthly_summary
)
from services.deduction_service import (
    get_pending_proposals,
    get_approved_proposals,
    review_proposal,
    execute_proposal
)
from services.attendance_jobs import (
    run_daily_job,
    run_monthly_job,
    run_daily_job_for_range,
    get_job_logs
)
from services.warning_service import (
    get_pending_warnings,
    get_approved_warnings,
    review_warning,
    execute_warning,
    get_employee_warnings,
    check_and_create_warnings,
    get_employee_absence_pattern
)

router = APIRouter(prefix="/api/attendance-engine", tags=["attendance-engine"])


# ==================== DAY RESOLVER ====================

class ResolveDayRequest(BaseModel):
    employee_id: str
    date: str  # YYYY-MM-DD


class ResolveBulkRequest(BaseModel):
    date: str  # YYYY-MM-DD
    employee_ids: Optional[List[str]] = None  # إذا فارغ = جميع الموظفين


class ProcessDailyRequest(BaseModel):
    date: str  # YYYY-MM-DD
    employee_id: Optional[str] = None  # إذا فارغ = جميع الموظفين


# الموظفون المستثنون من الحضور (ليسوا موظفين)
EXEMPT_EMPLOYEE_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-004', 'EMP-NAIF']


@router.post("/process-daily")
async def process_daily_attendance(req: ProcessDailyRequest, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """
    التحضير اليدوي من الإدارة - تحليل الحضور للموظفين
    
    المنطق الذكي الجديد:
    - إذا الموظف سجل بصمة ذاتية (GPS) → لا يُغيّر أبداً
    - إذا الموظف ليس له سجل → يُنشئ سجل جديد
    - إذا الموظف له سجل بدون GPS وجاءت GPS لاحقاً → يُحدّث تلقائياً
    - يمنع الكتابة فوق GPS تحت أي ظرف
    
    يستثني: ستاس، محمد، صلاح، نايف (ليسوا موظفين)
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    RIYADH_TZ = ZoneInfo('Asia/Riyadh')
    
    # جلب الموظفين
    if req.employee_id:
        employees = await db.employees.find(
            {"id": req.employee_id, "is_active": {"$ne": False}}, 
            {"_id": 0, "id": 1}
        ).to_list(1)
    else:
        employees = await db.employees.find(
            {
                "is_active": {"$ne": False},
                "id": {"$nin": EXEMPT_EMPLOYEE_IDS}
            }, 
            {"_id": 0, "id": 1}
        ).to_list(500)
    
    processed = 0
    skipped_gps = 0
    skipped_existing = 0
    updated = 0
    results = []
    
    for emp in employees:
        result = await resolve_and_save_v2(emp['id'], req.date)
        
        action = result.get('action', 'processed')
        
        if action == 'skipped':
            skipped_gps += 1
            results.append({
                "employee_id": emp['id'],
                "action": "skipped_gps",
                "reason_ar": result.get('reason_ar', 'بصمة GPS موجودة')
            })
        elif action == 'kept':
            skipped_existing += 1
            results.append({
                "employee_id": emp['id'],
                "action": "kept",
                "reason_ar": result.get('reason_ar', 'السجل موجود')
            })
        elif action == 'updated':
            updated += 1
            results.append({
                "employee_id": emp['id'],
                "action": "updated",
                "status": result.get('final_status'),
                "status_ar": result.get('status_ar'),
                "reason_ar": result.get('reason_ar')
            })
        else:
            processed += 1
            results.append({
                "employee_id": emp['id'],
                "action": "created",
                "status": result.get('final_status'),
                "status_ar": result.get('status_ar'),
                "late_minutes": result.get('late_minutes', 0)
            })
    
    # رسالة واضحة بالعربي
    message_parts = []
    if processed > 0:
        message_parts.append(f"✅ {processed} موظف جديد")
    if updated > 0:
        message_parts.append(f"🔄 {updated} تحديث")
    if skipped_gps > 0:
        message_parts.append(f"🔒 {skipped_gps} محمي (GPS)")
    if skipped_existing > 0:
        message_parts.append(f"⏭️ {skipped_existing} موجود")
    
    return {
        "success": True,
        "date": req.date,
        "processed": processed,
        "updated": updated,
        "skipped_gps": skipped_gps,
        "skipped_existing": skipped_existing,
        "total": len(employees),
        "message_ar": " | ".join(message_parts) if message_parts else "لا يوجد موظفين للمعالجة",
        "explanation_ar": "🔒 GPS لا يمكن التعديل عليها | 🔄 تم تحديث من جاءت له GPS بعد التحضير السابق",
        "results": results
    }


@router.post("/resolve-day")
async def api_resolve_day(req: ResolveDayRequest, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """تحليل يوم واحد لموظف (V2 مع العروق)"""
    result = await resolve_and_save_v2(req.employee_id, req.date)
    return result


@router.post("/resolve-bulk")
async def api_resolve_bulk(req: ResolveBulkRequest, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """تحليل يوم لجميع الموظفين أو مجموعة محددة (V2 مع العروق)"""
    if req.employee_ids:
        employees = await db.employees.find(
            {"id": {"$in": req.employee_ids}, "is_active": {"$ne": False}}, 
            {"_id": 0, "id": 1}
        ).to_list(500)
    else:
        employees = await db.employees.find(
            {"is_active": {"$ne": False}}, 
            {"_id": 0, "id": 1}
        ).to_list(500)
    
    results = []
    for emp in employees:
        result = await resolve_and_save_v2(emp['id'], req.date)
        results.append({
            "employee_id": emp['id'],
            "status": result.get('final_status'),
            "error": result.get('error'),
            "trace_summary": result.get('trace_summary', {}).get('conclusion_ar')
        })
    
    return {
        "date": req.date,
        "processed": len(results),
        "results": results
    }


@router.get("/daily-status/{employee_id}/{date}")
async def get_daily_status(employee_id: str, date: str, user=Depends(get_current_user)):
    """جلب السجل اليومي لموظف (مع العروق)"""
    record = await db.daily_status.find_one(
        {"employee_id": employee_id, "date": date}, 
        {"_id": 0}
    )
    
    if not record:
        # محاولة التحليل الآن باستخدام V2
        record = await resolve_day_v2(employee_id, date)
    
    return record


@router.get("/daily-status-range/{employee_id}")
async def get_daily_status_range(
    employee_id: str, 
    start_date: str, 
    end_date: str,
    user=Depends(get_current_user)
):
    """جلب السجلات اليومية لفترة"""
    records = await db.daily_status.find({
        "employee_id": employee_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0}).sort("date", 1).to_list(100)
    
    return records


# ==================== DAILY STATUS CORRECTION ====================

class CorrectionRequest(BaseModel):
    new_status: str
    reason: str


@router.patch("/daily-status/{record_id}/correct")
async def correct_daily_status(
    record_id: str, 
    req: CorrectionRequest,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """تصحيح السجل اليومي (ينشئ transaction)"""
    record = await db.daily_status.find_one({"id": record_id}, {"_id": 0})
    
    if not record:
        raise HTTPException(status_code=404, detail="السجل غير موجود")
    
    # فحص حالة القفل
    if record.get('lock_status') == 'locked':
        raise HTTPException(status_code=400, detail="السجل مقفل ولا يمكن تعديله")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إنشاء سجل التصحيح
    correction = {
        "id": str(uuid.uuid4()) if 'uuid' in dir() else now,
        "old_status": record['final_status'],
        "new_status": req.new_status,
        "reason": req.reason,
        "corrected_by": user['user_id'],
        "corrected_at": now
    }
    
    # تحديث السجل
    from models.daily_status import STATUS_AR, DailyStatusEnum
    status_ar = STATUS_AR.get(DailyStatusEnum(req.new_status), req.new_status)
    
    await db.daily_status.update_one(
        {"id": record_id},
        {
            "$set": {
                "final_status": req.new_status,
                "status_ar": status_ar,
                "updated_at": now,
                "updated_by": user['user_id']
            },
            "$push": {"corrections": correction}
        }
    )
    
    return {"message": "تم التصحيح", "correction": correction}


# ==================== MONTHLY HOURS ====================

class MonthlyHoursRequest(BaseModel):
    employee_id: str
    month: str  # YYYY-MM


@router.post("/monthly-hours/calculate")
async def api_calculate_monthly(req: MonthlyHoursRequest, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """حساب الساعات الشهرية"""
    result = await calc_save_monthly(req.employee_id, req.month)
    return result


@router.post("/monthly-hours/finalize")
async def api_finalize_month(req: MonthlyHoursRequest, user=Depends(require_roles('stas'))):
    """إغلاق الشهر (STAS فقط)"""
    result = await finalize_month(req.employee_id, req.month, user['user_id'])
    return result


@router.get("/monthly-hours/{employee_id}/{month}")
async def get_monthly_hours(employee_id: str, month: str, user=Depends(get_current_user)):
    """جلب ملخص الساعات الشهرية"""
    record = await db.monthly_hours.find_one(
        {"employee_id": employee_id, "month": month}, 
        {"_id": 0}
    )
    
    if not record:
        # حساب جديد
        record = await calculate_monthly_hours(employee_id, month)
    
    return record


@router.get("/monthly-hours/team/{month}")
async def get_team_monthly(month: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """ملخص الفريق الشهري"""
    return await get_team_monthly_summary(month)


# ==================== DEDUCTION PROPOSALS ====================

class ReviewRequest(BaseModel):
    approved: bool
    note: Optional[str] = ""


class ExecuteRequest(BaseModel):
    note: Optional[str] = ""


@router.get("/deductions/pending")
async def get_pending(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """مقترحات الخصم المعلقة"""
    return await get_pending_proposals()


@router.get("/deductions/approved")
async def get_approved(user=Depends(require_roles('stas'))):
    """مقترحات الخصم الموافق عليها (للتنفيذ)"""
    return await get_approved_proposals()


@router.post("/deductions/{proposal_id}/review")
async def api_review_proposal(
    proposal_id: str, 
    req: ReviewRequest,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """مراجعة مقترح الخصم (سلطان/نايف)"""
    result = await review_proposal(proposal_id, req.approved, user['user_id'], req.note)
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/deductions/{proposal_id}/execute")
async def api_execute_proposal(
    proposal_id: str, 
    req: ExecuteRequest,
    user=Depends(require_roles('stas'))
):
    """تنفيذ مقترح الخصم (STAS فقط)"""
    result = await execute_proposal(proposal_id, user['user_id'], req.note)
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.get("/deductions/employee/{employee_id}")
async def get_employee_deductions(employee_id: str, user=Depends(get_current_user)):
    """جلب خصومات موظف"""
    return await db.deduction_proposals.find(
        {"employee_id": employee_id}, 
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)


# ==================== TEAM ATTENDANCE VIEW ====================

@router.get("/team-attendance/{date}")
async def get_team_attendance_day(date: str, user=Depends(require_roles('stas', 'sultan', 'naif', 'supervisor'))):
    """عرض حضور الفريق ليوم واحد"""
    # جلب جميع السجلات اليومية
    records = await db.daily_status.find({"date": date}, {"_id": 0}).to_list(500)
    
    # إضافة بيانات الموظفين
    result = []
    for r in records:
        emp = await db.employees.find_one({"id": r['employee_id']}, {"_id": 0, "full_name": 1, "full_name_ar": 1, "photo_url": 1})
        if emp:
            r['employee_name'] = emp.get('full_name_ar', emp.get('full_name', ''))
            r['photo_url'] = emp.get('photo_url')
            result.append(r)
    
    return result


@router.get("/team-attendance/week/{start_date}")
async def get_team_attendance_week(start_date: str, user=Depends(require_roles('stas', 'sultan', 'naif', 'supervisor'))):
    """عرض حضور الفريق لأسبوع"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = start + timedelta(days=6)
    end_date = end.strftime("%Y-%m-%d")
    
    # جلب جميع الموظفين النشطين
    employees = await db.employees.find(
        {"is_active": {"$ne": False}}, 
        {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1, "photo_url": 1}
    ).to_list(500)
    
    result = []
    for emp in employees:
        # جلب سجلات الأسبوع
        records = await db.daily_status.find({
            "employee_id": emp['id'],
            "date": {"$gte": start_date, "$lte": end_date}
        }, {"_id": 0}).sort("date", 1).to_list(7)
        
        # جلب ملخص الشهر
        month = start_date[:7]
        monthly = await db.monthly_hours.find_one(
            {"employee_id": emp['id'], "month": month},
            {"_id": 0, "actual_hours": 1, "required_hours": 1, "net_hours": 1, "permission_hours": 1}
        )
        
        result.append({
            "employee_id": emp['id'],
            "employee_name": emp.get('full_name_ar', emp.get('full_name', '')),
            "photo_url": emp.get('photo_url'),
            "week_records": records,
            "monthly_summary": monthly
        })
    
    return result


@router.get("/team-attendance/month/{month}")
async def get_team_attendance_month(month: str, user=Depends(require_roles('stas', 'sultan', 'naif', 'supervisor'))):
    """عرض حضور الفريق لشهر"""
    employees = await db.employees.find(
        {"is_active": {"$ne": False}}, 
        {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1, "photo_url": 1}
    ).to_list(500)
    
    result = []
    for emp in employees:
        # جلب الملخص الشهري
        monthly = await db.monthly_hours.find_one(
            {"employee_id": emp['id'], "month": month},
            {"_id": 0}
        )
        
        if not monthly:
            monthly = await calculate_monthly_hours(emp['id'], month)
        
        # حساب slider bar (نسبة الساعات)
        progress = 0
        if monthly and monthly.get('required_hours', 0) > 0:
            progress = min(100, (monthly.get('actual_hours', 0) / monthly['required_hours']) * 100)
        
        result.append({
            "employee_id": emp['id'],
            "employee_name": emp.get('full_name_ar', emp.get('full_name', '')),
            "photo_url": emp.get('photo_url'),
            "required_hours": monthly.get('required_hours', 0) if monthly else 0,
            "actual_hours": monthly.get('actual_hours', 0) if monthly else 0,
            "permission_hours": monthly.get('permission_hours', 0) if monthly else 0,
            "net_hours": monthly.get('net_hours', 0) if monthly else 0,
            "deficit_hours": monthly.get('deficit_hours', 0) if monthly else 0,
            "progress_percent": round(progress, 1),
            "status": "ok" if monthly and monthly.get('net_hours', 0) >= 0 else "warning"
        })
    
    return result


# ==================== LOCK MANAGEMENT ====================

@router.post("/daily-status/{record_id}/lock")
async def lock_daily_status(record_id: str, user=Depends(require_roles('stas'))):
    """قفل السجل اليومي (STAS)"""
    now = datetime.now(timezone.utc).isoformat()
    
    await db.daily_status.update_one(
        {"id": record_id},
        {"$set": {
            "lock_status": "locked",
            "locked_at": now,
            "locked_by": user['user_id']
        }}
    )
    
    return {"message": "تم قفل السجل"}


@router.post("/daily-status/{record_id}/review")
async def set_review_status(record_id: str, user=Depends(require_roles('stas'))):
    """تحويل السجل للمراجعة"""
    now = datetime.now(timezone.utc).isoformat()
    review_deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    
    await db.daily_status.update_one(
        {"id": record_id},
        {"$set": {
            "lock_status": "review",
            "review_started_at": now,
            "lock_deadline": review_deadline
        }}
    )
    
    return {"message": "تم تحويل السجل للمراجعة"}



# ==================== JOBS API ====================

class DailyJobRequest(BaseModel):
    target_date: Optional[str] = None  # YYYY-MM-DD


class MonthlyJobRequest(BaseModel):
    target_month: Optional[str] = None  # YYYY-MM
    finalize: bool = False


class DateRangeRequest(BaseModel):
    start_date: str
    end_date: str


@router.post("/jobs/daily")
async def api_run_daily_job(req: DailyJobRequest, user=Depends(require_roles('stas'))):
    """
    تشغيل Job الحضور اليومي
    
    يحلل جميع الموظفين ليوم محدد وينشئ مقترحات الخصم للغياب
    """
    result = await run_daily_job(req.target_date)
    return result


@router.post("/jobs/monthly")
async def api_run_monthly_job(req: MonthlyJobRequest, user=Depends(require_roles('stas'))):
    """
    تشغيل Job الحساب الشهري
    
    يحسب الساعات الشهرية لجميع الموظفين.
    إذا finalize=True يُغلق الشهر وينشئ مقترحات الخصم.
    """
    result = await run_monthly_job(req.target_month, req.finalize)
    return result


@router.post("/jobs/daily-range")
async def api_run_daily_range(req: DateRangeRequest, user=Depends(require_roles('stas'))):
    """
    تشغيل Job الحضور اليومي لفترة من التواريخ
    """
    result = await run_daily_job_for_range(req.start_date, req.end_date)
    return result


@router.get("/jobs/logs")
async def api_get_job_logs(job_type: Optional[str] = None, limit: int = 20, user=Depends(require_roles('stas'))):
    """جلب سجلات تشغيل الـ Jobs"""
    logs = await get_job_logs(job_type, limit)
    return logs


# ==================== WARNINGS API ====================

class WarningReviewRequest(BaseModel):
    approved: bool
    note: Optional[str] = ""


class WarningExecuteRequest(BaseModel):
    note: Optional[str] = ""


@router.get("/warnings/pending")
async def api_get_pending_warnings(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """جلب الإنذارات المعلقة للمراجعة"""
    return await get_pending_warnings()


@router.get("/warnings/approved")
async def api_get_approved_warnings(user=Depends(require_roles('stas'))):
    """جلب الإنذارات الموافق عليها (للتنفيذ)"""
    return await get_approved_warnings()


@router.get("/warnings/employee/{employee_id}")
async def api_get_employee_warnings(employee_id: str, year: Optional[str] = None, user=Depends(get_current_user)):
    """جلب إنذارات موظف"""
    return await get_employee_warnings(employee_id, year)


@router.get("/warnings/employee/{employee_id}/pattern")
async def api_get_absence_pattern(employee_id: str, year: Optional[str] = None, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """تحليل نمط الغياب لموظف"""
    return await get_employee_absence_pattern(employee_id, year)


@router.post("/warnings/{warning_id}/review")
async def api_review_warning(
    warning_id: str,
    req: WarningReviewRequest,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """مراجعة الإنذار (سلطان/نايف)"""
    result = await review_warning(warning_id, req.approved, user['user_id'], req.note)
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/warnings/{warning_id}/execute")
async def api_execute_warning(
    warning_id: str,
    req: WarningExecuteRequest,
    user=Depends(require_roles('stas'))
):
    """تنفيذ الإنذار (STAS فقط)"""
    result = await execute_warning(warning_id, user['user_id'], req.note)
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.post("/warnings/check/{employee_id}")
async def api_check_warnings(employee_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """فحص الموظف وإنشاء الإنذارات اللازمة"""
    return await check_and_create_warnings(employee_id)


# ==================== MY FINANCES (Employee) ====================

@router.get("/my-finances/deductions")
async def get_my_deductions(user=Depends(get_current_user)):
    """
    جلب خصومات الموظف الحالي (صفحة ماليّاتي)
    """
    employee_id = user.get('employee_id') or user.get('user_id')
    
    # جلب الخصومات المنفذة من finance_ledger
    deductions = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit"
    }, {"_id": 0}).sort("executed_at", -1).to_list(100)
    
    # تحويل البيانات لتتوافق مع الواجهة
    result = []
    for d in deductions:
        result.append({
            "id": d.get('id'),
            "amount": d.get('amount'),
            "currency": d.get('currency', 'SAR'),
            "reason": d.get('description'),
            "reason_ar": d.get('description_ar'),
            "deduction_type": d.get('deduction_type'),
            "month": d.get('month'),
            "date": d.get('executed_at', '')[:10] if d.get('executed_at') else '',
            "status": "executed",
            "executed_at": d.get('executed_at'),
            "explanation": d.get('explanation', {})
        })
    
    return result


@router.get("/my-finances/warnings")
async def get_my_warnings(user=Depends(get_current_user)):
    """جلب إنذارات الموظف الحالي"""
    employee_id = user.get('employee_id') or user.get('user_id')
    
    warnings = await db.warning_ledger.find({
        "employee_id": employee_id,
        "status": "executed"
    }, {"_id": 0}).sort("executed_at", -1).to_list(50)
    
    return warnings


@router.get("/my-finances/summary")
async def get_my_finance_summary(user=Depends(get_current_user)):
    """
    ملخص مالي للموظف الحالي
    """
    employee_id = user.get('employee_id') or user.get('user_id')
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    current_year = datetime.now(timezone.utc).strftime("%Y")
    
    # إجمالي الخصومات هذا الشهر
    monthly_deductions = await db.finance_ledger.aggregate([
        {
            "$match": {
                "employee_id": employee_id,
                "type": "debit",
                "month": current_month
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
    ]).to_list(1)
    
    # إجمالي الخصومات هذه السنة
    yearly_deductions = await db.finance_ledger.aggregate([
        {
            "$match": {
                "employee_id": employee_id,
                "type": "debit",
                "month": {"$regex": f"^{current_year}"}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$amount"},
                "count": {"$sum": 1}
            }
        }
    ]).to_list(1)
    
    # عدد الإنذارات
    warnings_count = await get_employee_warnings(employee_id, current_year)
    
    # حالة الغياب
    absence_pattern = await get_employee_absence_pattern(employee_id, current_year)
    
    return {
        "employee_id": employee_id,
        "current_month": current_month,
        "current_year": current_year,
        "monthly_deductions": {
            "total": monthly_deductions[0]['total'] if monthly_deductions else 0,
            "count": monthly_deductions[0]['count'] if monthly_deductions else 0
        },
        "yearly_deductions": {
            "total": yearly_deductions[0]['total'] if yearly_deductions else 0,
            "count": yearly_deductions[0]['count'] if yearly_deductions else 0
        },
        "warnings_count": len(warnings_count),
        "absence_summary": {
            "total_absent_days": absence_pattern['total_absent_days'],
            "max_consecutive": absence_pattern['max_consecutive_days'],
            "warning_15_days": absence_pattern['reaches_15_consecutive'],
            "warning_30_days": absence_pattern['reaches_30_scattered']
        }
    }



# ==================== FORGOTTEN PUNCH REQUESTS ====================

class ForgottenPunchRequest(BaseModel):
    date: str  # YYYY-MM-DD
    punch_type: str  # 'checkin' أو 'checkout'
    claimed_time: str  # HH:MM (الوقت المدّعى)
    reason: str


@router.post("/forgotten-punch")
async def request_forgotten_punch(req: ForgottenPunchRequest, user=Depends(get_current_user)):
    """
    طلب تسجيل نسيان بصمة
    - الحد الأقصى: 3 طلبات مقبولة شهرياً
    - يتم إنشاء الطلب بحالة 'pending'
    """
    employee_id = user.get('employee_id')
    if not employee_id:
        raise HTTPException(400, "لا يوجد employee_id للمستخدم")
    
    # التحقق من الشهر الحالي
    date_obj = datetime.strptime(req.date, "%Y-%m-%d")
    current_month = date_obj.month
    current_year = date_obj.year
    
    # عدد الطلبات المقبولة هذا الشهر
    approved_count = await db.forgotten_punch_requests.count_documents({
        "employee_id": employee_id,
        "status": "approved",
        "$expr": {
            "$and": [
                {"$eq": [{"$month": {"$dateFromString": {"dateString": "$date"}}}, current_month]},
                {"$eq": [{"$year": {"$dateFromString": {"dateString": "$date"}}}, current_year]}
            ]
        }
    })
    
    # حد 3 طلبات شهرياً - القاعدة مخفية عن الموظف
    if approved_count >= 3:
        raise HTTPException(400, "تم رفض الطلب - يرجى مراجعة مديرك")
    
    # إنشاء الطلب
    request_id = str(uuid.uuid4())
    await db.forgotten_punch_requests.insert_one({
        "id": request_id,
        "employee_id": employee_id,
        "date": req.date,
        "punch_type": req.punch_type,
        "claimed_time": req.claimed_time,
        "reason": req.reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get('id')
    })
    
    return {"success": True, "request_id": request_id, "message_ar": "تم إرسال الطلب بنجاح"}


@router.get("/forgotten-punch/pending")
async def get_pending_forgotten_punch(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """الحصول على طلبات نسيان البصمة المعلقة"""
    requests = await db.forgotten_punch_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # إضافة بيانات الموظف
    for req in requests:
        emp = await db.employees.find_one(
            {"id": req['employee_id']},
            {"_id": 0, "full_name_ar": 1, "employee_number": 1}
        )
        req['employee_name_ar'] = emp.get('full_name_ar', '') if emp else ''
        req['employee_number'] = emp.get('employee_number', '') if emp else ''
    
    return requests


@router.post("/forgotten-punch/{request_id}/approve")
async def approve_forgotten_punch(request_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """الموافقة على طلب نسيان البصمة"""
    req = await db.forgotten_punch_requests.find_one(
        {"id": request_id, "status": "pending"},
        {"_id": 0}
    )
    
    if not req:
        raise HTTPException(404, "الطلب غير موجود أو تمت معالجته")
    
    # التحقق من الحد الشهري قبل الموافقة
    date_obj = datetime.strptime(req['date'], "%Y-%m-%d")
    approved_count = await db.forgotten_punch_requests.count_documents({
        "employee_id": req['employee_id'],
        "status": "approved",
        "$expr": {
            "$and": [
                {"$eq": [{"$month": {"$dateFromString": {"dateString": "$date"}}}, date_obj.month]},
                {"$eq": [{"$year": {"$dateFromString": {"dateString": "$date"}}}, date_obj.year]}
            ]
        }
    })
    
    if approved_count >= 3:
        raise HTTPException(400, "الموظف تجاوز حد الـ 3 طلبات شهرياً")
    
    # تحديث الحالة
    await db.forgotten_punch_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": user.get('id')
        }}
    )
    
    # إعادة معالجة اليوم
    await resolve_and_save_v2(req['employee_id'], req['date'])
    
    return {"success": True, "message_ar": "تمت الموافقة وإعادة المعالجة"}


@router.post("/forgotten-punch/{request_id}/reject")
async def reject_forgotten_punch(request_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """رفض طلب نسيان البصمة"""
    result = await db.forgotten_punch_requests.update_one(
        {"id": request_id, "status": "pending"},
        {"$set": {
            "status": "rejected",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": user.get('id')
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(404, "الطلب غير موجود أو تمت معالجته")
    
    return {"success": True, "message_ar": "تم رفض الطلب"}


@router.get("/forgotten-punch/my-requests")
async def get_my_forgotten_punch_requests(user=Depends(get_current_user)):
    """الحصول على طلبات نسيان البصمة للموظف الحالي"""
    employee_id = user.get('employee_id')
    if not employee_id:
        return []
    
    requests = await db.forgotten_punch_requests.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return requests
