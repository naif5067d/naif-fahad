"""
Tasks System - نظام المهام
مرتبط بالتقييم السنوي للموظفين
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from database import db
from utils.auth import get_current_user, require_roles
import uuid

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# ==================== MODELS ====================

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    title_en: Optional[str] = None
    description: str = Field(..., min_length=10)
    description_en: Optional[str] = None
    employee_id: str
    due_date: str  # ISO format
    weight: int = Field(..., ge=1, le=100)  # الوزن التقييمي (1-100%)

class StageComplete(BaseModel):
    stage: int = Field(..., ge=1, le=4)  # 1, 2, 3, 4

class StageEvaluate(BaseModel):
    stage: int = Field(..., ge=1, le=4)
    rating: int = Field(..., ge=1, le=5)  # تقييم 1-5
    comment: Optional[str] = None

class TaskClose(BaseModel):
    final_comment: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================

def calculate_delay_penalty(due_date: str, completion_date: str) -> dict:
    """حساب غرامة التأخير"""
    due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
    completed = datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
    
    if completed <= due:
        return {"delayed": False, "days": 0, "penalty": 0}
    
    delay_days = (completed - due).days
    # خصم 5% لكل يوم تأخير بحد أقصى 25%
    penalty = min(delay_days * 5, 25)
    
    return {"delayed": True, "days": delay_days, "penalty": penalty}

def calculate_task_score(evaluations: list, delay_penalty: int) -> dict:
    """حساب درجة المهمة النهائية"""
    if not evaluations:
        return {"average": 0, "final_score": 0, "out_of": 5}
    
    total = sum(e.get('rating', 0) for e in evaluations)
    average = total / len(evaluations)
    
    # تطبيق غرامة التأخير
    penalty_factor = (100 - delay_penalty) / 100
    final_score = round(average * penalty_factor, 2)
    
    return {
        "average": round(average, 2),
        "delay_penalty": delay_penalty,
        "final_score": final_score,
        "out_of": 5
    }

async def send_task_notification(employee_id: str, title: str, message: str, type: str):
    """إرسال إشعار للموظف"""
    notification = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "title": title,
        "message": message,
        "type": type,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

# ==================== ENDPOINTS ====================

@router.post("/create")
async def create_task(
    task: TaskCreate,
    user=Depends(require_roles('sultan', 'naif', 'mohammed'))
):
    """
    إنشاء مهمة جديدة
    المخولين: نايف، سلطان، محمد
    """
    # التحقق من وجود الموظف
    employee = await db.employees.find_one({"id": task.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    new_task = {
        "id": str(uuid.uuid4()),
        "title": task.title,
        "title_en": task.title_en or task.title,
        "description": task.description,
        "description_en": task.description_en or task.description,
        "employee_id": task.employee_id,
        "employee_name": employee.get('full_name_ar', ''),
        "employee_name_en": employee.get('full_name', ''),
        "created_by": user.get('user_id'),
        "created_by_name": user.get('full_name', ''),
        "created_at": now,
        "due_date": task.due_date,
        "weight": task.weight,  # الوزن التقييمي
        "status": "active",  # active, pending_review, completed, closed
        "progress": 0,  # 0, 25, 50, 75, 100
        "current_stage": 0,  # 0-4
        "stages": [
            {"stage": 1, "completed": False, "completed_at": None, "evaluated": False, "rating": None, "comment": None},
            {"stage": 2, "completed": False, "completed_at": None, "evaluated": False, "rating": None, "comment": None},
            {"stage": 3, "completed": False, "completed_at": None, "evaluated": False, "rating": None, "comment": None},
            {"stage": 4, "completed": False, "completed_at": None, "evaluated": False, "rating": None, "comment": None},
        ],
        "delay_info": None,
        "final_score": None,
        "closed_at": None,
        "closed_by": None
    }
    
    await db.tasks.insert_one(new_task)
    new_task.pop('_id', None)
    
    # إشعار للموظف
    await send_task_notification(
        employee_id=task.employee_id,
        title="مهمة جديدة",
        message=f"تم تكليفك بمهمة: {task.title}",
        type="task_assigned"
    )
    
    return {
        "success": True,
        "message_ar": "تم إنشاء المهمة بنجاح",
        "message_en": "Task created successfully",
        "task": new_task
    }


@router.get("/my-tasks")
async def get_my_tasks(user=Depends(get_current_user)):
    """جلب مهام الموظف الحالي"""
    employee_id = user.get('employee_id')
    if not employee_id:
        return []
    
    tasks = await db.tasks.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return tasks


@router.get("/all")
async def get_all_tasks(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(require_roles('sultan', 'naif', 'mohammed', 'stas'))
):
    """جلب جميع المهام (للإدارة)"""
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return tasks


@router.get("/{task_id}")
async def get_task(task_id: str, user=Depends(get_current_user)):
    """جلب تفاصيل مهمة"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    # التحقق من الصلاحية
    role = user.get('role', '')
    employee_id = user.get('employee_id', '')
    
    if role not in ['sultan', 'naif', 'mohammed', 'stas'] and task['employee_id'] != employee_id:
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    return task


@router.post("/{task_id}/complete-stage")
async def complete_stage(
    task_id: str,
    data: StageComplete,
    user=Depends(get_current_user)
):
    """
    الموظف يُنهي مرحلة (25%)
    """
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    # التحقق أن الموظف هو صاحب المهمة
    if task['employee_id'] != user.get('employee_id'):
        raise HTTPException(status_code=403, detail="هذه ليست مهمتك")
    
    if task['status'] == 'closed':
        raise HTTPException(status_code=400, detail="المهمة مغلقة")
    
    stage_index = data.stage - 1
    stages = task.get('stages', [])
    
    # التحقق أن المرحلة السابقة مكتملة ومُقيّمة
    if data.stage > 1:
        prev_stage = stages[stage_index - 1]
        if not prev_stage.get('completed') or not prev_stage.get('evaluated'):
            raise HTTPException(
                status_code=400, 
                detail="يجب إكمال وتقييم المرحلة السابقة أولاً"
            )
    
    # التحقق أن المرحلة لم تُكمل بعد
    if stages[stage_index].get('completed'):
        raise HTTPException(status_code=400, detail="المرحلة مكتملة مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # تحديث المرحلة
    stages[stage_index]['completed'] = True
    stages[stage_index]['completed_at'] = now
    
    new_progress = data.stage * 25
    new_status = "pending_review"  # بانتظار تقييم المدير
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "stages": stages,
            "progress": new_progress,
            "current_stage": data.stage,
            "status": new_status
        }}
    )
    
    # إشعار للمدير الذي أنشأ المهمة
    await send_task_notification(
        employee_id=task['created_by'],
        title="مرحلة بانتظار التقييم",
        message=f"الموظف {task['employee_name']} أنهى المرحلة {data.stage} من مهمة: {task['title']}",
        type="stage_pending_review"
    )
    
    return {
        "success": True,
        "message_ar": f"تم إنهاء المرحلة {data.stage} بنجاح، بانتظار تقييم المدير",
        "message_en": f"Stage {data.stage} completed, awaiting manager review",
        "progress": new_progress
    }


@router.post("/{task_id}/evaluate-stage")
async def evaluate_stage(
    task_id: str,
    data: StageEvaluate,
    user=Depends(require_roles('sultan', 'naif', 'mohammed'))
):
    """
    المدير يُقيّم مرحلة (1-5)
    """
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    stage_index = data.stage - 1
    stages = task.get('stages', [])
    
    # التحقق أن المرحلة مكتملة
    if not stages[stage_index].get('completed'):
        raise HTTPException(status_code=400, detail="المرحلة لم تُكمل بعد")
    
    # التحقق أن المرحلة لم تُقيّم بعد
    if stages[stage_index].get('evaluated'):
        raise HTTPException(status_code=400, detail="المرحلة مُقيّمة مسبقاً")
    
    # تحديث التقييم
    stages[stage_index]['evaluated'] = True
    stages[stage_index]['rating'] = data.rating
    stages[stage_index]['comment'] = data.comment
    stages[stage_index]['evaluated_by'] = user.get('user_id')
    stages[stage_index]['evaluated_at'] = datetime.now(timezone.utc).isoformat()
    
    # تحديد الحالة الجديدة
    new_status = "active"
    if task['progress'] == 100 and all(s.get('evaluated') for s in stages):
        new_status = "completed"
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "stages": stages,
            "status": new_status
        }}
    )
    
    # إشعار للموظف
    rating_text = "⭐" * data.rating
    await send_task_notification(
        employee_id=task['employee_id'],
        title="تم تقييم مرحلتك",
        message=f"المرحلة {data.stage} من مهمة '{task['title']}' حصلت على: {rating_text}",
        type="stage_evaluated"
    )
    
    return {
        "success": True,
        "message_ar": f"تم تقييم المرحلة {data.stage} بنجاح",
        "message_en": f"Stage {data.stage} evaluated successfully",
        "rating": data.rating
    }


@router.post("/{task_id}/close")
async def close_task(
    task_id: str,
    data: TaskClose,
    user=Depends(require_roles('sultan', 'naif', 'mohammed'))
):
    """
    المدير يُغلق المهمة (استلام نهائي)
    يحسب الدرجة النهائية ويُسجلها في سجل الموظف
    """
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    if task['status'] == 'closed':
        raise HTTPException(status_code=400, detail="المهمة مغلقة مسبقاً")
    
    if task['progress'] < 100:
        raise HTTPException(status_code=400, detail="المهمة لم تكتمل بعد")
    
    stages = task.get('stages', [])
    if not all(s.get('evaluated') for s in stages):
        raise HTTPException(status_code=400, detail="يجب تقييم جميع المراحل أولاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # حساب التأخير
    delay_info = calculate_delay_penalty(task['due_date'], now)
    
    # حساب الدرجة النهائية
    evaluations = [{"rating": s.get('rating', 0)} for s in stages if s.get('evaluated')]
    score_info = calculate_task_score(evaluations, delay_info['penalty'])
    
    # تحديث المهمة
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "status": "closed",
            "delay_info": delay_info,
            "final_score": score_info,
            "closed_at": now,
            "closed_by": user.get('user_id'),
            "close_comment": data.final_comment
        }}
    )
    
    # تسجيل في سجل تقييمات الموظف
    evaluation_record = {
        "id": str(uuid.uuid4()),
        "employee_id": task['employee_id'],
        "task_id": task_id,
        "task_title": task['title'],
        "weight": task['weight'],
        "final_score": score_info['final_score'],
        "out_of": 5,
        "delay_days": delay_info['days'],
        "delay_penalty": delay_info['penalty'],
        "year": datetime.now().year,
        "created_at": now,
        "created_by": user.get('user_id')
    }
    await db.employee_task_evaluations.insert_one(evaluation_record)
    
    # إشعار للموظف
    await send_task_notification(
        employee_id=task['employee_id'],
        title="تم إغلاق المهمة",
        message=f"مهمة '{task['title']}' أُغلقت بدرجة {score_info['final_score']}/5",
        type="task_closed"
    )
    
    return {
        "success": True,
        "message_ar": "تم إغلاق المهمة وتسجيل التقييم",
        "message_en": "Task closed and evaluation recorded",
        "final_score": score_info,
        "delay_info": delay_info,
        "weight_info": {
            "weight": task['weight'],
            "message_ar": f"هذه المهمة تمثل {task['weight']}% من معيار إنجاز المهام في التقييم السنوي",
            "message_en": f"This task represents {task['weight']}% of the task completion criteria in annual evaluation"
        }
    }


@router.get("/employee/{employee_id}/annual-summary")
async def get_employee_annual_summary(
    employee_id: str,
    year: Optional[int] = None,
    user=Depends(require_roles('sultan', 'naif', 'mohammed', 'stas'))
):
    """
    ملخص تقييم المهام السنوي للموظف
    """
    if not year:
        year = datetime.now().year
    
    evaluations = await db.employee_task_evaluations.find(
        {"employee_id": employee_id, "year": year},
        {"_id": 0}
    ).to_list(100)
    
    if not evaluations:
        return {
            "employee_id": employee_id,
            "year": year,
            "total_tasks": 0,
            "average_score": 0,
            "weighted_score": 0,
            "total_weight": 0,
            "evaluations": []
        }
    
    # حساب المتوسط الموزون
    total_weight = sum(e.get('weight', 0) for e in evaluations)
    weighted_sum = sum(e.get('final_score', 0) * e.get('weight', 0) for e in evaluations)
    weighted_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0
    
    # المتوسط البسيط
    avg_score = round(sum(e.get('final_score', 0) for e in evaluations) / len(evaluations), 2)
    
    return {
        "employee_id": employee_id,
        "year": year,
        "total_tasks": len(evaluations),
        "average_score": avg_score,
        "weighted_score": weighted_score,
        "total_weight": total_weight,
        "out_of": 5,
        "evaluations": evaluations
    }


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """حذف مهمة (فقط إذا لم تبدأ)"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="المهمة غير موجودة")
    
    if task['progress'] > 0:
        raise HTTPException(status_code=400, detail="لا يمكن حذف مهمة بدأ العمل عليها")
    
    await db.tasks.delete_one({"id": task_id})
    
    return {
        "success": True,
        "message_ar": "تم حذف المهمة",
        "message_en": "Task deleted"
    }
