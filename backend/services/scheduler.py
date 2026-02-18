"""
Scheduler Service - جدولة المهام التلقائية
- معالجة الحضور اليومي (بعد منتصف الليل)
- ملخص الحضور الشهري (أول كل شهر)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()

async def run_daily_attendance_job():
    """تشغيل معالجة الحضور اليومي"""
    from services.day_resolver_v2 import resolve_and_save_v2
    from database import db
    
    # معالجة يوم الأمس
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"⏰ بدء المعالجة اليومية للحضور: {yesterday}")
    
    try:
        # الحصول على جميع الموظفين النشطين (باستثناء المستخدمين الإداريين)
        excluded_ids = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF', 'EMP-SULTAN']
        
        employees = await db.employees.find({
            "is_active": {"$ne": False},
            "id": {"$nin": excluded_ids}
        }, {"_id": 0, "id": 1}).to_list(None)
        
        processed = 0
        errors = []
        
        for emp in employees:
            try:
                await resolve_and_save_v2(emp['id'], yesterday)
                processed += 1
            except Exception as e:
                errors.append({"employee_id": emp['id'], "error": str(e)})
                logger.error(f"خطأ في معالجة {emp['id']}: {e}")
        
        # تسجيل النتيجة
        await db.job_logs.insert_one({
            "job_type": "daily_attendance",
            "date": yesterday,
            "processed_count": processed,
            "error_count": len(errors),
            "errors": errors,
            "executed_at": datetime.utcnow().isoformat(),
            "status": "success" if len(errors) == 0 else "partial"
        })
        
        logger.info(f"✅ تمت المعالجة اليومية: {processed} موظف، {len(errors)} خطأ")
        
    except Exception as e:
        logger.error(f"❌ فشل في المعالجة اليومية: {e}")
        await db.job_logs.insert_one({
            "job_type": "daily_attendance",
            "date": yesterday,
            "status": "failed",
            "error": str(e),
            "executed_at": datetime.utcnow().isoformat()
        })


async def run_monthly_summary_job():
    """تشغيل ملخص الحضور الشهري"""
    from services.penalty_service import generate_monthly_penalties
    from database import db
    
    # الشهر السابق
    today = datetime.now()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    year = last_month_end.year
    month = last_month_end.month
    
    logger.info(f"⏰ بدء الملخص الشهري: {year}-{month:02d}")
    
    try:
        # الحصول على جميع الموظفين النشطين
        excluded_ids = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF', 'EMP-SULTAN']
        
        employees = await db.employees.find({
            "is_active": {"$ne": False},
            "id": {"$nin": excluded_ids}
        }, {"_id": 0, "id": 1}).to_list(None)
        
        processed = 0
        proposals_created = 0
        
        for emp in employees:
            try:
                result = await generate_monthly_penalties(emp['id'], year, month)
                processed += 1
                if result.get('proposals_created'):
                    proposals_created += result['proposals_created']
            except Exception as e:
                logger.error(f"خطأ في ملخص {emp['id']}: {e}")
        
        # تسجيل النتيجة
        await db.job_logs.insert_one({
            "job_type": "monthly_summary",
            "year": year,
            "month": month,
            "processed_count": processed,
            "proposals_created": proposals_created,
            "executed_at": datetime.utcnow().isoformat(),
            "status": "success"
        })
        
        logger.info(f"✅ تم الملخص الشهري: {processed} موظف، {proposals_created} اقتراح خصم")
        
    except Exception as e:
        logger.error(f"❌ فشل في الملخص الشهري: {e}")


def init_scheduler():
    """تهيئة وتشغيل الـ scheduler"""
    # المعالجة اليومية - كل يوم الساعة 1:00 صباحاً (توقيت الرياض = 22:00 UTC)
    scheduler.add_job(
        run_daily_attendance_job,
        CronTrigger(hour=22, minute=0),  # 1 AM Riyadh time
        id='daily_attendance',
        name='Daily Attendance Processing',
        replace_existing=True
    )
    
    # الملخص الشهري - أول كل شهر الساعة 3:00 صباحاً (توقيت الرياض = 00:00 UTC)
    scheduler.add_job(
        run_monthly_summary_job,
        CronTrigger(day=1, hour=0, minute=0),  # 3 AM Riyadh time on 1st
        id='monthly_summary',
        name='Monthly Attendance Summary',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ تم تشغيل جدولة المهام")


def shutdown_scheduler():
    """إيقاف الـ scheduler"""
    scheduler.shutdown(wait=False)
    logger.info("🛑 تم إيقاف جدولة المهام")
