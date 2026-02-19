"""
User Management Routes - For STAS to manage employee credentials
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles, hash_password
from datetime import datetime, timezone

router = APIRouter(prefix="/api/users", tags=["users"])


class UserCredentialsUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None


class UserCreate(BaseModel):
    employee_id: str
    username: str
    password: str


@router.get("")
async def list_users(user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """
    قائمة جميع المستخدمين مع بيانات الدخول (بدون كلمات المرور)
    """
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return users


@router.get("/{employee_id}")
async def get_user_by_employee(employee_id: str, user=Depends(require_roles('stas', 'sultan', 'naif'))):
    """
    الحصول على بيانات المستخدم بناءً على employee_id
    كلمة المرور لا تُعرض أبداً - للأمان
    """
    user_data = await db.users.find_one(
        {"employee_id": employee_id}, 
        {"_id": 0, "password_hash": 0, "plain_password": 0}
    )
    
    if not user_data:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return user_data


@router.put("/{employee_id}/credentials")
async def update_user_credentials(
    employee_id: str,
    update: UserCredentialsUpdate,
    user=Depends(require_roles('stas'))
):
    """
    تحديث اليوزر نيم أو كلمة المرور للموظف
    STAS فقط
    """
    existing = await db.users.find_one({"employee_id": employee_id})
    if not existing:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if update.username:
        # التحقق من عدم تكرار اليوزر نيم
        username_exists = await db.users.find_one({
            "username": update.username,
            "employee_id": {"$ne": employee_id}
        })
        if username_exists:
            raise HTTPException(status_code=400, detail="اسم المستخدم موجود مسبقاً")
        updates["username"] = update.username
    
    if update.password:
        if len(update.password) < 6:
            raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        updates["password_hash"] = hash_password(update.password)
        # إزالة كلمة المرور النصية إن وجدت (للأمان)
        updates["plain_password"] = None
    
    await db.users.update_one({"employee_id": employee_id}, {"$set": updates})
    
    updated = await db.users.find_one({"employee_id": employee_id}, {"_id": 0, "password_hash": 0})
    return {
        "message": "تم تحديث بيانات الدخول بنجاح",
        "user": updated
    }


@router.post("/create")
async def create_user_for_employee(
    data: UserCreate,
    user=Depends(require_roles('stas'))
):
    """
    إنشاء مستخدم جديد لموظف
    """
    # التحقق من وجود الموظف
    employee = await db.employees.find_one({"id": data.employee_id})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # التحقق من عدم وجود مستخدم مسبقاً
    existing_user = await db.users.find_one({"employee_id": data.employee_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="يوجد مستخدم مسبقاً لهذا الموظف")
    
    # التحقق من عدم تكرار اليوزر نيم
    username_exists = await db.users.find_one({"username": data.username})
    if username_exists:
        raise HTTPException(status_code=400, detail="اسم المستخدم موجود مسبقاً")
    
    import uuid
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = {
        "id": str(uuid.uuid4()),
        "username": data.username,
        "password_hash": hash_password(data.password),
        "full_name": employee.get("full_name", ""),
        "full_name_ar": employee.get("full_name_ar", ""),
        "role": "employee",
        "email": employee.get("email", ""),
        "is_active": True,
        "employee_id": data.employee_id,
        "created_at": now,
        "created_by": user["user_id"]
    }
    
    await db.users.insert_one(new_user)
    
    new_user.pop("_id", None)
    new_user.pop("password_hash", None)
    
    return {
        "message": "تم إنشاء المستخدم بنجاح",
        "user": new_user
    }


@router.delete("/{employee_id}")
async def delete_user(employee_id: str, user=Depends(require_roles('stas'))):
    """
    حذف مستخدم (تعطيله)
    """
    existing = await db.users.find_one({"employee_id": employee_id})
    if not existing:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # تعطيل بدلاً من الحذف
    await db.users.update_one(
        {"employee_id": employee_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "تم تعطيل المستخدم بنجاح"}
