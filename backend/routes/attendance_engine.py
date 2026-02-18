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
    user=Depends(require_roles('sultan', 'naif'))
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
