"""
Executive Analytics API
لوحة الحوكمة الذكية - المؤشرات التنفيذية
تعمل بشكل سنوي: من أول يوم في السنة إلى اليوم الحالي
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


def get_year_range(year: int = None):
    """
    الحصول على نطاق السنة
    من أول يوم في السنة إلى اليوم الحالي (أو آخر يوم إذا كانت سنة سابقة)
    """
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    
    start_date = f"{year}-01-01"
    
    if year == now.year:
        # السنة الحالية: من أول يوم إلى اليوم الحالي
        end_date = now.strftime("%Y-%m-%d")
    else:
        # سنة سابقة: من أول يوم إلى آخر يوم
        end_date = f"{year}-12-31"
    
    return start_date, end_date


async def calculate_attendance_score(employee_id: str = None, month: str = None, year: int = None, use_yearly: bool = False) -> dict:
    """
    حساب مؤشر الحضور
    الصيغة: (أيام الحضور / أيام العمل) × 100 - (دقائق التأخير × 0.05)
    
    use_yearly=True: يحسب من أول السنة إلى اليوم الحالي
    """
    now = datetime.now(timezone.utc)
    
    if use_yearly:
        # النطاق السنوي
        if year is None:
            year = now.year
        start_date, end_date = get_year_range(year)
    elif month:
        yr, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(yr, mon)
    else:
        yr, mon = now.year, now.month
        start_date, end_date = get_month_range(yr, mon)
    
    query = {"date": {"$gte": start_date, "$lte": end_date}}
    if employee_id:
        query["employee_id"] = employee_id
    
    records = await db.daily_status.find(query, {"_id": 0, "final_status": 1, "late_minutes": 1, "date": 1, "employee_id": 1}).to_list(10000)
    
    if not records:
        return {"score": 0, "present_days": 0, "work_days": 0, "late_minutes": 0, "absent_days": 0, "start_date": start_date, "end_date": end_date}
    
    # حساب الأيام
    present_statuses = ["PRESENT", "LATE", "LATE_EXCUSED", "EARLY_LEAVE", "EARLY_EXCUSED", "PERMISSION", "ON_MISSION"]
    work_statuses = present_statuses + ["ABSENT"]
    
    work_days = len([r for r in records if r.get('final_status') in work_statuses])
    present_days = len([r for r in records if r.get('final_status') in present_statuses])
    absent_days = len([r for r in records if r.get('final_status') == "ABSENT"])
    total_late_minutes = sum(r.get('late_minutes', 0) for r in records)
    
    if work_days == 0:
        return {"score": 0, "present_days": 0, "work_days": 0, "late_minutes": 0, "absent_days": 0, "no_data": True, "start_date": start_date, "end_date": end_date}
    
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


async def calculate_task_score(employee_id: str = None, month: str = None, year: int = None, use_yearly: bool = False) -> dict:
    """
    حساب مؤشر أداء المهام
    الصيغة: متوسط final_score × 20 (لتحويل من 5 إلى 100)
    """
    now = datetime.now(timezone.utc)
    query = {"status": "closed"}
    if employee_id:
        query["employee_id"] = employee_id
    
    if use_yearly:
        if year is None:
            year = now.year
        start_date, end_date = get_year_range(year)
        query["closed_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    elif month:
        yr, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(yr, mon)
        query["closed_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    tasks = await db.tasks.find(query, {"_id": 0, "final_score": 1, "delay_info": 1, "closed_at": 1, "employee_id": 1}).to_list(5000)
    
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


async def calculate_financial_score(employee_id: str = None, month: str = None, year: int = None, use_yearly: bool = False) -> dict:
    """
    حساب مؤشر الانضباط المالي
    الصيغة: (العهد المعتمدة من أول مرة / الإجمالي) × 100
    """
    now = datetime.now(timezone.utc)
    query = {"status": {"$in": ["approved", "executed", "closed"]}}
    if employee_id:
        query["created_by"] = employee_id
    
    if use_yearly:
        if year is None:
            year = now.year
        start_date, end_date = get_year_range(year)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    elif month:
        yr, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(yr, mon)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    custodies = await db.admin_custodies.find(query, {"_id": 0, "audit_status": 1, "returned_count": 1, "spent": 1, "created_by": 1, "created_at": 1}).to_list(2000)
    
    if not custodies:
        return {"score": 0, "total_custodies": 0, "approved_first_time": 0, "returned": 0, "total_spent": 0, "no_data": True}
    
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


async def calculate_request_score(employee_id: str = None, month: str = None, year: int = None, use_yearly: bool = False) -> dict:
    """
    حساب مؤشر انضباط الطلبات
    الصيغة: (المقبولة / الإجمالي) × 100
    """
    now = datetime.now(timezone.utc)
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    
    if use_yearly:
        if year is None:
            year = now.year
        start_date, end_date = get_year_range(year)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    elif month:
        yr, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(yr, mon)
        query["created_at"] = {"$gte": f"{start_date}T00:00:00", "$lte": f"{end_date}T23:59:59"}
    
    transactions = await db.transactions.find(query, {"_id": 0, "status": 1, "employee_id": 1, "created_at": 1}).to_list(5000)
    
    if not transactions:
        return {"score": 0, "total_requests": 0, "approved": 0, "rejected": 0, "pending": 0, "no_data": True}
    
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
    يعمل سنوياً من أول السنة إلى اليوم الحالي
    """
    now = datetime.now(timezone.utc)
    use_yearly = True  # دائماً سنوي للوحة الحوكمة
    year = now.year
    
    attendance = await calculate_attendance_score(year=year, use_yearly=use_yearly)
    tasks = await calculate_task_score(year=year, use_yearly=use_yearly)
    financial = await calculate_financial_score(year=year, use_yearly=use_yearly)
    requests = await calculate_request_score(year=year, use_yearly=use_yearly)
    
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
    
    # نطاق التقرير
    start_date, end_date = get_year_range(year)
    
    return {
        "health_score": round(health_score, 1),
        "attendance": attendance,
        "tasks": tasks,
        "financial": financial,
        "requests": requests,
        "weights": weights,
        "period": {
            "type": "yearly",
            "year": year,
            "start_date": start_date,
            "end_date": end_date
        }
    }


async def get_top_performers(limit: int = 5, month: str = None, year: int = None, use_yearly: bool = True) -> list:
    """أفضل الموظفين أداءً - باستثناء الإداريين"""
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
        
    employees = await db.employees.find(
        {"status": "active", "exclude_from_evaluation": {"$ne": True}}, 
        {"_id": 0, "id": 1, "full_name": 1, "full_name_ar": 1, "department": 1}
    ).to_list(100)
    
    results = []
    for emp in employees:
        attendance = await calculate_attendance_score(employee_id=emp['id'], year=year, use_yearly=use_yearly)
        tasks = await calculate_task_score(employee_id=emp['id'], year=year, use_yearly=use_yearly)
        excuses = await calculate_excuse_score(employee_id=emp['id'], year=year, use_yearly=use_yearly)
        
        # حساب شامل مع الأعذار
        overall = (attendance['score'] * 0.35) + (tasks['score'] * 0.40) + (excuses['score'] * 0.25)
        
        results.append({
            "employee_id": emp['id'],
            "name": emp.get('full_name_ar', emp.get('full_name', 'N/A')),
            "department": emp.get('department', 'N/A'),
            "score": round(overall, 1),
            "attendance_score": attendance['score'],
            "task_score": tasks['score'],
            "excuse_score": excuses['score'],
            "forget_checkin": excuses.get('forget_checkin', {}).get('count', 0),
            "late_excuse": excuses.get('late_excuse', {}).get('count', 0)
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)[:limit]


async def get_bottom_performers(limit: int = 5, month: str = None, year: int = None, use_yearly: bool = True) -> list:
    """الموظفون الذين يحتاجون متابعة"""
    top = await get_top_performers(limit=100, year=year, use_yearly=use_yearly)
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
    year: Optional[int] = None,
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed', 'salah'))
):
    """
    لوحة المدير التنفيذي - الحوكمة السنوية
    البيانات من أول يوم في السنة إلى اليوم الحالي
    """
    now = datetime.now(timezone.utc)
    if not year:
        year = now.year
    
    # نطاق السنة
    start_date, end_date = get_year_range(year)
    
    # حساب المؤشرات سنوياً
    health_data = await calculate_company_health_score()
    
    # أفضل وأسوأ الموظفين سنوياً
    top_performers = await get_top_performers(limit=5, year=year, use_yearly=True)
    bottom_performers = await get_bottom_performers(limit=5, year=year, use_yearly=True)
    
    # الاتجاه الشهري (آخر 12 شهر)
    monthly_trend = await get_monthly_trend(months=12)
    
    # الملخص التنفيذي
    summary = await generate_executive_summary(health_data, top_performers, bottom_performers)
    
    # إحصائيات سريعة
    total_employees = await db.employees.count_documents({"status": "active"})
    pending_requests = await db.transactions.count_documents({"status": {"$nin": ["approved", "stas", "completed", "rejected", "cancelled"]}})
    open_custodies = await db.admin_custodies.count_documents({"status": {"$in": ["open", "pending_audit"]}})
    active_tasks = await db.tasks.count_documents({"status": {"$in": ["active", "pending"]}})
    
    return {
        "year": year,
        "period": {
            "type": "yearly",
            "start_date": start_date,
            "end_date": end_date,
            "days_elapsed": (now - datetime(year, 1, 1, tzinfo=timezone.utc)).days + 1
        },
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



# ==================== AI SMART EVALUATION ====================

async def calculate_excuse_score(employee_id: str, month: str = None, year: int = None, use_yearly: bool = False) -> dict:
    """
    حساب مؤشر الأعذار والاستئذان
    - نسيان بصمة: الحد 3 مرات/شهر (أو 36 سنوياً)
    - تبرير تأخير: الحد 5 مرات/شهر (أو 60 سنوياً)
    - خروج مبكر: رصيد الساعات
    """
    now = datetime.now(timezone.utc)
    
    if use_yearly:
        if year is None:
            year = now.year
        start_date, end_date = get_year_range(year)
        # تعديل الحدود للسنة
        forget_limit = 36  # 3 × 12 شهر
        late_limit = 60    # 5 × 12 شهر
    elif month:
        yr, mon = int(month.split('-')[0]), int(month.split('-')[1])
        start_date, end_date = get_month_range(yr, mon)
        forget_limit = 3
        late_limit = 5
    else:
        yr, mon = now.year, now.month
        start_date, end_date = get_month_range(yr, mon)
        forget_limit = 3
        late_limit = 5
    
    # نسيان البصمة
    forget_count = await db.transactions.count_documents({
        "employee_id": employee_id,
        "type": "forget_checkin",
        "status": {"$nin": ["rejected", "cancelled"]},
        "data.date": {"$gte": start_date, "$lte": end_date}
    })
    
    # تبرير التأخير
    late_excuse_count = await db.transactions.count_documents({
        "employee_id": employee_id,
        "type": "late_excuse",
        "status": {"$nin": ["rejected", "cancelled"]},
        "data.date": {"$gte": start_date, "$lte": end_date}
    })
    
    # الخروج المبكر (بالدقائق)
    early_leaves = await db.transactions.find({
        "employee_id": employee_id,
        "type": {"$in": ["early_leave_request", "early_leave", "permission"]},
        "status": {"$nin": ["rejected", "cancelled"]},
        "data.date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "data": 1}).to_list(200)
    
    early_leave_minutes = 0
    for el in early_leaves:
        from_time = el.get('data', {}).get('from_time', '')
        to_time = el.get('data', {}).get('to_time', '')
        if from_time and to_time:
            try:
                f_parts = from_time.split(':')
                t_parts = to_time.split(':')
                f_mins = int(f_parts[0]) * 60 + int(f_parts[1])
                t_mins = int(t_parts[0]) * 60 + int(t_parts[1])
                early_leave_minutes += (t_mins - f_mins)
            except:
                pass
    
    # حساب الدرجة
    # نسيان بصمة: كل مرة تخصم نقاط حسب الحد
    forget_penalty = min((forget_count / forget_limit) * 30, 30) if forget_limit > 0 else 0
    # تبرير تأخير
    late_penalty = min((late_excuse_count / late_limit) * 30, 30) if late_limit > 0 else 0
    # خروج مبكر: كل 30 دقيقة تخصم 5 نقاط
    early_penalty = min((early_leave_minutes // 30) * 5, 40)
    
    total_penalty = forget_penalty + late_penalty + early_penalty
    
    # إذا لا يوجد أي استخدام للأعذار، الدرجة 0 (لم يبدأ التقييم بعد)
    if forget_count == 0 and late_excuse_count == 0 and early_leave_minutes == 0:
        score = 0
        no_data = True
    else:
        score = max(0, 100 - total_penalty)
        no_data = False
    
    return {
        "score": round(score, 1),
        "no_data": no_data,
        "forget_checkin": {
            "count": forget_count,
            "limit": forget_limit,
            "penalty": round(forget_penalty, 1)
        },
        "late_excuse": {
            "count": late_excuse_count,
            "limit": late_limit,
            "penalty": round(late_penalty, 1)
        },
        "early_leave": {
            "minutes": early_leave_minutes,
            "hours": round(early_leave_minutes / 60, 1),
            "penalty": round(early_penalty, 1)
        }
    }


async def calculate_ai_employee_score(employee_id: str, month: str = None, year: int = None, use_yearly: bool = True) -> dict:
    """
    التقييم الذكي الشامل للموظف
    يجمع كل المؤشرات مع تحليل AI
    يعمل سنوياً من أول السنة إلى اليوم الحالي
    """
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year
    
    # جمع كل المؤشرات سنوياً
    attendance = await calculate_attendance_score(employee_id=employee_id, year=year, use_yearly=use_yearly)
    tasks = await calculate_task_score(employee_id=employee_id, year=year, use_yearly=use_yearly)
    financial = await calculate_financial_score(employee_id=employee_id, year=year, use_yearly=use_yearly)
    requests = await calculate_request_score(employee_id=employee_id, year=year, use_yearly=use_yearly)
    excuses = await calculate_excuse_score(employee_id=employee_id, year=year, use_yearly=use_yearly)
    
    # التحقق من وجود بيانات
    has_attendance_data = not attendance.get('no_data', False) and attendance.get('work_days', 0) > 0
    has_task_data = not tasks.get('no_data', False) and tasks.get('total_tasks', 0) > 0
    has_financial_data = not financial.get('no_data', False) and financial.get('total_custodies', 0) > 0
    has_request_data = not requests.get('no_data', False) and requests.get('total_requests', 0) > 0
    has_excuse_data = not excuses.get('no_data', True)
    
    # إذا لا يوجد أي بيانات
    has_any_data = has_attendance_data or has_task_data or has_financial_data or has_request_data or has_excuse_data
    
    if not has_any_data:
        return {
            "overall_score": 0,
            "rating": {"label": "لم يبدأ التقييم", "label_en": "Not Started", "stars": 0, "color": "#6B7280"},
            "breakdown": {
                "attendance": {"score": 0, "weight": 0.25, "weighted_score": 0, "details": attendance, "has_data": False},
                "tasks": {"score": 0, "weight": 0.30, "weighted_score": 0, "details": tasks, "has_data": False},
                "excuses": {"score": 0, "weight": 0.20, "weighted_score": 0, "details": excuses, "has_data": False},
                "financial": {"score": 0, "weight": 0.15, "weighted_score": 0, "details": financial, "has_data": False},
                "requests": {"score": 0, "weight": 0.10, "weighted_score": 0, "details": requests, "has_data": False}
            },
            "strengths": [],
            "weaknesses": ["لم يبدأ التقييم بعد - في انتظار البيانات من 2026-02-27"],
            "recommendations": [{"type": "info", "text": "سيبدأ التقييم تلقائياً مع بدء تسجيل الحضور والمهام"}],
            "no_data": True
        }
    
    # الأوزان المُحدّثة (تُحسب فقط للمؤشرات التي بها بيانات)
    weights = {
        "attendance": 0.25 if has_attendance_data else 0,
        "tasks": 0.30 if has_task_data else 0,
        "excuses": 0.20 if has_excuse_data else 0,
        "financial": 0.15 if has_financial_data else 0,
        "requests": 0.10 if has_request_data else 0,
    }
    
    # تطبيع الأوزان
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v/total_weight for k, v in weights.items()}
    
    overall_score = (
        attendance['score'] * weights['attendance'] +
        tasks['score'] * weights['tasks'] +
        excuses['score'] * weights['excuses'] +
        financial['score'] * weights['financial'] +
        requests['score'] * weights['requests']
    )
    
    # تحديد التصنيف
    if overall_score >= 90:
        rating = {"label": "ممتاز", "label_en": "Excellent", "stars": 5, "color": "#10B981"}
    elif overall_score >= 80:
        rating = {"label": "جيد جداً", "label_en": "Very Good", "stars": 4, "color": "#3B82F6"}
    elif overall_score >= 70:
        rating = {"label": "جيد", "label_en": "Good", "stars": 3, "color": "#F59E0B"}
    elif overall_score >= 50:
        rating = {"label": "مقبول", "label_en": "Acceptable", "stars": 2, "color": "#F97316"}
    else:
        rating = {"label": "يحتاج تحسين", "label_en": "Needs Improvement", "stars": 1, "color": "#EF4444"}
    
    # نقاط القوة والضعف
    strengths = []
    weaknesses = []
    
    if attendance['score'] >= 85:
        strengths.append("ملتزم بالحضور والانصراف")
    elif attendance['score'] < 60:
        weaknesses.append("يحتاج تحسين في الحضور")
    
    if tasks['score'] >= 85:
        strengths.append("متميز في إنجاز المهام")
    elif tasks['score'] < 60:
        weaknesses.append("أداء المهام يحتاج متابعة")
    
    if excuses['score'] >= 85:
        strengths.append("قليل الأعذار والاستئذان")
    elif excuses['score'] < 60:
        weaknesses.append("كثير الأعذار والاستئذان")
    
    if excuses['forget_checkin']['count'] == 0:
        strengths.append("لم ينسَ البصمة هذا الشهر")
    elif excuses['forget_checkin']['count'] >= 3:
        weaknesses.append(f"نسيان بصمة متكرر ({excuses['forget_checkin']['count']} مرات)")
    
    if excuses['late_excuse']['count'] == 0:
        strengths.append("لم يبرر تأخير هذا الشهر")
    elif excuses['late_excuse']['count'] >= 4:
        weaknesses.append(f"تبرير تأخير متكرر ({excuses['late_excuse']['count']} مرات)")
    
    # التوصيات الذكية
    recommendations = []
    if attendance['late_minutes'] > 60:
        recommendations.append({
            "type": "warning",
            "text": f"تأخر إجمالي {attendance['late_minutes']} دقيقة - يُنصح بتحسين الالتزام بالمواعيد"
        })
    
    if excuses['early_leave']['minutes'] > 120:
        recommendations.append({
            "type": "info",
            "text": f"استخدم {excuses['early_leave']['hours']} ساعة استئذان - قريب من الحد الشهري"
        })
    
    if overall_score >= 85:
        recommendations.append({
            "type": "success",
            "text": "موظف عالي الأداء - يستحق التقدير والمكافأة"
        })
    
    if tasks.get('delayed', 0) > 2:
        recommendations.append({
            "type": "warning",
            "text": f"{tasks['delayed']} مهام متأخرة - يحتاج متابعة"
        })
    
    return {
        "overall_score": round(overall_score, 1),
        "rating": rating,
        "breakdown": {
            "attendance": {
                "score": attendance['score'],
                "weight": weights['attendance'],
                "weighted_score": round(attendance['score'] * weights['attendance'], 1),
                "details": attendance
            },
            "tasks": {
                "score": tasks['score'],
                "weight": weights['tasks'],
                "weighted_score": round(tasks['score'] * weights['tasks'], 1),
                "details": tasks
            },
            "excuses": {
                "score": excuses['score'],
                "weight": weights['excuses'],
                "weighted_score": round(excuses['score'] * weights['excuses'], 1),
                "details": excuses
            },
            "financial": {
                "score": financial['score'],
                "weight": weights['financial'],
                "weighted_score": round(financial['score'] * weights['financial'], 1),
                "details": financial
            },
            "requests": {
                "score": requests['score'],
                "weight": weights['requests'],
                "weighted_score": round(requests['score'] * weights['requests'], 1),
                "details": requests
            }
        },
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations
    }


@router.get("/ai/employee/{employee_id}")
async def get_ai_employee_evaluation(
    employee_id: str,
    month: Optional[str] = None,
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed', 'salah'))
):
    """
    التقييم الذكي للموظف بالذكاء الاصطناعي
    متاح لـ: سلطان، نايف، صلاح، محمد، ستاس
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    evaluation = await calculate_ai_employee_score(employee_id, month)
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.get('full_name_ar', employee.get('full_name', '')),
        "employee_number": employee.get('employee_number', ''),
        "department": employee.get('department', ''),
        "job_title": employee.get('job_title_ar', employee.get('job_title', '')),
        "month": month,
        "evaluation": evaluation,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ai/smart-monitor")
async def get_smart_monitor(
    year: Optional[int] = None,
    user=Depends(require_roles('stas', 'sultan', 'salah'))
):
    """
    المراقب الذكي - تقييم شامل لجميع الموظفين
    يعمل سنوياً: من أول يوم في السنة إلى اليوم الحالي
    متاح لـ: سلطان، صلاح، ستاس
    """
    now = datetime.now(timezone.utc)
    if not year:
        year = now.year
    
    start_date, end_date = get_year_range(year)
    
    # جلب الموظفين النشطين غير المستثنين من التقييم
    employees = await db.employees.find(
        {
            "status": "active",
            "exclude_from_evaluation": {"$ne": True}
        },
        {"_id": 0, "id": 1, "full_name_ar": 1, "full_name": 1, "employee_number": 1, "department": 1, "job_title_ar": 1}
    ).to_list(200)
    
    evaluations = []
    for emp in employees:
        try:
            eval_data = await calculate_ai_employee_score(emp['id'], year=year, use_yearly=True)
            evaluations.append({
                "employee_id": emp['id'],
                "employee_name": emp.get('full_name_ar', emp.get('full_name', '')),
                "employee_number": emp.get('employee_number', ''),
                "department": emp.get('department', ''),
                "overall_score": eval_data['overall_score'],
                "rating": eval_data['rating'],
                "attendance_score": eval_data['breakdown']['attendance']['score'],
                "tasks_score": eval_data['breakdown']['tasks']['score'],
                "excuses_score": eval_data['breakdown']['excuses']['score'],
                "forget_checkin_count": eval_data['breakdown']['excuses']['details']['forget_checkin']['count'],
                "late_excuse_count": eval_data['breakdown']['excuses']['details']['late_excuse']['count'],
                "early_leave_hours": eval_data['breakdown']['excuses']['details']['early_leave']['hours'],
                "strengths_count": len(eval_data['strengths']),
                "weaknesses_count": len(eval_data['weaknesses'])
            })
        except Exception as e:
            print(f"Error evaluating {emp['id']}: {e}")
            continue
    
    # ترتيب حسب الدرجة
    evaluations.sort(key=lambda x: x['overall_score'], reverse=True)
    
    # أفضل 5 موظفين
    top_performers = evaluations[:5] if len(evaluations) >= 5 else evaluations
    
    # أسوأ 5 موظفين
    bottom_performers = evaluations[-5:][::-1] if len(evaluations) >= 5 else evaluations[::-1]
    
    # إحصائيات عامة
    if evaluations:
        avg_score = sum(e['overall_score'] for e in evaluations) / len(evaluations)
        excellent_count = len([e for e in evaluations if e['overall_score'] >= 90])
        good_count = len([e for e in evaluations if 70 <= e['overall_score'] < 90])
        needs_improvement = len([e for e in evaluations if e['overall_score'] < 50])
    else:
        avg_score = 0
        excellent_count = good_count = needs_improvement = 0
    
    # تنبيهات المراقب الذكي (مُعدّلة للسنة)
    alerts = []
    
    # موظفين بنسيان بصمة عالي (أكثر من 6 مرات سنوياً = أكثر من مرة كل شهرين)
    high_forget = [e for e in evaluations if e['forget_checkin_count'] >= 6]
    if high_forget:
        alerts.append({
            "type": "warning",
            "title": "نسيان بصمة متكرر",
            "message": f"{len(high_forget)} موظف لديهم نسيان بصمة متكرر هذه السنة",
            "employees": [e['employee_name'] for e in high_forget[:3]]
        })
    
    # موظفين بتأخير متكرر (أكثر من 10 مرات سنوياً)
    high_late = [e for e in evaluations if e['late_excuse_count'] >= 10]
    if high_late:
        alerts.append({
            "type": "warning",
            "title": "تبرير تأخير متكرر",
            "message": f"{len(high_late)} موظف لديهم تبرير تأخير متكرر",
            "employees": [e['employee_name'] for e in high_late[:3]]
        })
    
    # موظفين ممتازين
    if excellent_count > 0:
        alerts.append({
            "type": "success",
            "title": "موظفين ممتازين",
            "message": f"{excellent_count} موظف حققوا درجة ممتازة (90+)",
            "employees": [e['employee_name'] for e in top_performers[:3]]
        })
    
    return {
        "year": year,
        "period": {
            "type": "yearly",
            "start_date": start_date,
            "end_date": end_date,
            "days_elapsed": (now - datetime(year, 1, 1, tzinfo=timezone.utc)).days + 1
        },
        "total_employees": len(evaluations),
        "company_average": round(avg_score, 1),
        "distribution": {
            "excellent": excellent_count,
            "good": good_count,
            "needs_improvement": needs_improvement
        },
        "top_performers": top_performers,
        "bottom_performers": bottom_performers,
        "all_evaluations": evaluations,
        "alerts": alerts,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ai/annual-evaluation/{employee_id}")
async def get_annual_evaluation(
    employee_id: str,
    year: Optional[int] = None,
    user=Depends(require_roles('stas', 'sultan', 'naif', 'mohammed', 'salah'))
):
    """
    التقييم السنوي للموظف
    يجمع بيانات كل الشهور للسنة
    """
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    if not year:
        year = datetime.now(timezone.utc).year
    
    monthly_evaluations = []
    for mon in range(1, 13):
        month_str = f"{year}-{mon:02d}"
        try:
            eval_data = await calculate_ai_employee_score(employee_id, month_str)
            monthly_evaluations.append({
                "month": month_str,
                "month_name": calendar.month_name[mon],
                "overall_score": eval_data['overall_score'],
                "attendance_score": eval_data['breakdown']['attendance']['score'],
                "tasks_score": eval_data['breakdown']['tasks']['score'],
                "excuses_score": eval_data['breakdown']['excuses']['score'],
                "forget_checkin_count": eval_data['breakdown']['excuses']['details']['forget_checkin']['count'],
                "late_excuse_count": eval_data['breakdown']['excuses']['details']['late_excuse']['count'],
            })
        except:
            continue
    
    # حساب المتوسط السنوي
    if monthly_evaluations:
        avg_score = sum(e['overall_score'] for e in monthly_evaluations) / len(monthly_evaluations)
        total_forget = sum(e['forget_checkin_count'] for e in monthly_evaluations)
        total_late_excuse = sum(e['late_excuse_count'] for e in monthly_evaluations)
    else:
        avg_score = 0
        total_forget = total_late_excuse = 0
    
    # تحديد التصنيف السنوي
    if avg_score >= 90:
        annual_rating = {"label": "ممتاز", "stars": 5, "color": "#10B981", "recommendation": "ترقية أو زيادة راتب"}
    elif avg_score >= 80:
        annual_rating = {"label": "جيد جداً", "stars": 4, "color": "#3B82F6", "recommendation": "مكافأة"}
    elif avg_score >= 70:
        annual_rating = {"label": "جيد", "stars": 3, "color": "#F59E0B", "recommendation": "تشجيع"}
    elif avg_score >= 50:
        annual_rating = {"label": "مقبول", "stars": 2, "color": "#F97316", "recommendation": "متابعة"}
    else:
        annual_rating = {"label": "يحتاج تحسين", "stars": 1, "color": "#EF4444", "recommendation": "إنذار"}
    
    # ملاحظات سنوية
    annual_notes = []
    if total_forget > 10:
        annual_notes.append(f"⚠️ نسيان البصمة متكرر: {total_forget} مرة خلال السنة")
    if total_late_excuse > 20:
        annual_notes.append(f"⚠️ تبرير التأخير متكرر: {total_late_excuse} مرة خلال السنة")
    if avg_score >= 85:
        annual_notes.append("✅ موظف متميز يستحق التقدير")
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.get('full_name_ar', employee.get('full_name', '')),
        "employee_number": employee.get('employee_number', ''),
        "year": year,
        "annual_score": round(avg_score, 1),
        "annual_rating": annual_rating,
        "monthly_evaluations": monthly_evaluations,
        "totals": {
            "forget_checkin": total_forget,
            "late_excuse": total_late_excuse,
            "months_evaluated": len(monthly_evaluations)
        },
        "annual_notes": annual_notes,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
