from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from database import db
from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.employees import router as employees_router
from routes.transactions import router as transactions_router
from routes.leave import router as leave_router
from routes.attendance import router as attendance_router
from routes.finance import router as finance_router
from routes.contracts import router as contracts_router
from routes.stas import router as stas_router
from routes.work_locations import router as work_locations_router
from routes.custody import router as custody_router
from routes.financial_custody import router as financial_custody_router
from routes.settings import router as settings_router
from routes.maintenance import router as maintenance_router
from routes.contracts_v2 import router as contracts_v2_router
from routes.upload import router as upload_router
from seed import seed_database

app = FastAPI(title="DAR AL CODE HR OS", redirect_slashes=False)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(employees_router)
app.include_router(transactions_router)
app.include_router(leave_router)
app.include_router(attendance_router)
app.include_router(finance_router)
app.include_router(contracts_router)
app.include_router(stas_router)
app.include_router(work_locations_router)
app.include_router(custody_router)
app.include_router(financial_custody_router)
app.include_router(settings_router)
app.include_router(maintenance_router)
app.include_router(contracts_v2_router)

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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "DAR AL CODE HR OS"}
