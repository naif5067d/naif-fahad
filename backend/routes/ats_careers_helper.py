"""
ATS Public Careers Page - List all active jobs
"""

from fastapi import APIRouter, HTTPException
from database import db

# Add to existing ats_public router
# This will be added to ats_public.py

async def get_all_active_jobs():
    """Get all active jobs for public careers page"""
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
    
    return jobs
