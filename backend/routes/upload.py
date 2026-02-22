"""
File Upload Routes - for medical files and other documents
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from utils.auth import get_current_user
from datetime import datetime, timezone
import uuid
import os
import base64

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Directory to store uploaded files
UPLOAD_DIR = "/app/backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/medical")
async def upload_medical_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    """
    Upload medical PDF file for sick leave requests.
    Returns the file URL for storage in the transaction.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="يجب أن يكون الملف بصيغة PDF")
    
    # Validate file size (max 5MB)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم الملف يجب أن لا يتجاوز 5 ميجابايت")
    
    # Generate unique filename
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"medical_{user['user_id'][:8]}_{timestamp}_{unique_id}.pdf"
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Return relative URL
    return {
        "url": f"/api/upload/files/{filename}",
        "filename": filename,
        "size": len(contents)
    }


@router.get("/files/{filename}")
async def get_uploaded_file(filename: str):
    """
    Retrieve an uploaded file.
    ملاحظة: هذا الـ endpoint عام لأن الملفات تُفتح في نافذة جديدة
    الأمان يأتي من اسم الملف العشوائي (UUID)
    """
    from fastapi.responses import FileResponse
    
    # تأمين: منع path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="اسم ملف غير صالح")
    
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="الملف غير موجود")
    
    return FileResponse(file_path, media_type="application/pdf", filename=filename)


# ATS CV files directory
ATS_UPLOAD_DIR = "/app/uploads/ats_cv"
os.makedirs(ATS_UPLOAD_DIR, exist_ok=True)


@router.get("/ats_cv/{filename}")
async def get_ats_cv_file(filename: str, user=Depends(get_current_user)):
    """
    Retrieve an uploaded ATS CV file.
    Protected - requires authentication (HR/Admin only)
    """
    from fastapi.responses import FileResponse
    
    # Check if user has ATS access
    role = user.get('role', '')
    username = user.get('username', '')
    if role not in ['admin', 'hr'] and username not in ['stas', 'naif', 'sultan', 'mohammed']:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Security: prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join(ATS_UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Detect content type
    ext = filename.split('.')[-1].lower()
    content_types = {
        'pdf': 'application/pdf',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    content_type = content_types.get(ext, 'application/octet-stream')
    
    return FileResponse(file_path, media_type=content_type, filename=filename)
