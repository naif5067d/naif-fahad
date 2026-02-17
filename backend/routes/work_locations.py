from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/work-locations", tags=["work_locations"])


class WorkDays(BaseModel):
    saturday: bool = True
    sunday: bool = True
    monday: bool = True
    tuesday: bool = True
    wednesday: bool = True
    thursday: bool = True
    friday: bool = False


class WorkLocationCreate(BaseModel):
    name: str
    name_ar: str
    latitude: float
    longitude: float
    radius_meters: int = 500  # Default 500m circle
    work_start: str  # "08:00"
    work_end: str    # "17:00"
    grace_checkin_minutes: int = 0  # مدة السماح للدخول (0-15 دقيقة)
    grace_checkout_minutes: int = 0  # مدة السماح للخروج (0-15 دقيقة)
    work_days: WorkDays
    assigned_employees: List[str] = []  # List of employee IDs


class WorkLocationUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[int] = None
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    grace_checkin_minutes: Optional[int] = None
    grace_checkout_minutes: Optional[int] = None
    work_days: Optional[WorkDays] = None
    assigned_employees: Optional[List[str]] = None


@router.get("")
async def list_work_locations(user=Depends(get_current_user)):
    """List all work locations - visible to all but editable only by ops/stas"""
    locations = await db.work_locations.find({}, {"_id": 0}).to_list(100)
    return locations


@router.get("/{location_id}")
async def get_work_location(location_id: str, user=Depends(get_current_user)):
    """Get a specific work location"""
    location = await db.work_locations.find_one({"id": location_id}, {"_id": 0})
    if not location:
        raise HTTPException(status_code=404, detail="Work location not found")
    return location


@router.post("")
async def create_work_location(req: WorkLocationCreate, user=Depends(get_current_user)):
    """Create a new work location - Sultan, Naif, STAS only"""
    if user.get('role') not in ['sultan', 'naif', 'stas']:
        raise HTTPException(status_code=403, detail="Only Operations or STAS can create work locations")
    
    # Validate grace period (0-15 minutes)
    grace_period = max(0, min(15, req.grace_period_minutes))
    
    now = datetime.now(timezone.utc).isoformat()
    location = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "name_ar": req.name_ar,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "radius_meters": req.radius_meters,
        "work_start": req.work_start,
        "work_end": req.work_end,
        "grace_period_minutes": grace_period,
        "work_days": req.work_days.model_dump(),
        "assigned_employees": req.assigned_employees,
        "created_by": user['user_id'],
        "created_at": now,
        "updated_at": now,
        "is_active": True
    }
    
    await db.work_locations.insert_one(location)
    location.pop('_id', None)
    return location


@router.put("/{location_id}")
async def update_work_location(location_id: str, req: WorkLocationUpdate, user=Depends(get_current_user)):
    """Update a work location - Sultan, Naif, STAS only"""
    if user.get('role') not in ['sultan', 'naif', 'stas']:
        raise HTTPException(status_code=403, detail="Only Operations or STAS can update work locations")
    
    location = await db.work_locations.find_one({"id": location_id})
    if not location:
        raise HTTPException(status_code=404, detail="Work location not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if req.name is not None:
        update_data["name"] = req.name
    if req.name_ar is not None:
        update_data["name_ar"] = req.name_ar
    if req.latitude is not None:
        update_data["latitude"] = req.latitude
    if req.longitude is not None:
        update_data["longitude"] = req.longitude
    if req.radius_meters is not None:
        update_data["radius_meters"] = req.radius_meters
    if req.work_start is not None:
        update_data["work_start"] = req.work_start
    if req.work_end is not None:
        update_data["work_end"] = req.work_end
    if req.grace_period_minutes is not None:
        # Validate grace period (0-15 minutes)
        update_data["grace_period_minutes"] = max(0, min(15, req.grace_period_minutes))
    if req.work_days is not None:
        update_data["work_days"] = req.work_days.model_dump()
    if req.assigned_employees is not None:
        update_data["assigned_employees"] = req.assigned_employees
    
    await db.work_locations.update_one({"id": location_id}, {"$set": update_data})
    
    updated = await db.work_locations.find_one({"id": location_id}, {"_id": 0})
    return updated


@router.delete("/{location_id}")
async def delete_work_location(location_id: str, user=Depends(get_current_user)):
    """Delete (deactivate) a work location - Sultan, Naif, STAS only"""
    if user.get('role') not in ['sultan', 'naif', 'stas']:
        raise HTTPException(status_code=403, detail="Only Operations or STAS can delete work locations")
    
    result = await db.work_locations.update_one(
        {"id": location_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Work location not found")
    
    return {"message": "Work location deleted"}


@router.post("/{location_id}/assign")
async def assign_employees(location_id: str, employee_ids: List[str], user=Depends(get_current_user)):
    """Assign employees to a work location - Sultan, Naif only (STAS monitors)"""
    if user.get('role') not in ['sultan', 'naif']:
        raise HTTPException(status_code=403, detail="Only Operations can assign employees to locations")
    
    location = await db.work_locations.find_one({"id": location_id})
    if not location:
        raise HTTPException(status_code=404, detail="Work location not found")
    
    # Verify all employee IDs exist
    for emp_id in employee_ids:
        emp = await db.employees.find_one({"id": emp_id})
        if not emp:
            raise HTTPException(status_code=400, detail=f"Employee {emp_id} not found")
    
    await db.work_locations.update_one(
        {"id": location_id},
        {
            "$set": {
                "assigned_employees": employee_ids,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": f"Assigned {len(employee_ids)} employees to location"}


@router.get("/employee/{employee_id}")
async def get_employee_locations(employee_id: str, user=Depends(get_current_user)):
    """Get all work locations assigned to an employee"""
    locations = await db.work_locations.find(
        {"assigned_employees": employee_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    return locations
