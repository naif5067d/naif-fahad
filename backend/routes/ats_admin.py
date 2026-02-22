"""
ATS Admin Routes - Protected routes for HR/Admin only
Handles job management and application review
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone
from database import db
from utils.auth import get_current_user
import uuid
import os

router = APIRouter(prefix="/api/ats/admin", tags=["ATS Admin"])

# ==================== MODELS ====================

class JobCreate(BaseModel):
    title_ar: str
    title_en: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    contract_type: Optional[str] = "full_time"  # full_time, part_time, contract
    experience_years: Optional[int] = 0
    required_languages: Optional[List[str]] = ["ar"]
    required_skills: Optional[str] = ""  # comma separated

class JobUpdate(BaseModel):
    title_ar: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    contract_type: Optional[str] = None
    experience_years: Optional[int] = None
    required_languages: Optional[List[str]] = None
    required_skills: Optional[str] = None
    status: Optional[str] = None  # active, closed, archived

class ApplicationStatusUpdate(BaseModel):
    status: str  # new, reviewed, interview, offer, hired, rejected

class ApplicationNote(BaseModel):
    note: str

# ==================== HELPER FUNCTIONS ====================

def require_ats_access(user: dict):
    """Check if user has ATS access (admin or hr role)"""
    role = user.get('role', '')
    username = user.get('username', '')
    if role not in ['admin', 'hr'] and username not in ['stas', 'naif', 'sultan', 'mohammed']:
        raise HTTPException(status_code=403, detail="Access denied. ATS access requires admin or hr role.")
    return True

def require_admin_only(user: dict):
    """Check if user is admin (naif/stas only for destructive actions)"""
    role = user.get('role', '')
    username = user.get('username', '')
    if role != 'admin' and username not in ['stas', 'naif']:
        raise HTTPException(status_code=403, detail="Admin access required for this action.")
    return True

def generate_job_slug():
    """Generate unique job ID for public URL"""
    return str(uuid.uuid4())[:8]

# ==================== JOBS ENDPOINTS ====================

@router.get("/jobs")
async def list_jobs(user=Depends(get_current_user)):
    """List all jobs with application counts"""
    require_ats_access(user)
    
    jobs = await db.ats_jobs.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Add application count for each job
    for job in jobs:
        count = await db.ats_applications.count_documents({"job_id": job.get("id")})
        job["applicants_count"] = count
    
    return jobs


@router.post("/jobs")
async def create_job(job: JobCreate, user=Depends(get_current_user)):
    """Create a new job posting"""
    require_ats_access(user)
    
    job_id = str(uuid.uuid4())
    slug = generate_job_slug()
    now = datetime.now(timezone.utc).isoformat()
    
    job_doc = {
        "id": job_id,
        "slug": slug,
        "title_ar": job.title_ar,
        "title_en": job.title_en,
        "description": job.description,
        "location": job.location,
        "contract_type": job.contract_type,
        "experience_years": job.experience_years,
        "required_languages": job.required_languages,
        "required_skills": job.required_skills,
        "status": "active",
        "created_by": user.get("user_id"),
        "created_at": now,
        "updated_at": now
    }
    
    await db.ats_jobs.insert_one(job_doc)
    job_doc.pop("_id", None)
    
    return job_doc


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(get_current_user)):
    """Get job details"""
    require_ats_access(user)
    
    job = await db.ats_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Add application count
    count = await db.ats_applications.count_documents({"job_id": job_id})
    job["applicants_count"] = count
    
    return job


@router.put("/jobs/{job_id}")
async def update_job(job_id: str, job: JobUpdate, user=Depends(get_current_user)):
    """Update job details"""
    require_ats_access(user)
    
    existing = await db.ats_jobs.find_one({"id": job_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = {k: v for k, v in job.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.ats_jobs.update_one({"id": job_id}, {"$set": update_data})
    
    updated = await db.ats_jobs.find_one({"id": job_id}, {"_id": 0})
    return updated


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user=Depends(get_current_user)):
    """Delete a job (admin only) - also deletes all applications"""
    require_admin_only(user)
    
    job = await db.ats_jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete all applications for this job
    await db.ats_applications.delete_many({"job_id": job_id})
    
    # Delete the job
    await db.ats_jobs.delete_one({"id": job_id})
    
    return {"message": "Job and all applications deleted"}


@router.post("/jobs/{job_id}/archive")
async def archive_job(job_id: str, user=Depends(get_current_user)):
    """Archive a job (admin only)"""
    require_admin_only(user)
    
    result = await db.ats_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job archived"}


@router.post("/jobs/{job_id}/close")
async def close_job(job_id: str, user=Depends(get_current_user)):
    """Close a job (stop accepting applications)"""
    require_ats_access(user)
    
    result = await db.ats_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "closed", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job closed"}


@router.post("/jobs/{job_id}/reopen")
async def reopen_job(job_id: str, user=Depends(get_current_user)):
    """Reopen a closed job"""
    require_ats_access(user)
    
    result = await db.ats_jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "active", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"message": "Job reopened"}


# ==================== APPLICATIONS ENDPOINTS ====================

@router.get("/jobs/{job_id}/applications")
async def list_applications(
    job_id: str, 
    tier: str = None,  # Filter by tier: A, B, C, or all
    show_tier_c: bool = False,  # Show Tier C by default
    user=Depends(get_current_user)
):
    """List all applications for a job with tier filtering"""
    require_ats_access(user)
    
    job = await db.ats_jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Build query
    query = {"job_id": job_id}
    
    if tier and tier in ['A', 'B', 'C']:
        query["tier"] = tier
    elif not show_tier_c:
        # Default: hide Tier C
        query["tier"] = {"$in": ["A", "B"]}
    
    applications = await db.ats_applications.find(
        query, 
        {"_id": 0, "extracted_text": 0}  # Exclude large text field
    ).sort([("score", -1), ("submitted_at", -1)]).to_list(1000)
    
    # Count by tier
    tier_counts = {
        "A": await db.ats_applications.count_documents({"job_id": job_id, "tier": "A"}),
        "B": await db.ats_applications.count_documents({"job_id": job_id, "tier": "B"}),
        "C": await db.ats_applications.count_documents({"job_id": job_id, "tier": "C"}),
    }
    
    return {
        "job": job, 
        "applications": applications,
        "tier_counts": tier_counts,
        "total": sum(tier_counts.values())
    }


@router.get("/applications/{app_id}")
async def get_application(app_id: str, user=Depends(get_current_user)):
    """Get application details with full scoring info"""
    require_ats_access(user)
    
    app = await db.ats_applications.find_one({"id": app_id}, {"_id": 0})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get job info
    job = await db.ats_jobs.find_one({"id": app.get("job_id")}, {"_id": 0})
    app["job"] = job
    
    return app


@router.put("/applications/{app_id}/status")
async def update_application_status(app_id: str, data: ApplicationStatusUpdate, user=Depends(get_current_user)):
    """Update application status"""
    require_ats_access(user)
    
    valid_statuses = ["new", "reviewed", "interview", "offer", "hired", "rejected"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    result = await db.ats_applications.update_one(
        {"id": app_id},
        {"$set": {
            "status": data.status,
            "status_updated_at": datetime.now(timezone.utc).isoformat(),
            "status_updated_by": user.get("user_id")
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {"message": f"Status updated to {data.status}"}


@router.post("/applications/{app_id}/notes")
async def add_application_note(app_id: str, data: ApplicationNote, user=Depends(get_current_user)):
    """Add a note to an application"""
    require_ats_access(user)
    
    note = {
        "id": str(uuid.uuid4()),
        "text": data.note,
        "created_by": user.get("user_id"),
        "created_by_name": user.get("full_name_ar", user.get("username", "")),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.ats_applications.update_one(
        {"id": app_id},
        {"$push": {"notes": note}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return note


@router.delete("/applications/{app_id}")
async def delete_application(app_id: str, user=Depends(get_current_user)):
    """Permanently delete an application (admin only)"""
    require_admin_only(user)
    
    app = await db.ats_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Delete uploaded files
    files = app.get("files", [])
    for f in files:
        file_path = f.get("path", "")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    
    # Delete from database
    await db.ats_applications.delete_one({"id": app_id})
    
    return {"message": "Application and files permanently deleted"}


# ==================== STATISTICS ====================

@router.get("/stats")
async def get_ats_stats(user=Depends(get_current_user)):
    """Get ATS statistics"""
    require_ats_access(user)
    
    total_jobs = await db.ats_jobs.count_documents({})
    active_jobs = await db.ats_jobs.count_documents({"status": "active"})
    total_applications = await db.ats_applications.count_documents({})
    new_applications = await db.ats_applications.count_documents({"status": "new"})
    
    # Applications by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = await db.ats_applications.aggregate(pipeline).to_list(20)
    
    # Applications by tier
    tier_pipeline = [
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}}
    ]
    tier_counts = await db.ats_applications.aggregate(tier_pipeline).to_list(10)
    
    # Applications by class
    class_pipeline = [
        {"$group": {"_id": "$auto_class", "count": {"$sum": 1}}}
    ]
    class_counts = await db.ats_applications.aggregate(class_pipeline).to_list(10)
    
    # High potential count
    high_potential = await db.ats_applications.count_documents({"scoring.high_potential": True})
    
    # Average score
    avg_pipeline = [
        {"$match": {"score": {"$ne": None}}},
        {"$group": {"_id": None, "avg_score": {"$avg": "$score"}}}
    ]
    avg_result = await db.ats_applications.aggregate(avg_pipeline).to_list(1)
    avg_score = avg_result[0]["avg_score"] if avg_result else 0
    
    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "new_applications": new_applications,
        "by_status": {s["_id"]: s["count"] for s in status_counts if s["_id"]},
        "by_tier": {t["_id"]: t["count"] for t in tier_counts if t["_id"]},
        "by_class": {c["_id"]: c["count"] for c in class_counts if c["_id"]},
        "high_potential": high_potential,
        "avg_score": round(avg_score, 1)
    }


# ==================== FEEDBACK LEARNING ====================

@router.post("/applications/{app_id}/outcome")
async def record_outcome(app_id: str, outcome: str, notes: str = "", user=Depends(get_current_user)):
    """
    Record final outcome for feedback learning
    Outcomes: shortlisted, interview, offer, hired, rejected
    """
    require_ats_access(user)
    
    valid_outcomes = ["shortlisted", "interview", "offer", "hired", "rejected"]
    if outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid outcome. Must be one of: {valid_outcomes}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.ats_applications.update_one(
        {"id": app_id},
        {"$set": {
            "final_outcome": outcome,
            "outcome_recorded_at": now,
            "outcome_recorded_by": user.get("user_id"),
            "outcome_notes": notes
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {"message": f"Outcome recorded: {outcome}"}


@router.get("/calibration-report")
async def get_calibration_report(user=Depends(get_current_user)):
    """
    Monthly calibration report: compare ATS predictions vs actual outcomes
    Used for weight adjustment suggestions
    """
    require_ats_access(user)
    
    # Get applications with outcomes
    apps_with_outcome = await db.ats_applications.find(
        {"final_outcome": {"$exists": True, "$ne": None}},
        {"_id": 0, "score": 1, "auto_class": 1, "tier": 1, "final_outcome": 1, "scoring": 1}
    ).to_list(1000)
    
    if not apps_with_outcome:
        return {
            "message": "No outcome data yet for calibration",
            "total_with_outcomes": 0
        }
    
    # Analyze accuracy
    positive_outcomes = ["shortlisted", "interview", "offer", "hired"]
    
    # Group by tier
    tier_accuracy = {"A": {"correct": 0, "total": 0}, "B": {"correct": 0, "total": 0}, "C": {"correct": 0, "total": 0}}
    class_accuracy = {"Excellent": {"correct": 0, "total": 0}, "Strong": {"correct": 0, "total": 0}, 
                      "Acceptable": {"correct": 0, "total": 0}, "Weak": {"correct": 0, "total": 0}}
    
    for app in apps_with_outcome:
        tier = app.get("tier", "C")
        auto_class = app.get("auto_class", "Weak")
        outcome = app.get("final_outcome", "")
        is_positive = outcome in positive_outcomes
        
        if tier in tier_accuracy:
            tier_accuracy[tier]["total"] += 1
            if (tier in ["A", "B"] and is_positive) or (tier == "C" and not is_positive):
                tier_accuracy[tier]["correct"] += 1
        
        if auto_class in class_accuracy:
            class_accuracy[auto_class]["total"] += 1
            expected_positive = auto_class in ["Excellent", "Strong"]
            if (expected_positive and is_positive) or (not expected_positive and not is_positive):
                class_accuracy[auto_class]["correct"] += 1
    
    # Calculate accuracy percentages
    for tier in tier_accuracy:
        total = tier_accuracy[tier]["total"]
        if total > 0:
            tier_accuracy[tier]["accuracy"] = round(tier_accuracy[tier]["correct"] / total * 100, 1)
        else:
            tier_accuracy[tier]["accuracy"] = 0
    
    for cls in class_accuracy:
        total = class_accuracy[cls]["total"]
        if total > 0:
            class_accuracy[cls]["accuracy"] = round(class_accuracy[cls]["correct"] / total * 100, 1)
        else:
            class_accuracy[cls]["accuracy"] = 0
    
    # Weight adjustment suggestions
    suggestions = []
    if tier_accuracy["A"]["accuracy"] < 70:
        suggestions.append("Consider increasing skill_match weight - Tier A accuracy is low")
    if tier_accuracy["C"]["accuracy"] < 60:
        suggestions.append("Consider reviewing fluff_penalty - too many Tier C candidates being hired")
    
    return {
        "total_with_outcomes": len(apps_with_outcome),
        "tier_accuracy": tier_accuracy,
        "class_accuracy": class_accuracy,
        "suggestions": suggestions
    }
