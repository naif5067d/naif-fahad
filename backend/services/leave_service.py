"""
Leave Service - نظام الإجازات 21/30
============================================================
- أقل من 5 سنوات = 21 يوم
- 5 سنوات فأكثر = 30 يوم
- الرصيد يُحسب فقط من leave_ledger (credits - debits)
- لا يوجد رصيد مخزن يدوي

المرضية 30/60/30:
- 30 يوم 100%
- 60 يوم 75%
- 30 يوم بدون أجر
- تُحسب تراكمياً خلال 12 شهر متحركة
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from database import db
from services.service_calculator import calculate_service_years, get_employee_service_info


# ============================================================
# LEAVE RULES CONFIGURATION
# ============================================================

ANNUAL_LEAVE_RULES = {
    "under_5_years": 21,  # أقل من 5 سنوات
    "5_years_plus": 30,   # 5 سنوات فأكثر
    "threshold_years": 5  # الحد الفاصل
}

SICK_LEAVE_TIERS = [
    {"days": 30, "pay_percentage": 100, "name": "full_pay", "name_ar": "أجر كامل"},
    {"days": 60, "pay_percentage": 75, "name": "three_quarter_pay", "name_ar": "75% من الأجر"},
    {"days": 30, "pay_percentage": 0, "name": "unpaid", "name_ar": "بدون أجر"},
]

SPECIAL_LEAVE_TYPES = {
    "marriage": {"days": 5, "pay_percentage": 100, "name_ar": "إجازة زواج"},
    "bereavement": {"days": 5, "pay_percentage": 100, "name_ar": "إجازة وفاة"},
    "maternity": {"days": 70, "pay_percentage": 100, "name_ar": "إجازة أمومة"},
    "paternity": {"days": 3, "pay_percentage": 100, "name_ar": "إجازة أبوة"},
    "exam": {"days": -1, "pay_percentage": 100, "name_ar": "إجازة اختبار"},  # -1 = حسب الحاجة
    "unpaid": {"days": -1, "pay_percentage": 0, "name_ar": "إجازة بدون أجر"},
}

# أنواع الإجازات المعتمدة
LEAVE_TYPES = {
    "annual": {"name_ar": "سنوية", "name_en": "Annual"},
    "sick": {"name_ar": "مرضية", "name_en": "Sick"},
    "marriage": {"name_ar": "زواج", "name_en": "Marriage"},
    "bereavement": {"name_ar": "وفاة", "name_en": "Bereavement"},
    "maternity": {"name_ar": "أمومة", "name_en": "Maternity"},
    "paternity": {"name_ar": "أبوة", "name_en": "Paternity"},
    "exam": {"name_ar": "اختبار", "name_en": "Exam"},
    "unpaid": {"name_ar": "بدون أجر", "name_en": "Unpaid"},
    "emergency": {"name_ar": "طارئة", "name_en": "Emergency"},
}


# ============================================================
# LEAVE BALANCE CALCULATION (FROM LEDGER ONLY)
# ============================================================

async def get_leave_balance(employee_id: str, leave_type: str) -> int:
    """
    حساب رصيد الإجازات من leave_ledger فقط
    الرصيد = sum(credits) - sum(debits)
    
    Args:
        employee_id: معرف الموظف
        leave_type: نوع الإجازة
        
    Returns:
        int: الرصيد المتبقي
    """
    entries = await db.leave_ledger.find(
        {"employee_id": employee_id, "leave_type": leave_type}, 
        {"_id": 0}
    ).to_list(5000)
    
    balance = 0
    for entry in entries:
        if entry.get('type') == 'credit':
            balance += entry.get('days', 0)
        else:  # debit
            balance -= entry.get('days', 0)
    
    return balance


async def get_all_leave_balances(employee_id: str) -> Dict[str, int]:
    """
    جلب جميع أرصدة الإجازات للموظف
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: {leave_type: balance}
    """
    balances = {}
    
    for leave_type in LEAVE_TYPES.keys():
        balances[leave_type] = await get_leave_balance(employee_id, leave_type)
    
    return balances


# ============================================================
# ANNUAL LEAVE ENTITLEMENT (21/30)
# ============================================================

async def calculate_annual_entitlement(employee_id: str) -> dict:
    """
    حساب استحقاق الإجازة السنوية بناءً على سنوات الخدمة
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: {
            entitlement: عدد أيام الاستحقاق السنوي,
            service_years: سنوات الخدمة,
            rule_applied: القاعدة المطبقة
        }
    """
    service_info = await get_employee_service_info(employee_id)
    
    if not service_info:
        return {
            "entitlement": 0,
            "service_years": 0,
            "rule_applied": "no_active_contract",
            "message_ar": "لا يوجد عقد نشط"
        }
    
    years = service_info['service']['years']
    
    if years >= ANNUAL_LEAVE_RULES['threshold_years']:
        entitlement = ANNUAL_LEAVE_RULES['5_years_plus']
        rule_applied = "5_years_plus"
        message_ar = f"5 سنوات فأكثر = {entitlement} يوم"
    else:
        entitlement = ANNUAL_LEAVE_RULES['under_5_years']
        rule_applied = "under_5_years"
        message_ar = f"أقل من 5 سنوات = {entitlement} يوم"
    
    return {
        "entitlement": entitlement,
        "service_years": years,
        "rule_applied": rule_applied,
        "message_ar": message_ar
    }


async def calculate_monthly_accrual(employee_id: str) -> dict:
    """
    حساب الاستحقاق الشهري للإجازة السنوية
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: تفاصيل الاستحقاق الشهري
    """
    annual = await calculate_annual_entitlement(employee_id)
    
    if annual['entitlement'] == 0:
        return {
            "monthly_accrual": 0,
            "daily_accrual": 0,
            **annual
        }
    
    monthly = annual['entitlement'] / 12
    daily = annual['entitlement'] / 365
    
    return {
        "annual_entitlement": annual['entitlement'],
        "monthly_accrual": round(monthly, 2),
        "daily_accrual": round(daily, 4),
        "service_years": annual['service_years'],
        "rule_applied": annual['rule_applied'],
        "message_ar": annual['message_ar']
    }


# ============================================================
# SICK LEAVE TIERS (30/60/30)
# ============================================================

async def get_sick_leave_usage_12_months(employee_id: str) -> dict:
    """
    حساب استخدام الإجازة المرضية خلال آخر 12 شهر متحركة
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: تفاصيل الاستخدام حسب الشرائح
    """
    # حساب فترة 12 شهر
    today = datetime.now(timezone.utc)
    year_ago = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    # جلب سجلات الإجازة المرضية
    entries = await db.leave_ledger.find({
        "employee_id": employee_id,
        "leave_type": "sick",
        "type": "debit",
        "date": {"$gte": year_ago, "$lte": today_str}
    }, {"_id": 0}).to_list(1000)
    
    total_used = sum(e.get('days', 0) for e in entries)
    
    # توزيع على الشرائح
    remaining = total_used
    usage_breakdown = []
    current_tier_index = 0
    
    for i, tier in enumerate(SICK_LEAVE_TIERS):
        tier_limit = tier['days']
        used_in_tier = min(remaining, tier_limit) if remaining > 0 else 0
        remaining_in_tier = tier_limit - used_in_tier
        
        usage_breakdown.append({
            "tier": tier['name'],
            "tier_ar": tier['name_ar'],
            "pay_percentage": tier['pay_percentage'],
            "limit": tier_limit,
            "used": used_in_tier,
            "remaining": remaining_in_tier
        })
        
        if remaining > 0:
            remaining -= used_in_tier
            if used_in_tier >= tier_limit:
                current_tier_index = i + 1
    
    # الشريحة الحالية
    if current_tier_index >= len(SICK_LEAVE_TIERS):
        current_tier = {
            "name": "exhausted",
            "name_ar": "استنفدت",
            "pay_percentage": 0
        }
    else:
        current_tier = SICK_LEAVE_TIERS[current_tier_index]
    
    return {
        "total_used_12_months": total_used,
        "total_limit": sum(t['days'] for t in SICK_LEAVE_TIERS),
        "usage_breakdown": usage_breakdown,
        "current_tier": {
            "index": current_tier_index,
            "name": current_tier['name'],
            "name_ar": current_tier.get('name_ar', current_tier['name']),
            "pay_percentage": current_tier['pay_percentage']
        },
        "period": {
            "from": year_ago,
            "to": today_str
        }
    }


async def calculate_sick_leave_pay(employee_id: str, days_requested: int) -> dict:
    """
    حساب نسبة الأجر للإجازة المرضية المطلوبة
    
    Args:
        employee_id: معرف الموظف
        days_requested: عدد الأيام المطلوبة
        
    Returns:
        dict: توزيع الأيام حسب نسب الأجر
    """
    usage = await get_sick_leave_usage_12_months(employee_id)
    
    days_by_pay = []
    remaining_days = days_requested
    current_tier = usage['current_tier']['index']
    
    for i in range(current_tier, len(SICK_LEAVE_TIERS)):
        if remaining_days <= 0:
            break
        
        tier = SICK_LEAVE_TIERS[i]
        tier_remaining = usage['usage_breakdown'][i]['remaining']
        
        days_in_tier = min(remaining_days, tier_remaining)
        
        if days_in_tier > 0:
            days_by_pay.append({
                "days": days_in_tier,
                "pay_percentage": tier['pay_percentage'],
                "tier_ar": tier['name_ar']
            })
            remaining_days -= days_in_tier
    
    return {
        "days_requested": days_requested,
        "days_breakdown": days_by_pay,
        "current_usage": usage
    }


# ============================================================
# LEAVE COMPENSATION (FOR SETTLEMENT)
# ============================================================

async def calculate_leave_compensation(employee_id: str, daily_wage: float) -> dict:
    """
    حساب بدل الإجازات للمخالصة
    
    Args:
        employee_id: معرف الموظف
        daily_wage: الأجر اليومي
        
    Returns:
        dict: تفاصيل بدل الإجازات
    """
    balance = await get_leave_balance(employee_id, 'annual')
    
    compensation = balance * daily_wage if balance > 0 else 0
    
    return {
        "leave_balance": balance,
        "daily_wage": daily_wage,
        "compensation": round(compensation, 2),
        "formula": f"{balance} يوم × {daily_wage:,.2f} ر.س = {compensation:,.2f} ر.س"
    }


# ============================================================
# LEAVE SUMMARY FOR EMPLOYEE
# ============================================================

async def get_employee_leave_summary(employee_id: str) -> dict:
    """
    ملخص شامل لحالة إجازات الموظف
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: ملخص كامل
    """
    # الأرصدة
    balances = await get_all_leave_balances(employee_id)
    
    # الاستحقاق السنوي
    annual_entitlement = await calculate_annual_entitlement(employee_id)
    
    # الإجازة المرضية
    sick_usage = await get_sick_leave_usage_12_months(employee_id)
    
    # حساب نسبة الاستهلاك
    annual_balance = balances.get('annual', 0)
    annual_total = annual_entitlement.get('entitlement', 21)
    consumption_rate = ((annual_total - annual_balance) / annual_total * 100) if annual_total > 0 else 0
    
    return {
        "employee_id": employee_id,
        "balances": balances,
        "annual_leave": {
            "balance": annual_balance,
            "entitlement": annual_total,
            "used": annual_total - annual_balance,
            "consumption_rate": round(consumption_rate, 1),
            "rule": annual_entitlement.get('rule_applied'),
            "service_years": annual_entitlement.get('service_years', 0)
        },
        "sick_leave": {
            "used_12_months": sick_usage['total_used_12_months'],
            "total_limit": sick_usage['total_limit'],
            "current_tier": sick_usage['current_tier'],
            "breakdown": sick_usage['usage_breakdown']
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
