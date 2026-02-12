from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class CheckInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False


class CheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False


GEOFENCE_CENTER = {"lat": 24.7136, "lng": 46.6753}  # Riyadh default
GEOFENCE_RADIUS_KM = 5.0


def haversine_distance(lat1, lon1, lat2, lon2):
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


@router.post("/check-in")
async def check_in(req: CheckInRequest, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="Not registered as employee")

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    existing = await db.attendance_ledger.find_one({
        "employee_id": emp['id'],
        "date": today,
        "type": "check_in"
    })
    if existing:
        raise HTTPException(status_code=400, detail="Already checked in today")

    gps_valid = False
    distance = None
    if req.gps_available and req.latitude and req.longitude:
        distance = haversine_distance(req.latitude, req.longitude, GEOFENCE_CENTER['lat'], GEOFENCE_CENTER['lng'])
        gps_valid = distance <= GEOFENCE_RADIUS_KM

    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": emp['id'],
        "transaction_id": None,
        "type": "check_in",
        "timestamp": now.isoformat(),
        "date": today,
        "location": {"lat": req.latitude, "lng": req.longitude} if req.gps_available else None,
        "gps_available": req.gps_available,
        "gps_valid": gps_valid,
        "distance_km": round(distance, 2) if distance else None,
        "created_at": now.isoformat()
    }
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.post("/check-out")
async def check_out(req: CheckOutRequest, user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="Not registered as employee")

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    checkin = await db.attendance_ledger.find_one({
        "employee_id": emp['id'], "date": today, "type": "check_in"
    })
    if not checkin:
        raise HTTPException(status_code=400, detail="No check-in found for today")

    existing_out = await db.attendance_ledger.find_one({
        "employee_id": emp['id'], "date": today, "type": "check_out"
    })
    if existing_out:
        raise HTTPException(status_code=400, detail="Already checked out today")

    gps_valid = False
    distance = None
    if req.gps_available and req.latitude and req.longitude:
        distance = haversine_distance(req.latitude, req.longitude, GEOFENCE_CENTER['lat'], GEOFENCE_CENTER['lng'])
        gps_valid = distance <= GEOFENCE_RADIUS_KM

    entry = {
        "id": str(uuid.uuid4()),
        "employee_id": emp['id'],
        "transaction_id": None,
        "type": "check_out",
        "timestamp": now.isoformat(),
        "date": today,
        "location": {"lat": req.latitude, "lng": req.longitude} if req.gps_available else None,
        "gps_available": req.gps_available,
        "gps_valid": gps_valid,
        "distance_km": round(distance, 2) if distance else None,
        "created_at": now.isoformat()
    }
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.get("/today")
async def get_today_attendance(user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        return {"check_in": None, "check_out": None}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    checkin = await db.attendance_ledger.find_one(
        {"employee_id": emp['id'], "date": today, "type": "check_in"}, {"_id": 0}
    )
    checkout = await db.attendance_ledger.find_one(
        {"employee_id": emp['id'], "date": today, "type": "check_out"}, {"_id": 0}
    )
    return {"check_in": checkin, "check_out": checkout}


@router.get("/history")
async def get_attendance_history(user=Depends(get_current_user)):
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        return []
    entries = await db.attendance_ledger.find(
        {"employee_id": emp['id']}, {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    return entries
