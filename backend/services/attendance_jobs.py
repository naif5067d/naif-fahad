"""
Attendance Jobs - الوظائف التلقائية لمحرك الحضور

Jobs:
1. daily_job    - يعمل يومياً بعد نهاية الدوام (مثلاً 6 مساءً)
2. monthly_job  - يعمل في أول يوم من كل شهر

هذه الـ Jobs يمكن تشغيلها:
- تلقائياً عبر scheduler (cron)
- يدوياً عبر API endpoints
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from database import db
from services.day_resolver_v2 import resolve_and_save_v2
from services.monthly_hours_service import calculate_and_save as calc_monthly, finalize_month
from services.deduction_service import create_absence_deduction_proposal
from services.notification_service import create_notification


async def run_daily_job(target_date: str = None) -> dict:
    """
    Job يومي: تحليل الحضور لجميع الموظفين ليوم محدد
    
    يجب تشغيله بعد نهاية الدوام (مثلاً 6 مساءً أو منتصف الليل)
    
    Args:
        target_date: التاريخ المستهدف (YYYY-MM-DD). إذا فارغ = أمس
    
    Returns:
        ملخص النتائج
    """
    job_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    
    # تحديد التاريخ
    if not target_date:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
    
    # جلب جميع الموظفين النشطين
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "full_name_ar": 1, "full_name": 1}
    ).to_list(1000)
    
    results = {
        "job_id": job_id,
        "job_type": "daily",
        "target_date": target_date,
        "started_at": start_time.isoformat(),
        "total_employees": len(employees),
        "processed": 0,
        "success": 0,
        "errors": 0,
        "absent_count": 0,
        "present_count": 0,
        "leave_count": 0,
        "details": []
    }
    
    absent_employees = []
    
    for emp in employees:
        emp_id = emp['id']
        emp_name = emp.get('full_name_ar', emp.get('full_name', ''))
        
        try:
            # تنفيذ التحليل وحفظه
            result = await resolve_and_save_v2(emp_id, target_date)
            
            results["processed"] += 1
            results["success"] += 1
            
            status = result.get('final_status', 'ERROR')
            
            # إحصائيات
            if status == 'ABSENT':
                results["absent_count"] += 1
                absent_employees.append({
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "daily_status_id": result.get('id')
                })
            elif status in ['PRESENT', 'LATE', 'EARLY_LEAVE']:
                results["present_count"] += 1
            elif status in ['ON_LEAVE', 'ON_ADMIN_LEAVE']:
                results["leave_count"] += 1
            
            results["details"].append({
                "employee_id": emp_id,
                "status": status,
                "success": True
            })
            
        except Exception as e:
            results["processed"] += 1
            results["errors"] += 1
            results["details"].append({
                "employee_id": emp_id,
                "status": "ERROR",
                "success": False,
                "error": str(e)
            })
    
    # إنشاء مقترحات خصم للغياب
    for absent in absent_employees:
        daily_status = await db.daily_status.find_one(
            {"id": absent['daily_status_id']},
            {"_id": 0}
        )
        if daily_status:
            await create_absence_deduction_proposal(
                absent['employee_id'],
                target_date,
                daily_status
            )
    
    results["absent_proposals_created"] = len(absent_employees)
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # حفظ سجل الـ Job
    await db.job_logs.insert_one(results)
    results.pop('_id', None)
    
    return results


async def run_monthly_job(target_month: str = None, finalize: bool = False) -> dict:
    """
    Job شهري: حساب الساعات الشهرية وإنشاء مقترحات الخصم
    
    يجب تشغيله في أول يوم من الشهر التالي
    
    Args:
        target_month: الشهر المستهدف (YYYY-MM). إذا فارغ = الشهر الماضي
        finalize: هل يتم إغلاق الشهر وإنشاء مقترحات الخصم؟
    
    Returns:
        ملخص النتائج
    """
    job_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)
    
    # تحديد الشهر
    if not target_month:
        # الشهر الماضي
        today = datetime.now(timezone.utc)
        first_of_month = today.replace(day=1)
        last_month = first_of_month - timedelta(days=1)
        target_month = last_month.strftime("%Y-%m")
    
    # جلب جميع الموظفين النشطين
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "full_name_ar": 1, "full_name": 1}
    ).to_list(1000)
    
    results = {
        "job_id": job_id,
        "job_type": "monthly",
        "target_month": target_month,
        "finalize": finalize,
        "started_at": start_time.isoformat(),
        "total_employees": len(employees),
        "processed": 0,
        "success": 0,
        "errors": 0,
        "deficit_count": 0,
        "proposals_created": 0,
        "details": []
    }
    
    for emp in employees:
        emp_id = emp['id']
        emp_name = emp.get('full_name_ar', emp.get('full_name', ''))
        
        try:
            if finalize:
                # إغلاق الشهر وإنشاء مقترحات الخصم
                monthly = await finalize_month(emp_id, target_month, "system_job")
            else:
                # حساب فقط بدون إغلاق
                monthly = await calc_monthly(emp_id, target_month)
            
            results["processed"] += 1
            results["success"] += 1
            
            has_deficit = monthly.get('deficit_hours', 0) > 0
            if has_deficit:
                results["deficit_count"] += 1
                if finalize:
                    results["proposals_created"] += 1
            
            results["details"].append({
                "employee_id": emp_id,
                "employee_name": emp_name,
                "required_hours": monthly.get('required_hours', 0),
                "actual_hours": monthly.get('actual_hours', 0),
                "net_hours": monthly.get('net_hours', 0),
                "deficit_hours": monthly.get('deficit_hours', 0),
                "has_deficit": has_deficit,
                "success": True
            })
            
        except Exception as e:
            results["processed"] += 1
            results["errors"] += 1
            results["details"].append({
                "employee_id": emp_id,
                "success": False,
                "error": str(e)
            })
    
    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    results["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
    
    # حفظ سجل الـ Job
    await db.job_logs.insert_one(results)
    results.pop('_id', None)
    
    return results


async def run_daily_job_for_range(start_date: str, end_date: str) -> dict:
    """
    تشغيل الـ Job اليومي لفترة من التواريخ
    
    مفيد لتحليل أيام سابقة أو اختبار
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    results = {
        "start_date": start_date,
        "end_date": end_date,
        "days_processed": 0,
        "daily_results": []
    }
    
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        daily_result = await run_daily_job(date_str)
        results["daily_results"].append({
            "date": date_str,
            "processed": daily_result.get('processed', 0),
            "absent": daily_result.get('absent_count', 0)
        })
        results["days_processed"] += 1
        current += timedelta(days=1)
    
    return results


async def get_job_logs(job_type: str = None, limit: int = 20) -> List[dict]:
    """جلب سجلات الـ Jobs"""
    query = {}
    if job_type:
        query["job_type"] = job_type
    
    logs = await db.job_logs.find(query, {"_id": 0}).sort("started_at", -1).limit(limit).to_list(limit)
    return logs
