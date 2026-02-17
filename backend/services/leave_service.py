"""
Leave Service - نظام الإجازات المحدث
============================================================
Version: 2.0.0 - Pro-Rata + HR Policy Integration
============================================================
نوع الإجازة | الأيام | الأجر | الرصيد
============================================================
السنوية    | 21/30  | 100%  | Pro-Rata يومي
المرضية    | 30/60/30 | 100%/75%/0% | عداد تراكمي
الزواج     | 5      | 100%  | لا يُخصم من السنوية
الوفاة     | 5      | 100%  | لا يُخصم من السنوية
الاختبار   | حسب الإثبات | 100% | لا يُخصم من السنوية
بدون راتب  | حسب الحاجة | 0% | لا يُخصم من السنوية

ملاحظات مهمة:
- الرصيد الوحيد المتتبع هو الإجازة السنوية (Pro-Rata)
- الخصم يتم فقط عند STAS Execute
- لا ترحيل تلقائي للإجازات
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from database import db
from services.service_calculator import calculate_service_years, get_employee_service_info
from services.hr_policy import (
    calculate_pro_rata_entitlement,
    get_annual_leave_balance_v2,
    get_employee_annual_policy,
    check_blocking_transaction,
    DEFAULT_ANNUAL_ENTITLEMENT,
    EXTENDED_ANNUAL_ENTITLEMENT,
    FIXED_LEAVE_DAYS,
    ADMIN_LEAVE_TYPES
)


# ============================================================
# تعريفات الإجازات
# ============================================================

# أنواع الإجازات المعتمدة مع القواعد
LEAVE_TYPES = {
    "annual": {
        "name_ar": "الإجازة السنوية",
        "name_en": "Annual Leave",
        "has_balance": True,  # الوحيد الذي له رصيد
        "pay_percentage": 100,
        "deduct_from_annual": False,  # لا يُخصم من نفسه
        "requires_attachment": False,
    },
    "sick": {
        "name_ar": "الإجازة المرضية",
        "name_en": "Sick Leave",
        "has_balance": False,  # عداد وليس رصيد
        "pay_percentage": "tiered",  # حسب الشرائح
        "deduct_from_annual": False,
        "requires_attachment": True,  # يتطلب مرفق من صحتي
        "attachment_source": "صحتي",
    },
    "marriage": {
        "name_ar": "إجازة الزواج",
        "name_en": "Marriage Leave",
        "has_balance": False,
        "fixed_days": 5,
        "pay_percentage": 100,
        "deduct_from_annual": False,
        "once_per_employee": True,  # مرة واحدة فقط
    },
    "bereavement": {
        "name_ar": "إجازة الوفاة",
        "name_en": "Bereavement Leave",
        "has_balance": False,
        "fixed_days": 5,
        "pay_percentage": 100,
        "deduct_from_annual": False,
    },
    "exam": {
        "name_ar": "إجازة الاختبار",
        "name_en": "Exam Leave",
        "has_balance": False,
        "fixed_days": -1,  # حسب الإثبات
        "pay_percentage": 100,
        "deduct_from_annual": False,
        "requires_attachment": True,
    },
    "unpaid": {
        "name_ar": "إجازة بدون راتب",
        "name_en": "Unpaid Leave",
        "has_balance": False,
        "pay_percentage": 0,
        "deduct_from_annual": False,
        "track_days": True,  # تُحسب الأيام فقط
    },
}

# قواعد الإجازة السنوية 21/30 - من HR Policy
ANNUAL_LEAVE_RULES = {
    "default": DEFAULT_ANNUAL_ENTITLEMENT,  # 21 يوم
    "extended": EXTENDED_ANNUAL_ENTITLEMENT,  # 30 يوم
}

# شرائح الإجازة المرضية 30/60/30
SICK_LEAVE_TIERS = [
    {"days": 30, "pay_percentage": 100, "name": "full_pay", "name_ar": "أجر كامل (30 يوم)"},
    {"days": 60, "pay_percentage": 75, "name": "three_quarter_pay", "name_ar": "75% من الأجر (60 يوم)"},
    {"days": 30, "pay_percentage": 0, "name": "unpaid", "name_ar": "بدون أجر (30 يوم)"},
]


# ============================================================
# حساب رصيد الإجازة السنوية (Pro-Rata الجديد)
# ============================================================

async def get_annual_leave_balance(employee_id: str) -> float:
    """
    حساب رصيد الإجازة السنوية باستخدام Pro-Rata
    المعادلة: earned_to_date - used_executed
    
    Returns:
        float: الرصيد المتاح (2 decimals)
    """
    return await get_annual_leave_balance_v2(employee_id)


async def get_leave_balance(employee_id: str, leave_type: str) -> float:
    """
    حساب رصيد الإجازة - فقط للسنوية
    باقي الأنواع ليس لها رصيد (مسار إداري)
    """
    if leave_type != 'annual':
        return 0.0  # لا رصيد لغير السنوية
    
    return await get_annual_leave_balance(employee_id)


async def get_all_leave_balances(employee_id: str) -> Dict[str, float]:
    """
    جلب الأرصدة - فقط السنوية لها رصيد
    """
    annual_balance = await get_annual_leave_balance(employee_id)
    
    return {
        "annual": round(annual_balance, 2),
        "sick": 0,
        "marriage": 0,
        "bereavement": 0,
        "exam": 0,
        "unpaid": 0,
    }


# ============================================================
# استحقاق الإجازة السنوية (Pro-Rata)
# ============================================================

async def calculate_annual_entitlement(employee_id: str) -> dict:
    """
    حساب استحقاق الإجازة السنوية باستخدام Pro-Rata
    
    المعادلات:
    - annual_entitlement_year = 21 أو 30 (من العقد أو قرار إداري)
    - daily_accrual = annual_entitlement_year / days_in_year
    - earned_to_date = daily_accrual * days_worked_in_year
    """
    pro_rata = await calculate_pro_rata_entitlement(employee_id)
    
    if pro_rata.get('error'):
        return {
            "entitlement": 0,
            "service_years": 0,
            "rule_applied": "no_active_contract",
            "message_ar": pro_rata.get('message_ar', 'لا يوجد عقد نشط')
        }
    
    policy = await get_employee_annual_policy(employee_id)
    
    return {
        "entitlement": pro_rata.get('annual_policy_days', DEFAULT_ANNUAL_ENTITLEMENT),
        "earned_to_date": pro_rata.get('earned_to_date', 0),
        "available_balance": pro_rata.get('available_balance', 0),
        "used": pro_rata.get('used_executed', 0),
        "daily_accrual": pro_rata.get('daily_accrual', 0),
        "days_worked": pro_rata.get('days_worked', 0),
        "rule_applied": f"{policy['source']}_{policy['days']}",
        "policy_source": policy['source'],
        "policy_source_ar": policy['source_ar'],
        "formula": pro_rata.get('formula', ''),
        "message_ar": pro_rata.get('message_ar', '')
    }


async def calculate_monthly_accrual(employee_id: str) -> dict:
    """
    حساب الاستحقاق الشهري للإجازة السنوية
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
# عداد الإجازة المرضية (30/60/30)
# ============================================================

async def get_sick_leave_usage_12_months(employee_id: str) -> dict:
    """
    حساب استخدام الإجازة المرضية خلال آخر 12 شهر متحركة
    
    الشرائح:
    - 30 يوم الأولى: 100% من الأجر
    - 60 يوم التالية: 75% من الأجر
    - 30 يوم الأخيرة: بدون أجر
    
    المجموع: 120 يوم كحد أقصى خلال 12 شهر
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
            "name_ar": "استُنفدت جميع الشرائح",
            "pay_percentage": 0
        }
    else:
        current_tier = SICK_LEAVE_TIERS[current_tier_index]
    
    return {
        "total_used_12_months": total_used,
        "total_limit": sum(t['days'] for t in SICK_LEAVE_TIERS),  # 120 يوم
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
# التحقق من صحة طلب الإجازة
# ============================================================

async def validate_leave_request(
    employee_id: str, 
    leave_type: str, 
    days_requested: int,
    has_attachment: bool = False
) -> dict:
    """
    التحقق من صحة طلب الإجازة
    
    Returns:
        dict: {valid: bool, errors: list, warnings: list}
    """
    errors = []
    warnings = []
    
    leave_config = LEAVE_TYPES.get(leave_type)
    if not leave_config:
        errors.append(f"نوع إجازة غير معروف: {leave_type}")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # التحقق من المرفقات المطلوبة
    if leave_config.get('requires_attachment') and not has_attachment:
        if leave_type == 'sick':
            errors.append("الإجازة المرضية تتطلب مرفق من تطبيق صحتي")
        elif leave_type == 'exam':
            errors.append("إجازة الاختبار تتطلب إثبات موعد الاختبار")
    
    # التحقق من الرصيد للإجازة السنوية فقط
    if leave_type == 'annual':
        balance = await get_annual_leave_balance(employee_id)
        if days_requested > balance:
            errors.append(f"رصيد الإجازة السنوية غير كافٍ. المتاح: {balance} يوم، المطلوب: {days_requested} يوم")
    
    # التحقق من شرائح الإجازة المرضية
    elif leave_type == 'sick':
        sick_usage = await get_sick_leave_usage_12_months(employee_id)
        total_available = sick_usage['total_limit'] - sick_usage['total_used_12_months']
        
        if days_requested > total_available:
            errors.append(f"تجاوزت الحد المسموح للإجازة المرضية. المتبقي: {total_available} يوم")
        
        # تحذير إذا كان سيدخل في شريحة بدون أجر
        pay_calc = await calculate_sick_leave_pay(employee_id, days_requested)
        unpaid_days = sum(d['days'] for d in pay_calc['days_breakdown'] if d['pay_percentage'] == 0)
        if unpaid_days > 0:
            warnings.append(f"ستكون {unpaid_days} يوم من هذه الإجازة بدون أجر")
    
    # التحقق من الإجازات ذات الأيام الثابتة
    elif leave_config.get('fixed_days', -1) > 0:
        if days_requested > leave_config['fixed_days']:
            errors.append(f"{leave_config['name_ar']} لا تتجاوز {leave_config['fixed_days']} أيام")
    
    # التحقق من إجازة الزواج (مرة واحدة فقط)
    if leave_type == 'marriage':
        existing = await db.leave_ledger.find_one({
            "employee_id": employee_id,
            "leave_type": "marriage",
            "type": "debit"
        })
        if existing:
            errors.append("إجازة الزواج تُمنح مرة واحدة فقط")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


# ============================================================
# حساب بدل الإجازات للمخالصة
# ============================================================

async def calculate_leave_compensation(employee_id: str, daily_wage: float) -> dict:
    """
    حساب بدل الإجازات للمخالصة
    يُحسب فقط للإجازة السنوية المتبقية
    """
    balance = await get_annual_leave_balance(employee_id)
    
    compensation = balance * daily_wage if balance > 0 else 0
    
    return {
        "leave_balance": balance,
        "daily_wage": daily_wage,
        "compensation": round(compensation, 2),
        "formula": f"{balance} يوم × {daily_wage:,.2f} ر.س = {compensation:,.2f} ر.س",
        "note_ar": "بدل الإجازة السنوية المتبقية فقط"
    }


# ============================================================
# ملخص شامل لحالة إجازات الموظف
# ============================================================

async def get_employee_leave_summary(employee_id: str) -> dict:
    """
    ملخص شامل لحالة إجازات الموظف
    """
    # رصيد الإجازة السنوية
    annual_balance = await get_annual_leave_balance(employee_id)
    
    # استحقاق الإجازة السنوية
    annual_entitlement = await calculate_annual_entitlement(employee_id)
    
    # عداد الإجازة المرضية
    sick_usage = await get_sick_leave_usage_12_months(employee_id)
    
    # حساب نسبة الاستهلاك
    annual_total = annual_entitlement.get('entitlement', 21)
    consumption_rate = ((annual_total - annual_balance) / annual_total * 100) if annual_total > 0 else 0
    
    # إحصائيات الإجازات الأخرى
    other_leaves = {}
    for leave_type in ['marriage', 'bereavement', 'exam', 'unpaid']:
        count = await db.leave_ledger.count_documents({
            "employee_id": employee_id,
            "leave_type": leave_type,
            "type": "debit"
        })
        days = 0
        if count > 0:
            entries = await db.leave_ledger.find({
                "employee_id": employee_id,
                "leave_type": leave_type,
                "type": "debit"
            }, {"_id": 0}).to_list(100)
            days = sum(e.get('days', 0) for e in entries)
        
        other_leaves[leave_type] = {
            "name_ar": LEAVE_TYPES[leave_type]['name_ar'],
            "count": count,
            "total_days": days
        }
    
    return {
        "employee_id": employee_id,
        "annual_leave": {
            "balance": annual_balance,
            "entitlement": annual_total,
            "used": annual_total - annual_balance,
            "consumption_rate": round(consumption_rate, 1),
            "rule": annual_entitlement.get('rule_applied'),
            "service_years": annual_entitlement.get('service_years', 0),
            "message_ar": annual_entitlement.get('message_ar', '')
        },
        "sick_leave": {
            "used_12_months": sick_usage['total_used_12_months'],
            "total_limit": sick_usage['total_limit'],
            "remaining": sick_usage['total_limit'] - sick_usage['total_used_12_months'],
            "current_tier": sick_usage['current_tier'],
            "breakdown": sick_usage['usage_breakdown'],
            "note_ar": "عداد تراكمي خلال 12 شهر - لا يُخصم من السنوية"
        },
        "other_leaves": other_leaves,
        "notes_ar": [
            "الرصيد الوحيد المتتبع هو الإجازة السنوية",
            "الإجازة المرضية: عداد تراكمي (30 يوم 100% + 60 يوم 75% + 30 يوم بدون أجر)",
            "إجازة الزواج والوفاة: 5 أيام مدفوعة - لا تُخصم من السنوية",
            "إجازة الاختبار: حسب الإثبات - مدفوعة",
            "إجازة بدون راتب: لا أجر ولا خصم من السنوية"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
