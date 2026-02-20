"""
Performance Review System - نظام تقييم الأداء السنوي
=====================================================

يربط بين:
- الحضور والانصراف (attendance)
- العقوبات والخصومات (penalties, deductions)
- المهام (tasks)
- الإنذارات (warnings)

التقييم يُنشئ سنوياً لكل موظف ويُراجع من سلطان
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/performance", tags=["Performance Review"])


# ============================================================
# MODELS
# ============================================================

class PerformanceCategory:
    ATTENDANCE = "attendance"  # الحضور والالتزام
    TASKS = "tasks"  # إنجاز المهام
    BEHAVIOR = "behavior"  # السلوك والانضباط
    SKILLS = "skills"  # المهارات والتطوير
    TEAMWORK = "teamwork"  # العمل الجماعي


class ManualRatingInput(BaseModel):
    """تقييم يدوي من المشرف/المدير"""
    skills_rating: Optional[int] = None  # 1-5
    teamwork_rating: Optional[int] = None  # 1-5
    notes: Optional[str] = ""
    strengths: Optional[List[str]] = []
    improvements: Optional[List[str]] = []


class FinalReviewInput(BaseModel):
    """مراجعة نهائية من سلطان"""
    final_rating: int  # 1-5
    final_notes: str
    recommendations: Optional[str] = ""  # ترقية، تدريب، إنذار، إلخ


# ============================================================
# RATING SCALE
# ============================================================

RATING_SCALE = {
    5: {"ar": "ممتاز", "en": "Excellent", "color": "emerald"},
    4: {"ar": "جيد جداً", "en": "Very Good", "color": "blue"},
    3: {"ar": "جيد", "en": "Good", "color": "amber"},
    2: {"ar": "مقبول", "en": "Acceptable", "color": "orange"},
    1: {"ar": "ضعيف", "en": "Poor", "color": "red"}
}


# ============================================================
# CALCULATE AUTO SCORES
# ============================================================

async def calculate_attendance_score(employee_id: str, year: str) -> dict:
    """حساب درجة الحضور من البيانات الفعلية"""
    
    # جلب بيانات الحضور للسنة
    daily_records = await db.daily_status.find({
        "employee_id": employee_id,
        "date": {"$regex": f"^{year}"}
    }, {"_id": 0}).to_list(400)
    
    total_days = len(daily_records)
    if total_days == 0:
        return {"score": 0, "details": {}, "raw_score": 0}
    
    present = sum(1 for r in daily_records if r.get('final_status') == 'PRESENT')
    late = sum(1 for r in daily_records if r.get('final_status') == 'LATE')
    absent = sum(1 for r in daily_records if r.get('final_status') == 'ABSENT')
    on_leave = sum(1 for r in daily_records if r.get('final_status') in ['ON_LEAVE', 'ON_ADMIN_LEAVE'])
    
    # حساب النسبة (الحضور + الإجازات المعتمدة)
    attendance_rate = (present + on_leave) / total_days if total_days > 0 else 0
    late_rate = late / total_days if total_days > 0 else 0
    
    # تحويل النسبة لدرجة 1-5
    if attendance_rate >= 0.98 and late_rate < 0.02:
        score = 5
    elif attendance_rate >= 0.95 and late_rate < 0.05:
        score = 4
    elif attendance_rate >= 0.90 and late_rate < 0.10:
        score = 3
    elif attendance_rate >= 0.80:
        score = 2
    else:
        score = 1
    
    return {
        "score": score,
        "raw_score": round(attendance_rate * 100, 1),
        "details": {
            "total_days": total_days,
            "present": present,
            "late": late,
            "absent": absent,
            "on_leave": on_leave,
            "attendance_rate": round(attendance_rate * 100, 1),
            "late_rate": round(late_rate * 100, 1)
        }
    }


async def calculate_tasks_score(employee_id: str, year: str) -> dict:
    """حساب درجة المهام من البيانات الفعلية"""
    
    # جلب المهام للسنة
    tasks = await db.tasks.find({
        "employee_id": employee_id,
        "created_at": {"$regex": f"^{year}"}
    }, {"_id": 0}).to_list(500)
    
    total_tasks = len(tasks)
    if total_tasks == 0:
        return {"score": 3, "details": {}, "raw_score": 0}  # افتراضي متوسط
    
    completed = sum(1 for t in tasks if t.get('status') == 'completed')
    on_time = sum(1 for t in tasks if t.get('status') == 'completed' and not t.get('is_overdue'))
    overdue = sum(1 for t in tasks if t.get('is_overdue'))
    
    completion_rate = completed / total_tasks if total_tasks > 0 else 0
    on_time_rate = on_time / completed if completed > 0 else 0
    
    # حساب الدرجة
    combined_rate = (completion_rate * 0.6) + (on_time_rate * 0.4)
    
    if combined_rate >= 0.95:
        score = 5
    elif combined_rate >= 0.85:
        score = 4
    elif combined_rate >= 0.70:
        score = 3
    elif combined_rate >= 0.50:
        score = 2
    else:
        score = 1
    
    return {
        "score": score,
        "raw_score": round(combined_rate * 100, 1),
        "details": {
            "total_tasks": total_tasks,
            "completed": completed,
            "on_time": on_time,
            "overdue": overdue,
            "completion_rate": round(completion_rate * 100, 1),
            "on_time_rate": round(on_time_rate * 100, 1)
        }
    }


async def calculate_behavior_score(employee_id: str, year: str) -> dict:
    """حساب درجة السلوك من الإنذارات والعقوبات"""
    
    # جلب الإنذارات
    warnings = await db.warnings.find({
        "employee_id": employee_id,
        "created_at": {"$regex": f"^{year}"}
    }, {"_id": 0}).to_list(50)
    
    # جلب الخصومات السلوكية
    deductions = await db.finance_ledger.find({
        "employee_id": employee_id,
        "date": {"$regex": f"^{year}"},
        "category": {"$in": ["penalty", "deduction"]}
    }, {"_id": 0}).to_list(100)
    
    warning_count = len(warnings)
    deduction_count = len(deductions)
    total_deduction_amount = sum(d.get('amount', 0) for d in deductions)
    
    # حساب الدرجة (كلما قل عدد الإنذارات والخصومات زادت الدرجة)
    if warning_count == 0 and deduction_count == 0:
        score = 5
    elif warning_count <= 1 and deduction_count <= 2:
        score = 4
    elif warning_count <= 2 and deduction_count <= 5:
        score = 3
    elif warning_count <= 3:
        score = 2
    else:
        score = 1
    
    return {
        "score": score,
        "raw_score": max(0, 100 - (warning_count * 15) - (deduction_count * 5)),
        "details": {
            "warning_count": warning_count,
            "deduction_count": deduction_count,
            "total_deduction_amount": total_deduction_amount,
            "warnings": [{"level": w.get('level'), "reason": w.get('reason_ar')} for w in warnings]
        }
    }


# ============================================================
# GENERATE ANNUAL REVIEW
# ============================================================

@router.post("/generate/{employee_id}")
async def generate_annual_review(
    employee_id: str,
    year: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    إنشاء تقييم أداء سنوي للموظف
    
    يجمع البيانات تلقائياً من:
    - الحضور والانصراف
    - المهام
    - الإنذارات والعقوبات
    """
    # التحقق من وجود الموظف
    emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من عدم وجود تقييم سابق للسنة
    existing = await db.performance_reviews.find_one({
        "employee_id": employee_id,
        "year": year
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"يوجد تقييم سابق للسنة {year}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # حساب الدرجات التلقائية
    attendance = await calculate_attendance_score(employee_id, year)
    tasks = await calculate_tasks_score(employee_id, year)
    behavior = await calculate_behavior_score(employee_id, year)
    
    # الدرجات اليدوية (افتراضية)
    skills = {"score": 3, "details": {}, "raw_score": 0}
    teamwork = {"score": 3, "details": {}, "raw_score": 0}
    
    # حساب المتوسط
    auto_average = (attendance['score'] + tasks['score'] + behavior['score']) / 3
    
    review = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name": emp.get('full_name', ''),
        "employee_name_ar": emp.get('full_name_ar', ''),
        "department": emp.get('department', ''),
        "job_title_ar": emp.get('job_title_ar', ''),
        "year": year,
        "status": "draft",  # draft, pending_review, approved
        
        # الدرجات التلقائية
        "scores": {
            "attendance": attendance,
            "tasks": tasks,
            "behavior": behavior,
            "skills": skills,  # يُملأ يدوياً
            "teamwork": teamwork  # يُملأ يدوياً
        },
        
        # الملخص
        "auto_average": round(auto_average, 2),
        "final_rating": None,  # يُحدد من سلطان
        "final_rating_ar": None,
        
        # الملاحظات
        "supervisor_notes": "",
        "strengths": [],
        "improvements": [],
        "recommendations": "",
        
        # التتبع
        "created_at": now,
        "created_by": user['user_id'],
        "updated_at": now,
        "reviewed_at": None,
        "reviewed_by": None
    }
    
    await db.performance_reviews.insert_one(review)
    review.pop('_id', None)
    
    return {
        "success": True,
        "message": f"تم إنشاء تقييم الأداء للموظف {emp.get('full_name_ar', '')} لسنة {year}",
        "review": review
    }


# ============================================================
# UPDATE MANUAL SCORES
# ============================================================

@router.put("/{review_id}/manual-scores")
async def update_manual_scores(
    review_id: str,
    body: ManualRatingInput,
    user=Depends(require_roles('sultan', 'naif', 'supervisor'))
):
    """تحديث الدرجات اليدوية (المهارات، العمل الجماعي)"""
    
    review = await db.performance_reviews.find_one({"id": review_id}, {"_id": 0})
    if not review:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    if review['status'] == 'approved':
        raise HTTPException(status_code=400, detail="لا يمكن تعديل تقييم معتمد")
    
    now = datetime.now(timezone.utc).isoformat()
    
    updates = {"updated_at": now}
    
    if body.skills_rating:
        updates["scores.skills.score"] = body.skills_rating
        updates["scores.skills.raw_score"] = body.skills_rating * 20
    
    if body.teamwork_rating:
        updates["scores.teamwork.score"] = body.teamwork_rating
        updates["scores.teamwork.raw_score"] = body.teamwork_rating * 20
    
    if body.notes:
        updates["supervisor_notes"] = body.notes
    
    if body.strengths:
        updates["strengths"] = body.strengths
    
    if body.improvements:
        updates["improvements"] = body.improvements
    
    # إعادة حساب المتوسط
    scores = review['scores']
    if body.skills_rating:
        scores['skills']['score'] = body.skills_rating
    if body.teamwork_rating:
        scores['teamwork']['score'] = body.teamwork_rating
    
    all_scores = [
        scores['attendance']['score'],
        scores['tasks']['score'],
        scores['behavior']['score'],
        scores['skills']['score'],
        scores['teamwork']['score']
    ]
    updates["auto_average"] = round(sum(all_scores) / len(all_scores), 2)
    updates["status"] = "pending_review"
    
    await db.performance_reviews.update_one(
        {"id": review_id},
        {"$set": updates}
    )
    
    return {"success": True, "message": "تم تحديث التقييم"}


# ============================================================
# FINAL REVIEW (SULTAN ONLY)
# ============================================================

@router.put("/{review_id}/approve")
async def approve_review(
    review_id: str,
    body: FinalReviewInput,
    user=Depends(require_roles('sultan'))
):
    """اعتماد التقييم النهائي - سلطان فقط"""
    
    review = await db.performance_reviews.find_one({"id": review_id}, {"_id": 0})
    if not review:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    if review['status'] == 'approved':
        raise HTTPException(status_code=400, detail="التقييم معتمد مسبقاً")
    
    if body.final_rating < 1 or body.final_rating > 5:
        raise HTTPException(status_code=400, detail="الدرجة يجب أن تكون بين 1 و 5")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.performance_reviews.update_one(
        {"id": review_id},
        {"$set": {
            "status": "approved",
            "final_rating": body.final_rating,
            "final_rating_ar": RATING_SCALE[body.final_rating]['ar'],
            "final_notes": body.final_notes,
            "recommendations": body.recommendations,
            "reviewed_at": now,
            "reviewed_by": user['user_id'],
            "reviewed_by_name": user.get('full_name_ar', user.get('full_name', ''))
        }}
    )
    
    # حفظ في أرشيف STAS
    archive_entry = {
        "id": str(uuid.uuid4()),
        "year": review['year'],
        "type": "performance_review",
        "review_id": review_id,
        "employee_id": review['employee_id'],
        "employee_name_ar": review['employee_name_ar'],
        "final_rating": body.final_rating,
        "final_rating_ar": RATING_SCALE[body.final_rating]['ar'],
        "recommendations": body.recommendations,
        "approved_by": user['user_id'],
        "approved_by_name": user.get('full_name_ar', ''),
        "approved_at": now,
        "archived_at": now
    }
    await db.stas_annual_archive.insert_one(archive_entry)
    
    # إرسال إشعار للموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        await create_notification(
            recipient_id=review['employee_id'],
            notification_type=NotificationType.INFO,
            title="Annual Performance Review",
            title_ar="تقييم الأداء السنوي",
            message=f"Your {review['year']} performance review has been approved",
            message_ar=f"تم اعتماد تقييم أدائك لسنة {review['year']} - التقدير: {RATING_SCALE[body.final_rating]['ar']}",
            priority=NotificationPriority.HIGH,
            recipient_role="employee",
            reference_type="performance_review",
            reference_id=review_id
        )
    except Exception:
        pass
    
    return {
        "success": True,
        "message": f"تم اعتماد التقييم - {RATING_SCALE[body.final_rating]['ar']}",
        "final_rating": body.final_rating,
        "final_rating_ar": RATING_SCALE[body.final_rating]['ar']
    }


# ============================================================
# GET REVIEWS
# ============================================================

@router.get("/list")
async def get_reviews(
    year: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """جلب جميع التقييمات"""
    
    query = {}
    if year:
        query["year"] = year
    if status:
        query["status"] = status
    
    reviews = await db.performance_reviews.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    # إحصائيات
    total = len(reviews)
    draft = sum(1 for r in reviews if r.get('status') == 'draft')
    pending = sum(1 for r in reviews if r.get('status') == 'pending_review')
    approved = sum(1 for r in reviews if r.get('status') == 'approved')
    
    return {
        "stats": {
            "total": total,
            "draft": draft,
            "pending_review": pending,
            "approved": approved
        },
        "reviews": reviews
    }


@router.get("/employee/{employee_id}")
async def get_employee_reviews(
    employee_id: str,
    user=Depends(get_current_user)
):
    """جلب تقييمات موظف معين"""
    
    # الموظف يرى تقييماته فقط، الإدارة ترى الجميع
    if user.get('role') == 'employee' and user.get('employee_id') != employee_id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    reviews = await db.performance_reviews.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("year", -1).to_list(20)
    
    return reviews


@router.get("/{review_id}")
async def get_review(
    review_id: str,
    user=Depends(get_current_user)
):
    """جلب تقييم محدد"""
    
    review = await db.performance_reviews.find_one(
        {"id": review_id},
        {"_id": 0}
    )
    
    if not review:
        raise HTTPException(status_code=404, detail="التقييم غير موجود")
    
    # الموظف يرى تقييمه فقط
    if user.get('role') == 'employee' and user.get('employee_id') != review['employee_id']:
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    return review


# ============================================================
# GENERATE BULK REVIEWS
# ============================================================

@router.post("/generate-all")
async def generate_all_reviews(
    year: str,
    user=Depends(require_roles('stas'))
):
    """إنشاء تقييمات لجميع الموظفين - STAS فقط"""
    
    # جلب جميع الموظفين النشطين
    EXEMPT_IDS = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-004', 'EMP-NAIF']
    
    employees = await db.employees.find({
        "is_active": {"$ne": False},
        "id": {"$nin": EXEMPT_IDS}
    }, {"_id": 0, "id": 1, "full_name_ar": 1}).to_list(500)
    
    created = 0
    skipped = 0
    errors = []
    
    for emp in employees:
        try:
            # التحقق من وجود تقييم سابق
            existing = await db.performance_reviews.find_one({
                "employee_id": emp['id'],
                "year": year
            })
            
            if existing:
                skipped += 1
                continue
            
            # إنشاء التقييم
            attendance = await calculate_attendance_score(emp['id'], year)
            tasks = await calculate_tasks_score(emp['id'], year)
            behavior = await calculate_behavior_score(emp['id'], year)
            
            auto_average = (attendance['score'] + tasks['score'] + behavior['score']) / 3
            
            now = datetime.now(timezone.utc).isoformat()
            
            review = {
                "id": str(uuid.uuid4()),
                "employee_id": emp['id'],
                "employee_name_ar": emp.get('full_name_ar', ''),
                "year": year,
                "status": "draft",
                "scores": {
                    "attendance": attendance,
                    "tasks": tasks,
                    "behavior": behavior,
                    "skills": {"score": 3, "details": {}, "raw_score": 0},
                    "teamwork": {"score": 3, "details": {}, "raw_score": 0}
                },
                "auto_average": round(auto_average, 2),
                "final_rating": None,
                "created_at": now,
                "created_by": user['user_id']
            }
            
            await db.performance_reviews.insert_one(review)
            created += 1
            
        except Exception as e:
            errors.append({"employee_id": emp['id'], "error": str(e)})
    
    return {
        "success": True,
        "message": f"تم إنشاء {created} تقييم لسنة {year}",
        "created": created,
        "skipped": skipped,
        "errors": errors
    }
