"""
Executive Analytics API
لوحة الحوكمة الذكية - المؤشرات التنفيذية
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user, require_roles
import calendar

router = APIRouter(prefix="/api/analytics", tags=["Executive Analytics"])

# ==================== HELPER FUNCTIONS ====================

def get_month_range(year: int, month: int):
    """Get start and end dates for a month"""
    start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{last_day}"
    return start, end


async def calculate_attendance_score(employee_id: str = None, month: str = None) -> dict:
    """
    حساب مؤشر الحضور
    الصيغة: (أيام الحضور / أيام العمل) × 100 - (دقائق التأخير × 0.05)
    """
    now = datetime.now(timezone.utc)
    if month:
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
    else:
        year, mon = now.year, now.month
    
    start_date, end_date = get_month_range(year, mon)
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if employee_id:
        query["employee_id"] = employee_id
    
    records = await db.daily_status.find(query, {"_id": 0}).to_list(5000)
    
    if not records:
        return {"score": 0, "present_days": 0, "work_days": 0, "late_minutes": 0, "absent_days": 0}
    
    # حساب الأيام
    present_statuses = ["PRESENT", "LATE", "LATE_EXCUSED", "EARLY_LEAVE", "EARLY_EXCUSED", "PERMISSION", "ON_MISSION"]
    work_statuses = present_statuses + ["ABSENT"]
    
    work_days = len([r for r in records if r.get('final_status') in work_statuses])
    present_days = len([r for r in records if r.get('final_status') in present_statuses])
    absent_days = len([r for r in records if r.get('final_status') == "ABSENT"])
    total_late_minutes = sum(r.get('late_minutes', 0) for r in records)
    
    if work_days == 0:
        return {"score": 100, "present_days": 0, "work_days": 0, "late_minutes": 0, "absent_days": 0}
    
    # الصيغة
    presence_rate = (present_days / work_days) * 100
    late_penalty = min(total_late_minutes * 0.05, 20)  # حد أقصى 20 نقطة خصم
    score = max(0, min(100, presence_rate - late_penalty))
    
    return {
        "score": round(score, 1),
        "present_days": present_days,
        "work_days": work_days,
        "late_minutes": total_late_minutes,
        "absent_days": absent_days,
        "presence_rate": round(presence_rate, 1)
    }


async def calculate_task_score(employee_id: str = None, month: str = None) -> dict:
    """
    حساب مؤشر أداء المهام
    الصيغة: متوسط final_score × 20 (لتحويل من 5 إلى 100)
    """
    query = {"status": "closed"}
    if employee_id:
        query["employee_id"] = employee_id
    
    if month:
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(year, mon)
        query["closed_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    
    if not tasks:
        return {"score": 0, "total_tasks": 0, "completed_on_time": 0, "delayed": 0, "average_rating": 0}
    
    scores = [t.get('final_score', {}).get('final_score', 0) for t in tasks if t.get('final_score')]
    on_time = len([t for t in tasks if not t.get('delay_info', {}).get('delayed', False)])
    delayed = len(tasks) - on_time
    
    avg_score = sum(scores) / len(scores) if scores else 0
    score = min(100, avg_score * 20)  # تحويل من 5 إلى 100
    
    return {
        "score": round(score, 1),
        "total_tasks": len(tasks),
        "completed_on_time": on_time,
        "delayed": delayed,
        "average_rating": round(avg_score, 2),
        "completion_rate": round((on_time / len(tasks)) * 100, 1) if tasks else 0
    }


async def calculate_financial_score(employee_id: str = None, month: str = None) -> dict:
    """
    حساب مؤشر الانضباط المالي
    الصيغة: (العهد المعتمدة من أول مرة / الإجمالي) × 100
    """
    query = {"status": {"$in": ["approved", "executed", "closed"]}}
    if employee_id:
        query["created_by"] = employee_id
    
    if month:
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(year, mon)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    custodies = await db.admin_custodies.find(query, {"_id": 0}).to_list(500)
    
    if not custodies:
        return {"score": 100, "total_custodies": 0, "approved_first_time": 0, "returned": 0, "total_spent": 0}
    
    # العهد المعتمدة من أول مرة (لم يتم إرجاعها)
    approved_first = len([c for c in custodies if c.get('audit_status') == 'approved' and not c.get('returned_count', 0)])
    returned = len([c for c in custodies if c.get('returned_count', 0) > 0])
    total_spent = sum(c.get('spent', 0) for c in custodies)
    
    score = (approved_first / len(custodies)) * 100 if custodies else 100
    
    return {
        "score": round(score, 1),
        "total_custodies": len(custodies),
        "approved_first_time": approved_first,
        "returned": returned,
        "total_spent": round(total_spent, 2)
    }


async def calculate_request_score(employee_id: str = None, month: str = None) -> dict:
    """
    حساب مؤشر انضباط الطلبات
    الصيغة: (المقبولة / الإجمالي) × 100
    """
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    
    if month:
        year, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(year, mon)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(2000)
    
    if not transactions:
        return {"score": 100, "total_requests": 0, "approved": 0, "rejected": 0, "pending": 0}
    
    approved = len([t for t in transactions if t.get('status') in ['approved', 'stas', 'completed']])
    rejected = len([t for t in transactions if t.get('status') in ['rejected', 'cancelled']])
    pending = len([t for t in transactions if t.get('status') not in ['approved', 'stas', 'completed', 'rejected', 'cancelled']])
    
    total_decided = approved + rejected
    score = (approved / total_decided) * 100 if total_decided > 0 else 100
    
    return {
        "score": round(score, 1),
        "total_requests": len(transactions),
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "approval_rate": round(score, 1)
    }


async def calculate_company_health_score(month: str = None) -> dict:
    """
    حساب مؤشر صحة الشركة
    المتوسط المرجح للمؤشرات الأربعة
    """
    attendance = await calculate_attendance_score(month=month)
    tasks = await calculate_task_score(month=month)
    financial = await calculate_financial_score(month=month)
    requests = await calculate_request_score(month=month)
    
    # الأوزان
    weights = {
        "attendance": 0.30,
        "tasks": 0.35,
        "financial": 0.20,
        "requests": 0.15
    }
    
    health_score = (
        attendance['score'] * weights['attendance'] +
        tasks['score'] * weights['tasks'] +
        financial['score'] * weights['financial'] +
        requests['score'] * weights['requests']
    )
    
    return {
        "health_score": round(health_score, 1),
        "attendance": attendance,
        "tasks": tasks,
        "financial": financial,
        "requests": requests,
        "weights": weights
    }


async def get_top_performers(limit: int = 5, month: str = None) -> list:
    """أفضل الموظفين أداءً"""
    employees = await db.employees.find({"status": "active"}, {"_id": 0, "id": 1, "full_name": 1, "department": 1}).to_list(100)
    
    results = []
    for emp in employees:
        attendance = await calculate_attendance_score(employee_id=emp['id'], month=month)
        tasks = await calculate_task_score(employee_id=emp['id'], month=month)
        
        overall = (attendance['score'] * 0.5) + (tasks['score'] * 0.5)
        
        results.append({
            "employee_id": emp['id'],
            "name": emp.get('full_name', 'N/A'),
            "department": emp.get('department', 'N/A'),
            "score": round(overall, 1),
            "attendance_score": attendance['score'],
            "task_score": tasks['score']
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]


async def get_bottom_performers(limit: int = 5, month: str = None) -> list:
    """الموظفون الذين يحتاجون متابعة"""
    top = await get_top_performers(limit=100, month=month)
    return sorted(top, key=lambda x: x['score'])[:limit]


async def get_monthly_trend(months: int = 6) -> list:
    """اتجاه الأداء الشهري"""
    now = datetime.now(timezone.utc)
    trends = []
    
    for i in range(months - 1, -1, -1):
        target_date = now - timedelta(days=30 * i)
        month_str = target_date.strftime("%Y-%m")
        
        health = await calculate_company_health_score(month=month_str)
        
        trends.append({
            "month": month_str,
            "month_name": target_date.strftime("%b %Y"),
            "health_score": health['health_score'],
            "attendance": health['attendance']['score'],
            "tasks": health['tasks']['score'],
            "financial": health['financial']['score'],
            "requests": health['requests']['score']
        })
    
    return trends


async def generate_executive_summary(health_data: dict, top_performers: list, bottom_performers: list) -> str:
    """توليد ملخص تنفيذي ذكي"""
    score = health_data['health_score']
    attendance = health_data['attendance']
    tasks = health_data['tasks']
    
    parts = []
    
    # تقييم عام
    if score >= 85:
        parts.append("مستوى الأداء العام ممتاز.")
    elif score >= 70:
        parts.append("مستوى الأداء العام جيد ومستقر.")
    elif score >= 50:
        parts.append("مستوى الأداء العام يحتاج تحسين.")
    else:
        parts.append("مستوى الأداء العام يتطلب تدخل عاجل.")
    
    # أفضل قسم
    if top_performers:
        top_dept = top_performers[0].get('department', '')
        if top_dept:
            parts.append(f"قسم {top_dept} الأعلى إنتاجية.")
    
    # تنبيهات
    if attendance['late_minutes'] > 500:
        parts.append("هناك ارتفاع ملحوظ في دقائق التأخير هذا الشهر.")
    
    if tasks.get('delayed', 0) > tasks.get('completed_on_time', 0):
        parts.append("نسبة تأخير المهام تتجاوز المقبول.")
    
    if attendance['absent_days'] > 10:
        parts.append("معدل الغياب يحتاج مراجعة.")
    
    return " ".join(parts)


# ==================== API ENDPOINTS ====================

@router.get("/executive/dashboard")
async def get_executive_dashboard(
    month: Optional[str] = None,
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed'))
):
    """
    لوحة المدير التنفيذي
    البيانات الكاملة للعرض
    """
    # الشهر الحالي إذا لم يُحدد
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    # حساب المؤشرات
    health_data = await calculate_company_health_score(month=month)
    
    # أفضل وأسوأ الموظفين
    top_performers = await get_top_performers(limit=5, month=month)
    bottom_performers = await get_bottom_performers(limit=5, month=month)
    
    # الاتجاه الشهري
    monthly_trend = await get_monthly_trend(months=6)
    
    # الملخص التنفيذي
    summary = await generate_executive_summary(health_data, top_performers, bottom_performers)
    
    # إحصائيات سريعة
    total_employees = await db.employees.count_documents({"status": "active"})
    pending_requests = await db.transactions.count_documents({"status": {"$nin": ["approved", "stas", "completed", "rejected", "cancelled"]}})
    open_custodies = await db.admin_custodies.count_documents({"status": {"$in": ["open", "pending_audit"]}})
    active_tasks = await db.tasks.count_documents({"status": {"$in": ["active", "pending"]}})
    
    return {
        "month": month,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health_score": health_data['health_score'],
        "metrics": {
            "attendance": health_data['attendance'],
            "tasks": health_data['tasks'],
            "financial": health_data['financial'],
            "requests": health_data['requests']
        },
        "top_performers": top_performers,
        "needs_attention": bottom_performers,
        "monthly_trend": monthly_trend,
        "executive_summary": summary,
        "quick_stats": {
            "total_employees": total_employees,
            "pending_requests": pending_requests,
            "open_custodies": open_custodies,
            "active_tasks": active_tasks
        }
    }


@router.get("/employee/{employee_id}/score")
async def get_employee_score(
    employee_id: str,
    month: Optional[str] = None,
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed', 'salah'))
):
    """
    درجة موظف محدد
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    attendance = await calculate_attendance_score(employee_id=employee_id, month=month)
    tasks = await calculate_task_score(employee_id=employee_id, month=month)
    financial = await calculate_financial_score(employee_id=employee_id, month=month)
    requests = await calculate_request_score(employee_id=employee_id, month=month)
    
    overall = (
        attendance['score'] * 0.30 +
        tasks['score'] * 0.35 +
        financial['score'] * 0.20 +
        requests['score'] * 0.15
    )
    
    # التوصيات
    recommendations = []
    if attendance['score'] < 70:
        recommendations.append("يحتاج تحسين في الالتزام بالحضور")
    if tasks['score'] < 70:
        recommendations.append("يحتاج متابعة في إنجاز المهام")
    if attendance['late_minutes'] > 100:
        recommendations.append("تأخر متكرر - يحتاج تنبيه")
    if overall >= 85:
        recommendations.append("موظف عالي الأداء - يستحق تقدير")
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.get('full_name'),
        "department": employee.get('department'),
        "month": month,
        "overall_score": round(overall, 1),
        "attendance": attendance,
        "tasks": tasks,
        "financial": financial,
        "requests": requests,
        "recommendations": recommendations
    }


@router.get("/alerts")
async def get_executive_alerts(
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed'))
):
    """
    تنبيهات تنفيذية
    """
    alerts = []
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    
    # طلبات معلقة أكثر من 3 أيام
    three_days_ago = (now - timedelta(days=3)).isoformat()
    old_pending = await db.transactions.count_documents({
        "status": {"$nin": ["approved", "stas", "completed", "rejected", "cancelled"]},
        "created_at": {"$lt": three_days_ago}
    })
    if old_pending > 0:
        alerts.append({
            "type": "warning",
            "title": "طلبات معلقة",
            "message": f"{old_pending} طلب معلق منذ أكثر من 3 أيام",
            "priority": "high"
        })
    
    # عهد بانتظار التدقيق
    pending_audit = await db.admin_custodies.count_documents({"status": "pending_audit"})
    if pending_audit > 0:
        alerts.append({
            "type": "info",
            "title": "عهد للتدقيق",
            "message": f"{pending_audit} عهدة بانتظار تدقيق المحاسب",
            "priority": "medium"
        })
    
    # موظفين غائبين اليوم
    absent_today = await db.daily_status.count_documents({
        "date": today,
        "final_status": "ABSENT"
    })
    if absent_today > 0:
        alerts.append({
            "type": "alert",
            "title": "غياب اليوم",
            "message": f"{absent_today} موظف غائب اليوم",
            "priority": "medium"
        })
    
    # مهام متأخرة
    overdue_tasks = await db.tasks.count_documents({
        "status": "active",
        "due_date": {"$lt": now.isoformat()}
    })
    if overdue_tasks > 0:
        alerts.append({
            "type": "warning",
            "title": "مهام متأخرة",
            "message": f"{overdue_tasks} مهمة تجاوزت موعد التسليم",
            "priority": "high"
        })
    
    return {"alerts": alerts, "count": len(alerts)}
