"""
Scheduler Service - جدولة المهام التلقائية
- التحضير الذاتي في بداية كل يوم عمل (7:00 صباحاً)
- ملخص الحضور الشهري (أول كل شهر)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def run_daily_auto_attendance():
    """
    التحضير الذاتي - يعمل في بداية كل يوم عمل
    
    المنطق:
    1. ينشئ سجلات حضور لجميع الموظفين لليوم الحالي
    2. يتحقق من العطلات الرسمية وعطلة نهاية الأسبوع
    3. يضع الحالة المناسبة تلقائياً
    """
    from services.day_resolver_v2 import resolve_and_save_v2
    from database import db
    
    # معالجة اليوم الحالي
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    logger.info(f"⏰ بدء التحضير الذاتي لليوم: {today}")
    
    try:
        # الحصول على جميع الموظفين النشطين (باستثناء المستخدمين الإداريين)
        excluded_ids = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-SALAH', 'EMP-NAIF', 'EMP-SULTAN']
        
        employees = await db.employees.find({
            "is_active": {"$ne": False},
            "id": {"$nin": excluded_ids}
        }, {"_id": 0, "id": 1}).to_list(None)
        
        created = 0
        updated = 0
        skipped_holiday = 0
        skipped_weekend = 0
        skipped_existing = 0
        errors = []
        
        for emp in employees:
            try:
                result = await resolve_and_save_v2(emp['id'], today)
                action = result.get('action', 'created')
                status = result.get('status', '')
                
                if action == 'created':
                    created += 1
                elif action == 'updated':
                    updated += 1
                elif action == 'skipped':
                    if 'holiday' in status.lower():
                        skipped_holiday += 1
                    elif 'weekend' in status.lower():
                        skipped_weekend += 1
                    else:
                        skipped_existing += 1
                elif action == 'kept':
                    skipped_existing += 1
                    
            except Exception as e:
                errors.append({"employee_id": emp['id'], "error": str(e)})
                logger.error(f"خطأ في معالجة {emp['id']}: {e}")
        
        # تسجيل النتيجة
        await db.job_logs.insert_one({
            "job_type": "daily_auto_attendance",
            "date": today,
            "created_count": created,
            "updated_count": updated,
            "skipped_holiday": skipped_holiday,
            "skipped_weekend": skipped_weekend,
            "skipped_existing": skipped_existing,
            "total_employees": len(employees),
            "error_count": len(errors),
            "errors": errors,
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "status": "success" if len(errors) == 0 else "partial"
        })
        
        logger.info(f"✅ تم التحضير الذاتي: جديد={created}, تحديث={updated}, عطلة={skipped_holiday}, نهاية أسبوع={skipped_weekend}, موجود={skipped_existing}, أخطاء={len(errors)}")
        
    except Exception as e:
        logger.error(f"❌ فشل في التحضير الذاتي: {e}")
        await db.job_logs.insert_one({
            "job_type": "daily_auto_attendance",
            "date": today,
            "status": "failed",
            "error": str(e),
            "executed_at": datetime.now(timezone.utc).isoformat()
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
    # التحضير الذاتي - كل يوم الساعة 7:00 صباحاً (توقيت الرياض = 04:00 UTC)
    scheduler.add_job(
        run_daily_auto_attendance,
        CronTrigger(hour=4, minute=0),  # 7 AM Riyadh time (UTC+3)
        id='daily_auto_attendance',
        name='Daily Auto Attendance',
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
    logger.info("✅ تم تشغيل جدولة المهام - التحضير الذاتي 7:00 صباحاً")


def shutdown_scheduler():
    """إيقاف الـ scheduler"""
    scheduler.shutdown(wait=False)
    logger.info("🛑 تم إيقاف جدولة المهام")
