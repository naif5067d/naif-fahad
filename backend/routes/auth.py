from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import verify_password, create_access_token, get_current_user, hash_password
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate Limiting - تتبع محاولات تسجيل الدخول
login_attempts = {}  # {ip: {"count": int, "last_attempt": datetime, "blocked_until": datetime}}
MAX_LOGIN_ATTEMPTS = 5
BLOCK_DURATION_MINUTES = 15


def check_rate_limit(request: Request) -> bool:
    """التحقق من Rate Limiting"""
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    
    if client_ip in login_attempts:
        data = login_attempts[client_ip]
        
        # التحقق من الحظر
        if data.get("blocked_until") and now < data["blocked_until"]:
            remaining = (data["blocked_until"] - now).seconds // 60
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "TOO_MANY_ATTEMPTS",
                    "message_ar": f"تم حظرك مؤقتاً. حاول بعد {remaining} دقيقة",
                    "message_en": f"Too many attempts. Try again in {remaining} minutes"
                }
            )
        
        # إعادة تعيين إذا مر وقت كافٍ
        if (now - data["last_attempt"]).seconds > 300:  # 5 دقائق
            login_attempts[client_ip] = {"count": 0, "last_attempt": now}
    
    return True


def record_failed_attempt(request: Request):
    """تسجيل محاولة فاشلة"""
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    
    if client_ip not in login_attempts:
        login_attempts[client_ip] = {"count": 0, "last_attempt": now}
    
    login_attempts[client_ip]["count"] += 1
    login_attempts[client_ip]["last_attempt"] = now
    
    # حظر بعد المحاولات المسموحة
    if login_attempts[client_ip]["count"] >= MAX_LOGIN_ATTEMPTS:
        from datetime import timedelta
        login_attempts[client_ip]["blocked_until"] = now + timedelta(minutes=BLOCK_DURATION_MINUTES)


def clear_failed_attempts(request: Request):
    """مسح المحاولات الفاشلة بعد تسجيل دخول ناجح"""
    client_ip = request.client.host if request.client else "unknown"
    if client_ip in login_attempts:
        del login_attempts[client_ip]


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
EXEMPT_ROLES = ['stas', 'sultan', 'naif', 'mohammed', 'salah']  # المدراء معفون من فحص الجهاز


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
async def login(req: LoginRequest, request: Request):
    """
    تسجيل الدخول مع:
    - Rate Limiting (5 محاولات / 15 دقيقة حظر)
    - فحص تغير الجهاز
    - جلسات محدودة المدة حسب الدور
    """
    # التحقق من Rate Limiting
    check_rate_limit(request)
    
    user = await db.users.find_one({"username": req.username}, {"_id": 0})
    if not user:
        record_failed_attempt(request)
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "INVALID_CREDENTIALS",
                "message_ar": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "message_en": "Invalid username or password"
            }
        )
    
    if not verify_password(req.password, user['password_hash']):
        record_failed_attempt(request)
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
    user_id = user['id']
    
    # فحص تغير الجهاز (للموظفين فقط)
    device_changed = False
    if req.fingerprint_data and role not in EXEMPT_ROLES:
        from services.device_service import generate_core_hardware_signature
        current_signature = generate_core_hardware_signature(req.fingerprint_data)
        
        # الحصول على آخر جهاز مسجل
        last_session = await db.user_sessions.find_one(
            {"user_id": user_id, "is_active": True},
            sort=[("created_at", -1)]
        )
        
        if last_session and last_session.get("device_signature") != current_signature:
            device_changed = True
            # إبطال الجلسات القديمة عند تغير الجهاز
            await db.user_sessions.update_many(
                {"user_id": user_id, "is_active": True},
                {"$set": {"is_active": False, "revoked_reason": "device_changed", "revoked_at": datetime.now(timezone.utc)}}
            )
            # تسجيل الحدث
            await db.security_audit_log.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id or user_id,
                "action": "device_changed_logout",
                "old_signature": last_session.get("device_signature", "")[:16] + "...",
                "new_signature": current_signature[:16] + "...",
                "ip_address": request.client.host if request.client else "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    # مسح محاولات الدخول الفاشلة
    clear_failed_attempts(request)
    
    # إنشاء معرف الجلسة
    session_id = str(uuid.uuid4())
    token_id = str(uuid.uuid4())
    
    # تسجيل الجلسة الجديدة
    device_signature = None
    if req.fingerprint_data:
        from services.device_service import generate_core_hardware_signature
        device_signature = generate_core_hardware_signature(req.fingerprint_data)
    
    await db.user_sessions.insert_one({
        "id": session_id,
        "token_id": token_id,
        "user_id": user_id,
        "employee_id": employee_id,
        "role": role,
        "device_signature": device_signature,
        "fingerprint_data": req.fingerprint_data,
        "ip_address": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "last_activity": datetime.now(timezone.utc)
    })
    
    # تسجيل الدخول في سجل الأمان
    await db.security_audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id or user_id,
        "action": "login_success",
        "session_id": session_id,
        "device_signature": device_signature,
        "device_changed": device_changed,
        "ip_address": request.client.host if request.client else "unknown",
        "details": {"username": req.username, "role": role},
        "performed_by": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    token = create_access_token({
        "user_id": user_id,
        "role": role,
        "username": user['username'],
        "full_name": user['full_name'],
        "employee_id": employee_id,
        "session_id": session_id,
        "jti": token_id
    }, role=role)

    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": user['username'],
            "full_name": user['full_name'],
            "full_name_ar": user.get('full_name_ar', ''),
            "role": role,
            "employee_id": employee_id,
            "is_active": user.get('is_active', True)
        },
        "session_info": {
            "session_id": session_id,
            "device_changed": device_changed,
            "expires_in_hours": 12 if role == "stas" else (8 if role in EXEMPT_ROLES else 4)
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
