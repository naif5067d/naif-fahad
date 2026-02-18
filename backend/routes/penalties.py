"""
Penalty Routes - مسارات العقوبات

APIs:
- GET /api/penalties/monthly/{employee_id} - عقوبات موظف شهرية
- GET /api/penalties/monthly-report - تقرير شهري لجميع الموظفين
- GET /api/penalties/yearly/{employee_id} - غيابات سنوية متفرقة
- GET /api/warnings/{employee_id} - إنذارات الموظف
- POST /api/warnings/process - معالجة الإنذارات
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import datetime
from database import db
from utils.auth import get_current_user, require_roles
from services.penalty_service import (
    calculate_monthly_penalties,
    calculate_yearly_absence,
    create_monthly_penalty_report,
    create_warning_if_needed
)

router = APIRouter(prefix="/api/penalties", tags=["Penalties"])


@router.get("/monthly/{employee_id}")
async def get_monthly_penalties(
    employee_id: str,
    year: int = Query(default=None),
    month: int = Query(default=None),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    الحصول على عقوبات موظف شهرية
    """
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    result = await calculate_monthly_penalties(employee_id, year, month)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/monthly-report")
async def get_monthly_report(
    year: int = Query(default=None),
    month: int = Query(default=None),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    تقرير العقوبات الشهري لجميع الموظفين
    """
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    reports = await create_monthly_penalty_report(year, month)
    
    # ملخص
    total_deduction = sum(r.get("total_deduction_amount", 0) for r in reports)
    total_absent_days = sum(r.get("absence", {}).get("total_days", 0) for r in reports)
    total_deficit_hours = sum(r.get("deficit", {}).get("total_deficit_hours", 0) for r in reports)
    
    return {
        "period": f"{year}-{month:02d}",
        "summary": {
            "total_employees": len(reports),
            "total_deduction_amount": round(total_deduction, 2),
            "total_absent_days": total_absent_days,
            "total_deficit_hours": round(total_deficit_hours, 2)
        },
        "employees": reports
    }


@router.get("/yearly/{employee_id}")
async def get_yearly_absence(
    employee_id: str,
    year: int = Query(default=None),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    الحصول على الغيابات السنوية المتفرقة لموظف
    """
    if not year:
        year = datetime.now().year
    
    result = await calculate_yearly_absence(employee_id, year)
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


# ================================
# Warnings Routes - الإنذارات
# ================================

@router.get("/warnings/{employee_id}")
async def get_employee_warnings(
    employee_id: str,
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    الحصول على إنذارات موظف
    """
    query = {"employee_id": employee_id}
    if status:
        query["status"] = status
    
    warnings = await db.warnings.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return warnings


@router.get("/warnings")
async def get_all_warnings(
    status: Optional[str] = Query(default="pending"),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    الحصول على جميع الإنذارات
    """
    query = {}
    if status:
        query["status"] = status
    
    warnings = await db.warnings.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # إضافة بيانات الموظف
    for w in warnings:
        emp = await db.employees.find_one({"id": w["employee_id"]}, {"_id": 0, "full_name_ar": 1, "employee_number": 1})
        if emp:
            w["employee_name_ar"] = emp.get("full_name_ar", "")
            w["employee_number"] = emp.get("employee_number", "")
    
    return warnings


@router.post("/warnings/process/{warning_id}")
async def process_warning(
    warning_id: str,
    action: str = Query(..., description="approve, reject, execute"),
    notes: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    معالجة إنذار
    """
    warning = await db.warnings.find_one({"id": warning_id})
    
    if not warning:
        raise HTTPException(status_code=404, detail="الإنذار غير موجود")
    
    if action == "approve":
        new_status = "approved"
    elif action == "reject":
        new_status = "rejected"
    elif action == "execute":
        new_status = "executed"
    else:
        raise HTTPException(status_code=400, detail="الإجراء غير صالح")
    
    await db.warnings.update_one(
        {"id": warning_id},
        {
            "$set": {
                "status": new_status,
                "processed_by": user.get("user_id"),
                "processed_at": datetime.now().isoformat(),
                "notes": notes
            }
        }
    )
    
    return {
        "success": True,
        "message": f"تم {action} الإنذار بنجاح"
    }


@router.post("/process-monthly-warnings")
async def process_monthly_warnings(
    year: int = Query(default=None),
    month: int = Query(default=None),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    معالجة وإنشاء الإنذارات الشهرية تلقائياً
    """
    if not year:
        year = datetime.now().year
    if not month:
        month = datetime.now().month
    
    reports = await create_monthly_penalty_report(year, month)
    
    created_warnings = []
    
    for report in reports:
        # معالجة إنذارات الغياب
        for warning in report.get("absence", {}).get("warnings", []):
            w = await create_warning_if_needed(
                report["employee_id"],
                warning["type"],
                warning["reason"],
                {
                    "period": f"{year}-{month:02d}",
                    "days": warning["days"],
                    "start_date": warning.get("start_date"),
                    "end_date": warning.get("end_date")
                }
            )
            if w:
                created_warnings.append(w)
    
    return {
        "success": True,
        "message": f"تم إنشاء {len(created_warnings)} إنذار جديد",
        "warnings": created_warnings
    }
