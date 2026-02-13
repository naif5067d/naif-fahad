from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from utils.auth import verify_password, create_access_token, get_current_user, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


ROLE_ORDER = {"stas": 0, "mohammed": 1, "sultan": 2, "naif": 3, "salah": 4, "supervisor": 5, "employee": 6}


@router.get("/users")
async def list_all_users():
    """List all users for user switcher (no auth required). Excludes archived users."""
    users = await db.users.find(
        {"$or": [{"is_archived": {"$ne": True}}, {"is_archived": {"$exists": False}}]},
        {"_id": 0, "password_hash": 0}
    ).to_list(100)
    users.sort(key=lambda u: ROLE_ORDER.get(u.get('role', ''), 99))
    return users


@router.post("/switch/{user_id}")
async def switch_user(user_id: str):
    """Switch to a user by ID (no password required - user switcher mode)."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.get('is_active', True):
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({
        "user_id": user['id'],
        "role": user['role'],
        "username": user['username'],
        "full_name": user['full_name']
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
    user = await db.users.find_one({"username": req.username}, {"_id": 0})
    if not user or not verify_password(req.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get('is_active', True):
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({
        "user_id": user['id'],
        "role": user['role'],
        "username": user['username'],
        "full_name": user['full_name']
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


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0, "password_hash": 0})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    db_user = await db.users.find_one({"id": user['user_id']}, {"_id": 0})
    if not verify_password(req.current_password, db_user['password_hash']):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    await db.users.update_one(
        {"id": user['user_id']},
        {"$set": {"password_hash": hash_password(req.new_password)}}
    )
    return {"message": "Password changed successfully"}
