from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import verify_password, create_access_token, get_current_user, hash_password
from datetime import datetime, timezone

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    device_signature: Optional[str] = None
    fingerprint_data: Optional[dict] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


ROLE_ORDER = {"stas": 0, "mohammed": 1, "sultan": 2, "naif": 3, "salah": 4, "supervisor": 5, "employee": 6}

# الأدوار المُعفاة من فحص الأجهزة
EXEMPT_ROLES = ['stas']  # فقط STAS معفي من فحص الجهاز


@router.get("/users")
async def list_all_users(user=Depends(get_current_user)):
    """List all users for user switcher - STAS only"""
    # فقط STAS يمكنه رؤية قائمة المستخدمين
    if user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="غير مصرح")
    
    users = await db.users.find(
        {"$or": [{"is_archived": {"$ne": True}}, {"is_archived": {"$exists": False}}]},
        {"_id": 0, "password_hash": 0, "plain_password": 0}
    ).to_list(100)
    users.sort(key=lambda u: ROLE_ORDER.get(u.get('role', ''), 99))
    return users


@router.post("/switch/{user_id}")
async def switch_user(user_id: str, current_user=Depends(get_current_user)):
    """Switch to a user by ID - STAS only"""
    # فقط STAS يمكنه تبديل المستخدمين
    if current_user.get('role') != 'stas':
        raise HTTPException(status_code=403, detail="فقط STAS يمكنه تبديل المستخدمين")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    if not user.get('is_active', True):
        raise HTTPException(status_code=403, detail="الحساب معطل")

    token = create_access_token({
        "user_id": user['id'],
        "role": user['role'],
        "username": user['username'],
        "full_name": user['full_name'],
        "employee_id": user.get('employee_id'),
        "switched_by": current_user.get('user_id')  # تسجيل من قام بالتبديل
    })

    return {
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "full_name": user['full_name'],
            "full_name_ar": user.get('full_name_ar', ''),
            "role": user['role'],
            "employee_id": user.get('employee_id'),
            "is_active": user.get('is_active', True)
        }
    }


@router.post("/login")
async def login(req: LoginRequest):
    """
    تسجيل الدخول مع فحص الجهاز
    - المدراء (STAS, Sultan, Naif, etc.): معفون من فحص الأجهزة
    - الموظفون: يتم فحص الجهاز ويجب أن يكون معتمداً
    """
    user = await db.users.find_one({"username": req.username}, {"_id": 0})
    if not user:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "INVALID_CREDENTIALS",
                "message_ar": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "message_en": "Invalid username or password"
            }
        )
    
    if not verify_password(req.password, user['password_hash']):
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "INVALID_CREDENTIALS",
                "message_ar": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "message_en": "Invalid username or password"
            }
        )
    
    if not user.get('is_active', True):
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "ACCOUNT_DISABLED",
                "message_ar": "الحساب معطل",
                "message_en": "Account is disabled"
            }
        )
    
    # التحقق من الحساب المحظور
    if user.get('is_blocked'):
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "ACCOUNT_BLOCKED",
                "message_ar": "تم إيقاف حسابك مؤقتاً للتحقيق. يرجى مراجعة الإدارة.",
                "message_en": "Your account has been temporarily suspended for investigation."
            }
        )
    
    employee_id = user.get('employee_id')
    role = user.get('role', 'employee')
    
    # فحص الجهاز للموظفين فقط (غير المدراء)
    if role not in EXEMPT_ROLES and req.device_signature and employee_id:
        from services.device_service import check_device_for_login
        device_check = await check_device_for_login(
            employee_id=employee_id,
            device_signature=req.device_signature,
            fingerprint_data=req.fingerprint_data or {}
        )
        
        if not device_check['allowed']:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": device_check['error'],
                    "message_ar": device_check['message_ar'],
                    "message_en": device_check['message_en']
                }
            )
    
    # تسجيل الدخول في سجل الأمان
    await db.security_audit_log.insert_one({
        "id": str(__import__('uuid').uuid4()),
        "employee_id": employee_id or user['id'],
        "action": "login_success",
        "device_signature": req.device_signature,
        "fingerprint_data": req.fingerprint_data,
        "details": {"username": req.username, "role": role},
        "performed_by": user['id'],
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    token = create_access_token({
        "user_id": user['id'],
        "role": role,
        "username": user['username'],
        "full_name": user['full_name'],
        "employee_id": employee_id
    })

    return {
        "token": token,
        "user": {
            "id": user['id'],
            "username": user['username'],
            "full_name": user['full_name'],
            "full_name_ar": user.get('full_name_ar', ''),
            "role": role,
            "employee_id": employee_id,
            "is_active": user.get('is_active', True)
        }
    }


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0, "password_hash": 0, "plain_password": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    return db_user


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    if not verify_password(req.current_password, db_user['password_hash']):
        raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
    await db.users.update_one(
        {"id": user['user_id']},
        {"$set": {
            "password_hash": hash_password(req.new_password),
            "plain_password": None
        }}
    )
    return {"message": "تم تغيير كلمة المرور بنجاح"}
