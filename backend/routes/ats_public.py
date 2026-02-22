"""
ATS Public Routes - Completely isolated public endpoints
NO authentication required - for job applicants only
SECURITY: These routes have NO access to main HR system data
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timezone
from database import db
import uuid
import os
import re

router = APIRouter(prefix="/api/ats/public", tags=["ATS Public"])

# ==================== SECURITY CONFIGURATION ====================

# Allowed file types
ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILES = 2

# Upload directory (isolated from main app uploads)
ATS_UPLOAD_DIR = "/app/uploads/ats_cv"
os.makedirs(ATS_UPLOAD_DIR, exist_ok=True)

# ==================== HELPER FUNCTIONS ====================

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Validate phone number (basic)"""
    # Remove spaces and dashes
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    # Should be 8-15 digits, optionally starting with +
    return bool(re.match(r'^\+?\d{8,15}$', clean))

def get_file_extension(filename: str) -> str:
    """Get lowercase file extension"""
    return os.path.splitext(filename)[1].lower()

def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filename"""
    # Keep only alphanumeric, dots, underscores, dashes
    name = re.sub(r'[^\w\.\-]', '_', filename)
    return name[:100]  # Limit length

# ==================== PUBLIC ENDPOINTS ====================

@router.get("/careers")
async def get_careers_page():
    """
    Get all active jobs for public careers/jobs listing page
    Returns empty list with polite message if no jobs available
    """
    jobs = await db.ats_jobs.find(
        {"status": "active"},
        {
            "_id": 0,
            "id": 1,
            "slug": 1,
            "title_ar": 1,
            "title_en": 1,
            "description": 1,
            "location": 1,
            "contract_type": 1,
            "experience_years": 1,
            "created_at": 1
        }
    ).sort("created_at", -1).to_list(100)
    
    return {
        "jobs": jobs,
        "count": len(jobs),
        "message": {
            "ar": "شكراً لاهتمامك بالانضمام إلى فريقنا" if jobs else "نشكرك على اهتمامك، لا توجد شواغر متاحة حالياً. ندعوك لزيارة هذه الصفحة لاحقاً للاطلاع على الفرص الجديدة.",
            "en": "Thank you for your interest in joining our team" if jobs else "Thank you for your interest. There are no vacancies available at this time. Please check back later for new opportunities."
        }
    }


@router.get("/jobs/{slug}")
async def get_public_job(slug: str):
    """
    Get job details for public apply page
    SECURITY: Only returns minimal public info, no internal data
    """
    job = await db.ats_jobs.find_one(
        {"slug": slug, "status": "active"},
        {
            "_id": 0,
            "id": 1,
            "slug": 1,
            "title_ar": 1,
            "title_en": 1,
            "description": 1,
            "location": 1,
            "contract_type": 1,
            "experience_years": 1,
            "required_languages": 1,
            "required_skills": 1
        }
    )
    
    if not job:
        raise HTTPException(
            status_code=404, 
            detail={
                "ar": "الوظيفة غير موجودة أو أن التقديم مغلق",
                "en": "Job not found or applications are closed"
            }
        )
    
    return job


@router.post("/apply/{slug}")
async def submit_application(
    slug: str,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Submit a job application
    SECURITY: 
    - No authentication required
    - Strict file validation
    - Rate limiting should be added in production
    - No access to main HR system
    """
    
    # Validate job exists and is active
    job = await db.ats_jobs.find_one({"slug": slug, "status": "active"})
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "ar": "الوظيفة غير موجودة أو أن التقديم مغلق",
                "en": "Job not found or applications are closed"
            }
        )
    
    # Validate inputs
    if not full_name or len(full_name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "الرجاء إدخال الاسم الكامل",
                "en": "Please enter your full name"
            }
        )
    
    if not validate_email(email):
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "البريد الإلكتروني غير صحيح",
                "en": "Invalid email address"
            }
        )
    
    if not validate_phone(phone):
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "رقم الهاتف غير صحيح",
                "en": "Invalid phone number"
            }
        )
    
    # Validate file count
    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "الرجاء رفع السيرة الذاتية (ملف واحد أو اثنين)",
                "en": "Please upload your CV (1 or 2 files)"
            }
        )
    
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail={
                "ar": f"الحد الأقصى {MAX_FILES} ملفات فقط (سيرة عربية + سيرة إنجليزية)",
                "en": f"Maximum {MAX_FILES} files allowed (Arabic CV + English CV)"
            }
        )
    
    # Process and validate files
    saved_files = []
    app_id = str(uuid.uuid4())
    
    for idx, file in enumerate(files):
        # Check extension
        ext = get_file_extension(file.filename)
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail={
                    "ar": f"نوع الملف غير مدعوم: {ext}. الأنواع المسموحة: PDF, DOC, DOCX",
                    "en": f"Unsupported file type: {ext}. Allowed: PDF, DOC, DOCX"
                }
            )
        
        # Read file content
        content = await file.read()
        
        # Check size
        if len(content) > MAX_FILE_SIZE:
            size_mb = len(content) / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail={
                    "ar": f"حجم الملف كبير جداً ({size_mb:.1f}MB). الحد الأقصى 5MB",
                    "en": f"File too large ({size_mb:.1f}MB). Maximum size is 5MB"
                }
            )
        
        # Save file
        safe_name = sanitize_filename(file.filename)
        file_id = str(uuid.uuid4())[:8]
        filename = f"{app_id}_{file_id}_{safe_name}"
        filepath = os.path.join(ATS_UPLOAD_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        saved_files.append({
            "id": file_id,
            "original_name": file.filename,
            "saved_name": filename,
            "path": filepath,
            "size": len(content),
            "type": ext,
            "label": "cv_ar" if idx == 0 else "cv_en"
        })
    
    # Check for duplicate application (same email + same job)
    existing = await db.ats_applications.find_one({
        "job_id": job["id"],
        "email": email.lower().strip()
    })
    
    if existing:
        # Clean up uploaded files
        for f in saved_files:
            try:
                os.remove(f["path"])
            except:
                pass
        
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "لقد قدمت على هذه الوظيفة مسبقاً",
                "en": "You have already applied to this job"
            }
        )
    
    # ============ PHASE 2: Text Extraction & ATS Scoring ============
    from services.ats_extraction import extract_text_from_file, detect_language
    from services.ats_scoring import score_application
    
    # Extract text from all CV files
    all_text = ""
    ats_readable = True
    extraction_errors = []
    
    for f in saved_files:
        text, is_readable, error = await extract_text_from_file(f["path"])
        f["extracted_text"] = text
        f["is_readable"] = is_readable
        f["extraction_error"] = error
        f["language"] = detect_language(text)
        
        if text:
            all_text += text + "\n\n"
        
        if not is_readable:
            ats_readable = False
            extraction_errors.append(f["original_name"])
    
    # Reject if not ATS-readable
    if not ats_readable or len(all_text.strip()) < 100:
        # Clean up files
        for f in saved_files:
            try:
                os.remove(f["path"])
            except:
                pass
        
        raise HTTPException(
            status_code=400,
            detail={
                "ar": "ملفك غير مناسب للقراءة الآلية (ATS). ارفع نسخة نصية قابلة للقراءة (PDF نصي أو Word)، وتجنب ملفات السكان.",
                "en": "Your file is not ATS-readable. Upload a text-based PDF or Word file (avoid scanned/image PDFs)."
            }
        )
    
    # Score the application
    job_requirements = {
        "required_skills": job.get("required_skills", ""),
        "experience_years": job.get("experience_years", 0),
        "required_languages": job.get("required_languages", ["ar"]),
    }
    
    scoring_result = await score_application(all_text, job_requirements, ats_readable)
    
    # Create application record
    now = datetime.now(timezone.utc).isoformat()
    application = {
        "id": app_id,
        "job_id": job["id"],
        "job_slug": slug,
        "full_name": full_name.strip(),
        "email": email.lower().strip(),
        "phone": phone.strip(),
        "files": saved_files,
        "file_count": len(saved_files),
        "status": "new",
        # ATS Intelligence fields
        "ats_readable": ats_readable,
        "extracted_text": all_text[:10000],  # Limit stored text
        "score": scoring_result.get("score", 0),
        "auto_class": scoring_result.get("auto_class", "Weak"),
        "tier": scoring_result.get("tier", "C"),
        "scoring": scoring_result,
        # Legacy fields
        "notes": [],
        "submitted_at": now,
        "status_updated_at": now
    }
    
    await db.ats_applications.insert_one(application)
    
    return {
        "success": True,
        "message": {
            "ar": "شكراً، تم استلام السيرة الذاتية بنجاح. سيتم التواصل عبر بيانات الاتصال.",
            "en": "Thank you, your CV has been received successfully. We will contact you via your contact details."
        }
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint
    SECURITY: Returns minimal info, no system details
    """
    return {"status": "ok", "service": "ats-public"}
