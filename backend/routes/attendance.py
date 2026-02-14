from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user
from utils.attendance_rules import validate_check_in, validate_check_out
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class CheckInRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False
    work_location: str = "HQ"  # HQ or Project


class CheckOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_available: bool = False
    work_location: Optional[str] = None


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
    """
    Check-in with server-side validation:
    - Employee must be active with contract
    - Work location validated
    - Working hours checked (warning only)
    """
    # Validate using attendance rules
    validation = await validate_check_in(user['user_id'], req.work_location)
    
    if not validation['valid']:
        error = validation['error']
        raise HTTPException(status_code=400, detail=error['message'])
    
    emp = validation['employee']
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Calculate GPS validity
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
        "work_location": req.work_location,
        "warnings": validation.get('warnings', []),
        "created_at": now.isoformat()
    }
    
    await db.attendance_ledger.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.post("/check-out")
async def check_out(req: CheckOutRequest, user=Depends(get_current_user)):
    """
    Check-out with server-side validation:
    - Must have checked in today
    - Cannot checkout twice
    """
    # Validate using attendance rules
    validation = await validate_check_out(user['user_id'])
    
    if not validation['valid']:
        error = validation['error']
        raise HTTPException(status_code=400, detail=error['message'])
    
    emp = validation['employee']
    checkin = validation['checkin']
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Calculate GPS validity
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
        "work_location": req.work_location or checkin.get('work_location', 'HQ'),
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


@router.get("/admin")
async def get_admin_attendance(
    period: str = "daily",
    date: str = None,
    user=Depends(get_current_user)
):
    """Admin view of all employee attendance. period: daily/weekly/monthly/yearly"""
    role = user.get('role')
    if role not in ('sultan', 'naif', 'salah', 'mohammed', 'stas'):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    target_date = date or now.strftime("%Y-%m-%d")
    
    if period == "daily":
        query = {"date": target_date}
    elif period == "weekly":
        # Get current week (last 7 days from target)
        dt = datetime.strptime(target_date, "%Y-%m-%d")
        start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        end = (dt - timedelta(days=dt.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")
        query = {"date": {"$gte": start, "$lte": end}}
    elif period == "monthly":
        month_start = target_date[:7] + "-01"
        # Calculate month end
        dt = datetime.strptime(month_start, "%Y-%m-%d")
        if dt.month == 12:
            month_end = f"{dt.year + 1}-01-01"
        else:
            month_end = f"{dt.year}-{dt.month + 1:02d}-01"
        query = {"date": {"$gte": month_start, "$lt": month_end}}
    elif period == "yearly":
        year = target_date[:4]
        query = {"date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}}
    else:
        query = {"date": target_date}
    
    entries = await db.attendance_ledger.find(query, {"_id": 0}).sort("date", -1).to_list(5000)
    
    # Group by employee and date
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(200)
    emp_map = {e['id']: e for e in employees}
    
    # Build summary
    grouped = {}
    for entry in entries:
        emp_id = entry['employee_id']
        date_key = entry['date']
        key = f"{emp_id}_{date_key}"
        if key not in grouped:
            emp = emp_map.get(emp_id, {})
            grouped[key] = {
                "employee_id": emp_id,
                "employee_name": emp.get('full_name', ''),
                "employee_name_ar": emp.get('full_name_ar', ''),
                "employee_number": emp.get('employee_number', ''),
                "date": date_key,
                "check_in": None,
                "check_out": None,
                "check_in_time": None,
                "check_out_time": None,
                "gps_valid_in": None,
                "gps_valid_out": None,
                "work_location": None,
            }
        if entry['type'] == 'check_in':
            grouped[key]['check_in'] = entry['timestamp']
            grouped[key]['check_in_time'] = entry['timestamp'][11:19] if entry.get('timestamp') else None
            grouped[key]['gps_valid_in'] = entry.get('gps_valid')
            grouped[key]['work_location'] = entry.get('work_location')
        elif entry['type'] == 'check_out':
            grouped[key]['check_out'] = entry['timestamp']
            grouped[key]['check_out_time'] = entry['timestamp'][11:19] if entry.get('timestamp') else None
            grouped[key]['gps_valid_out'] = entry.get('gps_valid')
    
    result = sorted(grouped.values(), key=lambda x: (x['date'], x['employee_name']), reverse=True)
    return result
