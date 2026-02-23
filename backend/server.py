from fastapi import FastAPI, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        
        # Allow iframe for embed and public ATS pages
        path = request.url.path
        if "/embed" in path or "/careers" in path or "/apply" in path or "/api/ats/public" in path:
            # Remove X-Frame-Options to allow embedding anywhere
            # Use Content-Security-Policy frame-ancestors instead for better control
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
        else:
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # HSTS - Enable in production
        if os.environ.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

from database import db
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.employees import router as employees_router
from routes.transactions import router as transactions_router
from routes.leave import router as leave_router
from routes.attendance import router as attendance_router
from routes.contracts import router as contracts_router
from routes.stas import router as stas_router
from routes.work_locations import router as work_locations_router
from routes.custody import router as custody_router
from routes.financial_custody import router as financial_custody_router
from routes.settings import router as settings_router
from routes.maintenance import router as maintenance_router
from routes.contracts_v2 import router as contracts_v2_router
from routes.upload import router as upload_router
from routes.announcements import router as announcements_router
from routes.users import router as users_router
from routes.admin import router as admin_router
from routes.settlement import router as settlement_router
from routes.deductions import router as deductions_router
from routes.notifications import router as notifications_router
from routes.attendance_engine import router as attendance_engine_router
from routes.team_attendance import router as team_attendance_router
from routes.penalties import router as penalties_router
from routes.devices import router as devices_router
from routes.tasks import router as tasks_router
from routes.maintenance_tracking import router as maintenance_tracking_router
from routes.admin_custody import router as admin_custody_router
from routes.analytics import router as analytics_router
from routes.performance import router as performance_router
from routes.push_notifications import router as push_router
from routes.company_settings import router as company_settings_router
from routes.ats_admin import router as ats_admin_router
from routes.ats_public import router as ats_public_router
from routes.policies import router as policies_router
from seed import seed_database

# App Version
APP_VERSION = "22.0"

app = FastAPI(title="DAR AL CODE HR OS", version=APP_VERSION, redirect_slashes=False)

# Add Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(employees_router)
app.include_router(transactions_router)
app.include_router(leave_router)
app.include_router(attendance_router)
app.include_router(contracts_router)
app.include_router(stas_router)
app.include_router(work_locations_router)
app.include_router(custody_router)
app.include_router(financial_custody_router)
app.include_router(settings_router)
app.include_router(maintenance_router)
app.include_router(contracts_v2_router)
app.include_router(upload_router)
app.include_router(announcements_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(settlement_router)
app.include_router(deductions_router)
app.include_router(notifications_router)
app.include_router(attendance_engine_router)
app.include_router(team_attendance_router)
app.include_router(penalties_router)
app.include_router(devices_router)
app.include_router(tasks_router)
app.include_router(maintenance_tracking_router)
app.include_router(admin_custody_router)
app.include_router(analytics_router)
app.include_router(performance_router)
app.include_router(push_router)
app.include_router(company_settings_router)
app.include_router(ats_admin_router)
app.include_router(ats_public_router)
app.include_router(policies_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup():
    result = await seed_database(db)
    logger.info(f"Seed: {result['message']}")
    
    # إنشاء سجل الإصدار إذا لم يكن موجوداً
    version_exists = await db.settings.find_one({"type": "app_version"})
    if not version_exists:
        await db.settings.insert_one({
            "type": "app_version",
            "version": APP_VERSION,
            "release_notes_ar": "الإصدار الأولي",
            "release_notes_en": "Initial version",
            "updated_at": None,
            "updated_by": None,
            "version_history": []
        })
        logger.info(f"✅ Created default version record: {APP_VERSION}")
    
    # تشغيل جدولة المهام
    from services.scheduler import init_scheduler
    init_scheduler()
    logger.info("✅ Scheduler initialized")


@app.on_event("shutdown")
async def shutdown():
    from services.scheduler import shutdown_scheduler
    shutdown_scheduler()
    logger.info("🛑 Scheduler stopped")


# Health endpoint for Kubernetes liveness/readiness probes (without /api prefix)
@app.get("/health")
async def health_check():
    # Get version from database if available, fallback to APP_VERSION
    version_info = await db.settings.find_one({"type": "app_version"}, {"_id": 0})
    version = version_info.get("version", APP_VERSION) if version_info else APP_VERSION
    return {"status": "ok", "service": "DAR AL CODE HR OS", "version": version}


@app.get("/api/health")
async def health():
    # Get version from database if available, fallback to APP_VERSION
    version_info = await db.settings.find_one({"type": "app_version"}, {"_id": 0})
    version = version_info.get("version", APP_VERSION) if version_info else APP_VERSION
    return {"status": "ok", "service": "DAR AL CODE HR OS", "version": version}

