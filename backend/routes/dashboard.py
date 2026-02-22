from fastapi import APIRouter, Depends
from database import db
from utils.auth import get_current_user
from datetime import datetime, timezone

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    role = user.get('role')
    user_id = user.get('user_id')
    stats = {}

    if role == 'employee':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        emp_id = emp['id'] if emp else None
        stats['pending_transactions'] = await db.transactions.count_documents(
            {"employee_id": emp_id, "status": {"$nin": ["executed", "rejected", "cancelled"]}}
        )
        leave_entries = await db.leave_ledger.find({"employee_id": emp_id, "leave_type": "annual"}, {"_id": 0, "days": 1, "type": 1}).to_list(1000)
        balance = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in leave_entries)
        stats['leave_balance'] = balance

    elif role == 'supervisor':
        emp = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
        emp_id = emp['id'] if emp else None
        
        # رصيد الإجازات الخاص بالمشرف نفسه
        leave_entries = await db.leave_ledger.find({"employee_id": emp_id, "leave_type": "annual"}, {"_id": 0, "days": 1, "type": 1}).to_list(1000)
        stats['leave_balance'] = sum(e['days'] if e['type'] == 'credit' else -e['days'] for e in leave_entries)
        
        # فريق العمل
        direct_reports = await db.employees.find({"supervisor_id": emp_id}, {"_id": 0, "id": 1, "full_name": 1}).to_list(100)
        dr_ids = [d['id'] for d in direct_reports]
        stats['team_size'] = len(direct_reports)
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "supervisor", "employee_id": {"$in": dr_ids}, "status": {"$nin": ["executed", "rejected"]}}
        )

    elif role in ('sultan', 'naif'):
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "ops", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})
        stats['total_transactions'] = await db.transactions.count_documents({})

    elif role == 'salah':
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "finance", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['pending_custody_audit'] = await db.custody_financial.count_documents({"status": "pending_audit"})
        stats['total_finance_entries'] = await db.finance_ledger.count_documents({})

    elif role == 'mohammed':
        stats['pending_approvals'] = await db.transactions.count_documents(
            {"current_stage": "ceo", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['pending_custody_approval'] = await db.custody_financial.count_documents({"status": "pending_approval"})
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})

    elif role == 'stas':
        stats['pending_execution'] = await db.transactions.count_documents(
            {"current_stage": "stas", "status": {"$nin": ["executed", "rejected"]}}
        )
        stats['pending_custody_execution'] = await db.custody_financial.count_documents({"status": "pending_stas"})
        stats['total_transactions'] = await db.transactions.count_documents({})
        stats['total_employees'] = await db.employees.count_documents({"is_active": True})

    return stats


@router.get("/next-holiday")
async def get_next_holiday(user=Depends(get_current_user)):
    """Get the next upcoming official holiday with relative date info."""
    from datetime import timedelta
    from hijri_converter import Hijri, Gregorian
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Check public holidays first
    holiday = await db.public_holidays.find_one(
        {"date": {"$gte": today}},
        {"_id": 0},
        sort=[("date", 1)]
    )
    if not holiday:
        # Try manual holidays
        holiday = await db.holidays.find_one(
            {"date": {"$gte": today}},
            {"_id": 0},
            sort=[("date", 1)]
        )
    
    if not holiday:
        return None
    
    # Add relative date info
    holiday_date = holiday.get('date', '')
    
    # Determine if today, tomorrow, or future
    if holiday_date == today:
        holiday['relative'] = 'today'
        holiday['relative_ar'] = 'اليوم'
    elif holiday_date == tomorrow:
        holiday['relative'] = 'tomorrow'
        holiday['relative_ar'] = 'غداً'
    else:
        holiday['relative'] = 'upcoming'
        holiday['relative_ar'] = 'قادمة'
    
    # Convert to Hijri date
    try:
        year, month, day = map(int, holiday_date.split('-'))
        hijri = Gregorian(year, month, day).to_hijri()
        hijri_months_ar = ['محرم', 'صفر', 'ربيع الأول', 'ربيع الآخر', 'جمادى الأولى', 
                          'جمادى الآخرة', 'رجب', 'شعبان', 'رمضان', 'شوال', 'ذو القعدة', 'ذو الحجة']
        holiday['hijri_date'] = f"{hijri.day} {hijri_months_ar[hijri.month - 1]} {hijri.year}"
        holiday['hijri_date_short'] = f"{hijri.day}/{hijri.month}/{hijri.year}"
    except:
        holiday['hijri_date'] = ''
        holiday['hijri_date_short'] = ''
    
    return holiday
