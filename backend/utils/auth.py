from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import os

SECRET_KEY = os.environ.get('JWT_SECRET', 'dar-al-code-hr-os-2026-x9k2m')
ALGORITHM = "HS256"

# مدة الجلسة حسب الدور (بالساعات)
TOKEN_EXPIRE_HOURS = {
    "stas": 12,      # المدير العام
    "mohammed": 8,   # الرئيس التنفيذي
    "sultan": 8,     # مدير العمليات
    "naif": 8,       # المدير المالي
    "salah": 8,      # المدقق
    "supervisor": 6, # المشرفين
    "employee": 4    # الموظفين - أقصر مدة
}
DEFAULT_TOKEN_EXPIRE = 4  # الافتراضي 4 ساعات

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, role: str = "employee") -> str:
    """إنشاء توكن مع مدة صلاحية حسب الدور"""
    to_encode = data.copy()
    expire_hours = TOKEN_EXPIRE_HOURS.get(role, DEFAULT_TOKEN_EXPIRE)
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=expire_hours)
    to_encode["iat"] = datetime.now(timezone.utc)  # وقت الإصدار
    to_encode["jti"] = os.urandom(16).hex()  # معرف فريد للتوكن
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """التحقق من التوكن والجلسة"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        # التحقق من أن الجلسة لم تُبطل
        from database import db
        token_id = payload.get("jti")
        if token_id:
            revoked = await db.revoked_tokens.find_one({"token_id": token_id})
            if revoked:
                raise HTTPException(status_code=401, detail="تم إنهاء هذه الجلسة")
        
        # التحقق من أن المستخدم لم يُحظر
        user_id = payload.get("user_id")
        if user_id:
            user = await db.users.find_one({"id": user_id}, {"is_blocked": 1, "is_active": 1})
            if user and (user.get("is_blocked") or not user.get("is_active", True)):
                raise HTTPException(status_code=401, detail="الحساب معطل أو محظور")
        
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="توكن غير صالح أو منتهي الصلاحية")


def require_roles(*roles):
    async def checker(user=Depends(get_current_user)):
        if user.get('role') not in roles:
            raise HTTPException(status_code=403, detail="Access denied for your role")
        return user
    return checker
