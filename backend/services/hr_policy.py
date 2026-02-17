"""
HR Policy Engine - سياسة الموارد البشرية الشاملة
============================================================
Version: 1.0.0
Last Updated: 2026-02-17

هذا الملف يحتوي على:
1. معادلة الاستحقاق السنوي (Pro-Rata)
2. قواعد 21/30 يوم
3. منع الترحيل + تنبيهات
4. قواعد Blocking
5. قواعد عرض التصعيد
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from database import db
import calendar


# ============================================================
# ثوابت السياسة
# ============================================================

# الاستحقاق السنوي الافتراضي
DEFAULT_ANNUAL_ENTITLEMENT = 21  # يوم - الافتراضي
EXTENDED_ANNUAL_ENTITLEMENT = 30  # يوم - بقرار إداري أو عقد

# عتبة سنوات الخدمة للترقية إلى 30 يوم (اختياري)
SERVICE_YEARS_THRESHOLD = 5

# أيام التنبيه قبل نهاية العقد/السنة
ALERT_DAYS_BEFORE_END = 90  # 3 أشهر

# الإجازات الإدارية (لا تُخصم من السنوية)
ADMIN_LEAVE_TYPES = ['bereavement', 'marriage', 'exam', 'sick', 'unpaid']

# أيام الإجازات الثابتة
FIXED_LEAVE_DAYS = {
    'bereavement': 5,  # وفاة
    'marriage': 5,     # زواج
}


# ============================================================
# 1. معادلة الاستحقاق السنوي (Pro-Rata)
# ============================================================

async def calculate_pro_rata_entitlement(employee_id: str, year: int = None) -> dict:
    """
    حساب الاستحقاق السنوي التدريجي (Pro-Rata)
    
    المعادلات:
    - annual_entitlement_year = 21 أو 30 (من العقد أو قرار إداري)
    - daily_accrual = annual_entitlement_year / days_in_year
    - earned_to_date = daily_accrual * days_worked_in_year
    - available_balance = earned_to_date - used_approved_executed
    
    Args:
        employee_id: معرف الموظف
        year: السنة (افتراضي: السنة الحالية)
    
    Returns:
        dict: تفاصيل الاستحقاق
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    # 1. جلب العقد النشط
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0})
    
    if not contract:
        # جرب العقد القديم
        contract = await db.contracts.find_one({
            "employee_id": employee_id,
            "is_active": True
        }, {"_id": 0})
    
    if not contract:
        return {
            "error": True,
            "message_ar": "لا يوجد عقد نشط",
            "annual_entitlement": 0,
            "earned_to_date": 0,
            "available_balance": 0
        }
    
    # 2. تحديد الاستحقاق السنوي (21 أو 30)
    annual_policy_days = contract.get('annual_policy_days', DEFAULT_ANNUAL_ENTITLEMENT)
    
    # التحقق من قرار إداري يغير السياسة
    policy_override = await db.admin_overrides.find_one({
        "employee_id": employee_id,
        "override_type": "annual_leave_policy",
        "year": year,
        "is_active": True
    }, {"_id": 0})
    
    if policy_override:
        annual_policy_days = policy_override.get('value', annual_policy_days)
    
    # 3. حساب أيام السنة
    days_in_year = 366 if calendar.isleap(year) else 365
    
    # 4. حساب تاريخ بداية العمل في هذه السنة
    contract_start = contract.get('start_date', '')
    year_start = f"{year}-01-01"
    
    # تاريخ بداية الحساب = الأحدث بين بداية العقد وبداية السنة
    if contract_start > year_start:
        calc_start_date = contract_start
    else:
        calc_start_date = year_start
    
    # 5. حساب أيام العمل حتى اليوم
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    year_end = f"{year}-12-31"
    
    # إذا السنة لم تنتهِ بعد، نحسب حتى اليوم
    calc_end_date = min(today, year_end)
    
    start_dt = datetime.strptime(calc_start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(calc_end_date, "%Y-%m-%d")
    
    days_worked = (end_dt - start_dt).days + 1
    if days_worked < 0:
        days_worked = 0
    
    # 6. حساب الاستحقاق اليومي والمكتسب
    daily_accrual = round(annual_policy_days / days_in_year, 4)
    earned_to_date = round(daily_accrual * days_worked, 2)
    
    # 7. حساب المستخدم (المنفذ فقط)
    used_entries = await db.leave_ledger.find({
        "employee_id": employee_id,
        "leave_type": "annual",
        "type": "debit",
        "date": {"$gte": year_start, "$lte": year_end}
    }, {"_id": 0}).to_list(1000)
    
    used_executed = sum(e.get('days', 0) for e in used_entries)
    
    # 8. حساب الرصيد المتاح
    available_balance = round(earned_to_date - used_executed, 2)
    
    return {
        "error": False,
        "year": year,
        "annual_policy_days": annual_policy_days,
        "days_in_year": days_in_year,
        "daily_accrual": daily_accrual,
        "contract_start": contract_start,
        "calc_start_date": calc_start_date,
        "days_worked": days_worked,
        "earned_to_date": earned_to_date,
        "used_executed": used_executed,
        "available_balance": max(0, available_balance),
        "formula": f"{annual_policy_days} / {days_in_year} × {days_worked} - {used_executed} = {available_balance}",
        "message_ar": f"مكتسب: {earned_to_date:.2f} يوم، مستخدم: {used_executed} يوم، متاح: {max(0, available_balance):.2f} يوم"
    }


async def get_annual_leave_balance_v2(employee_id: str) -> float:
    """
    الحصول على رصيد الإجازة السنوية المتاح (Pro-Rata)
    هذه الدالة تُستخدم في كل مكان يحتاج الرصيد
    
    Returns:
        float: الرصيد المتاح (2 decimals)
    """
    result = await calculate_pro_rata_entitlement(employee_id)
    
    if result.get('error'):
        return 0.0
    
    return round(result.get('available_balance', 0), 2)


# ============================================================
# 2. قواعد 21/30 يوم
# ============================================================

async def get_employee_annual_policy(employee_id: str) -> dict:
    """
    الحصول على سياسة الإجازة السنوية للموظف
    المصدر: العقد أو قرار إداري
    
    Returns:
        dict: {days: 21|30, source: 'contract'|'admin_override', ...}
    """
    year = datetime.now(timezone.utc).year
    
    # التحقق من قرار إداري أولاً
    override = await db.admin_overrides.find_one({
        "employee_id": employee_id,
        "override_type": "annual_leave_policy",
        "year": year,
        "is_active": True
    }, {"_id": 0})
    
    if override:
        return {
            "days": override.get('value', DEFAULT_ANNUAL_ENTITLEMENT),
            "source": "admin_override",
            "source_ar": "قرار إداري",
            "override_id": override.get('id'),
            "override_date": override.get('created_at'),
            "approved_by": override.get('approved_by')
        }
    
    # من العقد
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0})
    
    if not contract:
        contract = await db.contracts.find_one({
            "employee_id": employee_id,
            "is_active": True
        }, {"_id": 0})
    
    if contract:
        days = contract.get('annual_policy_days', DEFAULT_ANNUAL_ENTITLEMENT)
        return {
            "days": days,
            "source": "contract",
            "source_ar": "العقد",
            "contract_serial": contract.get('contract_serial', contract.get('id', ''))
        }
    
    # الافتراضي
    return {
        "days": DEFAULT_ANNUAL_ENTITLEMENT,
        "source": "default",
        "source_ar": "الافتراضي"
    }


async def set_annual_policy_override(
    employee_id: str,
    days: int,
    approved_by: str,
    reason: str = None
) -> dict:
    """
    تعيين قرار إداري لتغيير سياسة الإجازة السنوية
    يتطلب: sultan + mohammed + nq + stas
    """
    import uuid
    
    if days not in [21, 30]:
        return {"error": True, "message_ar": "القيمة يجب أن تكون 21 أو 30 يوم"}
    
    year = datetime.now(timezone.utc).year
    now = datetime.now(timezone.utc).isoformat()
    
    # إلغاء أي قرار سابق
    await db.admin_overrides.update_many({
        "employee_id": employee_id,
        "override_type": "annual_leave_policy",
        "year": year
    }, {"$set": {"is_active": False, "superseded_at": now}})
    
    # إنشاء القرار الجديد
    override = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "override_type": "annual_leave_policy",
        "value": days,
        "year": year,
        "reason": reason,
        "approved_by": approved_by,
        "is_active": True,
        "created_at": now
    }
    
    await db.admin_overrides.insert_one(override)
    override.pop("_id", None)
    
    return {
        "error": False,
        "message_ar": f"تم تعيين سياسة الإجازة السنوية إلى {days} يوم",
        "override": override
    }


# ============================================================
# 3. منع الترحيل + التنبيهات
# ============================================================

async def check_carryover_eligibility(employee_id: str) -> dict:
    """
    التحقق من أهلية ترحيل الإجازات
    افتراضياً: لا ترحيل
    استثناء: قرار إداري
    """
    year = datetime.now(timezone.utc).year
    
    # التحقق من قرار الترحيل
    carryover_decision = await db.admin_overrides.find_one({
        "employee_id": employee_id,
        "override_type": "leave_carryover",
        "from_year": year - 1,
        "to_year": year,
        "is_active": True
    }, {"_id": 0})
    
    if carryover_decision:
        return {
            "allowed": True,
            "days": carryover_decision.get('value', 0),
            "source": "admin_decision",
            "source_ar": "قرار إداري",
            "decision_id": carryover_decision.get('id')
        }
    
    return {
        "allowed": False,
        "days": 0,
        "source": "policy",
        "source_ar": "سياسة الشركة - لا ترحيل تلقائي"
    }


async def generate_balance_alerts() -> List[dict]:
    """
    توليد تنبيهات الأرصدة قبل نهاية العقد/السنة
    تُنفذ كـ CRON Job
    
    ينبه إذا:
    - بقي 3 أشهر على نهاية العقد والموظف لديه رصيد
    - بقي 3 أشهر على نهاية السنة والموظف لديه رصيد
    """
    alerts = []
    today = datetime.now(timezone.utc)
    alert_threshold = today + timedelta(days=ALERT_DAYS_BEFORE_END)
    
    # 1. موظفون مع عقود تنتهي قريباً
    contracts = await db.contracts_v2.find({
        "status": "active",
        "end_date": {
            "$lte": alert_threshold.strftime("%Y-%m-%d"),
            "$gte": today.strftime("%Y-%m-%d")
        }
    }, {"_id": 0}).to_list(500)
    
    for contract in contracts:
        emp_id = contract['employee_id']
        balance_info = await calculate_pro_rata_entitlement(emp_id)
        
        if balance_info.get('available_balance', 0) > 0:
            alerts.append({
                "type": "contract_ending",
                "type_ar": "انتهاء العقد",
                "employee_id": emp_id,
                "contract_serial": contract.get('contract_serial'),
                "end_date": contract.get('end_date'),
                "remaining_balance": balance_info.get('available_balance'),
                "days_until_end": (datetime.strptime(contract['end_date'], "%Y-%m-%d") - today).days,
                "message_ar": f"ينتهي العقد في {contract.get('end_date')} ولديه رصيد {balance_info.get('available_balance')} يوم"
            })
    
    # 2. نهاية السنة (ديسمبر)
    if today.month >= 10:  # أكتوبر فما فوق
        year_end = datetime(today.year, 12, 31)
        days_until_year_end = (year_end - today).days
        
        if days_until_year_end <= ALERT_DAYS_BEFORE_END:
            # جلب جميع الموظفين النشطين
            active_employees = await db.employees.find({
                "is_active": True,
                "has_active_contract": True
            }, {"_id": 0}).to_list(500)
            
            for emp in active_employees:
                balance_info = await calculate_pro_rata_entitlement(emp['id'])
                
                if balance_info.get('available_balance', 0) > 0:
                    alerts.append({
                        "type": "year_ending",
                        "type_ar": "نهاية السنة",
                        "employee_id": emp['id'],
                        "employee_name": emp.get('full_name_ar', emp.get('full_name')),
                        "end_date": f"{today.year}-12-31",
                        "remaining_balance": balance_info.get('available_balance'),
                        "days_until_end": days_until_year_end,
                        "message_ar": f"نهاية السنة خلال {days_until_year_end} يوم ولديه رصيد {balance_info.get('available_balance')} يوم"
                    })
    
    return alerts


# ============================================================
# 4. قواعد Blocking - معاملة نشطة واحدة فقط
# ============================================================

async def check_blocking_transaction(employee_id: str, transaction_type: str) -> Tuple[bool, Optional[dict]]:
    """
    التحقق من وجود معاملة نشطة من نفس النوع
    
    قانون: لا يمكن رفع طلب جديد إذا كان هناك طلب من نفس النوع:
    - قيد الانتظار (pending_*)
    - لم يُنفذ ولم يُرفض ولم يُلغى
    
    Args:
        employee_id: معرف الموظف
        transaction_type: نوع المعاملة (leave_request, forget_checkin, etc.)
    
    Returns:
        Tuple[is_blocked, blocking_transaction]
    """
    # حالات المعاملات النشطة
    active_statuses = [
        "pending_supervisor",
        "pending_ops",
        "pending_ceo",
        "pending_stas",
        "pending_finance"
    ]
    
    blocking_tx = await db.transactions.find_one({
        "employee_id": employee_id,
        "type": transaction_type,
        "status": {"$in": active_statuses}
    }, {"_id": 0})
    
    if blocking_tx:
        return True, blocking_tx
    
    return False, None


async def get_employee_active_transactions(employee_id: str) -> List[dict]:
    """
    الحصول على جميع المعاملات النشطة للموظف
    """
    active_statuses = [
        "pending_supervisor",
        "pending_ops",
        "pending_ceo",
        "pending_stas",
        "pending_finance"
    ]
    
    transactions = await db.transactions.find({
        "employee_id": employee_id,
        "status": {"$in": active_statuses}
    }, {"_id": 0}).to_list(100)
    
    return transactions


# ============================================================
# 5. قواعد عرض التصعيد
# ============================================================

def should_show_escalation(viewer_role: str, viewer_id: str, transaction: dict) -> bool:
    """
    تحديد هل يُعرض التصعيد للمشاهد
    
    قواعد:
    - الموظف: لا يرى كلمة "تصعيد" أبداً
    - المشرف: لا يرى تصعيد
    - سلطان ومن فوقه: يرون التصعيد
    """
    # الأدوار التي ترى التصعيد
    roles_can_see_escalation = ['sultan', 'naif', 'stas', 'mohammed', 'ceo', 'admin']
    
    return viewer_role in roles_can_see_escalation


def get_status_for_viewer(transaction: dict, viewer_role: str) -> dict:
    """
    الحصول على الحالة المناسبة للمشاهد
    
    الموظف يرى: "قيد المراجعة" بدلاً من تفاصيل التصعيد
    pending_ceo يظهر "لدى سلطان" للموظف
    """
    status = transaction.get('status', '')
    
    # الأدوار المحدودة (لا يرون تفاصيل التصعيد)
    limited_roles = ['employee', 'supervisor']
    
    if viewer_role in limited_roles:
        # إخفاء تفاصيل التصعيد
        if transaction.get('self_request_escalated') or 'escalat' in status.lower():
            return {
                "status": "under_review",
                "status_ar": "قيد المراجعة",
                "show_details": False
            }
        
        # تبسيط الحالات الأخرى
        status_map = {
            "pending_supervisor": {"status_ar": "بانتظار المشرف", "show_details": True},
            "pending_ops": {"status_ar": "قيد المراجعة", "show_details": False},
            "pending_ceo": {"status_ar": "لدى سلطان", "show_details": False},  # يظهر "لدى سلطان"
            "pending_stas": {"status_ar": "قيد المراجعة", "show_details": False},
            "pending_finance": {"status_ar": "قيد المراجعة", "show_details": False},
            "executed": {"status_ar": "تم التنفيذ", "show_details": True},
            "rejected": {"status_ar": "مرفوض", "show_details": True},
            "cancelled": {"status_ar": "ملغى", "show_details": True}
        }
        
        return status_map.get(status, {"status_ar": "قيد المراجعة", "show_details": False})
    
    # للإدارة - عرض كامل
    return {
        "status": status,
        "status_ar": get_status_arabic(status),
        "show_details": True,
        "escalated": transaction.get('self_request_escalated', False)
    }


def get_status_arabic(status: str) -> str:
    """ترجمة الحالة للعربية"""
    translations = {
        "pending_supervisor": "بانتظار المشرف",
        "pending_ops": "بانتظار العمليات",
        "pending_ceo": "لدى سلطان",  # تم التعديل
        "pending_stas": "بانتظار التنفيذ",
        "pending_finance": "بانتظار المالية",
        "executed": "تم التنفيذ",
        "rejected": "مرفوض",
        "cancelled": "ملغى",
        "returned": "مُرجع"
    }
    return translations.get(status, status)


# ============================================================
# 6. تنسيق التاريخ والوقت
# ============================================================

def format_datetime_riyadh(iso_string: str, include_time: bool = True) -> str:
    """
    تنسيق التاريخ والوقت بتوقيت الرياض
    بدون ISO الطويل
    
    Args:
        iso_string: التاريخ بصيغة ISO
        include_time: هل يتضمن الوقت
    
    Returns:
        str: التاريخ المنسق
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # تحويل إلى توقيت الرياض (+3)
        riyadh_offset = timedelta(hours=3)
        dt_riyadh = dt + riyadh_offset
        
        if include_time:
            return dt_riyadh.strftime("%Y-%m-%d %H:%M")
        else:
            return dt_riyadh.strftime("%Y-%m-%d")
    except Exception:
        return iso_string


def get_arabic_month(month: int) -> str:
    """الحصول على اسم الشهر بالعربية"""
    months = {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
        5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
        9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    }
    return months.get(month, str(month))


def format_date_arabic(date_str: str) -> str:
    """
    تنسيق التاريخ بالعربية
    مثال: 17 فبراير 2026
    """
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return f"{dt.day} {get_arabic_month(dt.month)} {dt.year}"
    except Exception:
        return date_str



# ============================================================
# 7. سياسة الإجازة المرضية - نظام العمل السعودي (المادة 117)
# ============================================================

# شرائح الإجازة المرضية
SICK_LEAVE_TIERS = [
    {"days": 30, "salary_percent": 100, "label_ar": "30 يوم براتب كامل", "label_en": "30 days full pay"},
    {"days": 60, "salary_percent": 50, "label_ar": "60 يوم بنصف الراتب", "label_en": "60 days half pay"},
    {"days": 30, "salary_percent": 0, "label_ar": "30 يوم بدون أجر", "label_en": "30 days no pay"},
]

# إجمالي أيام الإجازة المرضية في السنة
MAX_SICK_DAYS_PER_YEAR = 120  # 30 + 60 + 30


async def calculate_sick_leave_consumption(employee_id: str, year: int = None) -> dict:
    """
    حساب استهلاك الإجازة المرضية حسب المادة 117 من نظام العمل السعودي
    
    الشرائح:
    - أول 30 يوم: براتب كامل (100%)
    - الـ 60 يوم التالية: بنصف الراتب (50%)
    - الـ 30 يوم الأخيرة: بدون أجر (0%)
    - الحد الأقصى: 120 يوم في السنة
    
    Args:
        employee_id: معرف الموظف
        year: السنة (افتراضي: السنة الحالية)
    
    Returns:
        dict: تفاصيل الاستهلاك مع الشرائح
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    year_start = f"{year}-01-01"
    year_end = f"{year}-12-31"
    
    # 1. جلب جميع طلبات الإجازة المرضية المنفذة في هذه السنة
    sick_entries = await db.leave_ledger.find({
        "employee_id": employee_id,
        "leave_type": "sick",
        "type": "debit",
        "$or": [
            {"start_date": {"$gte": year_start, "$lte": year_end}},
            {"date": {"$gte": year_start, "$lte": year_end}}
        ]
    }, {"_id": 0}).sort("start_date", 1).to_list(100)
    
    # إذا لم توجد في leave_ledger، جرب transactions
    if not sick_entries:
        sick_txns = await db.transactions.find({
            "employee_id": employee_id,
            "type": "leave_request",
            "status": "executed",
            "data.leave_type": "sick",
            "data.start_date": {"$gte": year_start, "$lte": year_end}
        }, {"_id": 0}).sort("data.start_date", 1).to_list(100)
        
        for tx in sick_txns:
            sick_entries.append({
                "days": tx.get("data", {}).get("working_days", 0),
                "start_date": tx.get("data", {}).get("start_date"),
                "end_date": tx.get("data", {}).get("end_date"),
                "ref_no": tx.get("ref_no")
            })
    
    # 2. حساب إجمالي الأيام المستهلكة
    total_sick_days = sum(e.get('days', 0) for e in sick_entries)
    
    # 3. توزيع الأيام على الشرائح
    tier_breakdown = []
    remaining_days = total_sick_days
    
    for tier in SICK_LEAVE_TIERS:
        tier_max = tier["days"]
        tier_used = min(remaining_days, tier_max)
        remaining_days -= tier_used
        
        tier_breakdown.append({
            "tier_name_ar": tier["label_ar"],
            "tier_name_en": tier["label_en"],
            "tier_max_days": tier_max,
            "tier_used_days": tier_used,
            "tier_remaining_days": tier_max - tier_used,
            "salary_percent": tier["salary_percent"],
            "is_active": tier_used > 0 and tier_used < tier_max,
            "is_exhausted": tier_used >= tier_max
        })
    
    # 4. تحديد الشريحة الحالية
    current_tier = None
    current_tier_index = 0
    accumulated = 0
    
    for i, tier in enumerate(SICK_LEAVE_TIERS):
        accumulated += tier["days"]
        if total_sick_days < accumulated:
            current_tier = tier
            current_tier_index = i + 1
            break
    
    if not current_tier and total_sick_days >= MAX_SICK_DAYS_PER_YEAR:
        current_tier = {"label_ar": "تم استنفاد الرصيد", "salary_percent": 0}
        current_tier_index = 4
    
    # 5. حساب الخصم المالي (للإدارة)
    salary_deduction_info = []
    remaining_calc = total_sick_days
    
    for tier in SICK_LEAVE_TIERS:
        tier_days = min(remaining_calc, tier["days"])
        if tier_days > 0:
            deduction_percent = 100 - tier["salary_percent"]
            salary_deduction_info.append({
                "days": tier_days,
                "salary_percent": tier["salary_percent"],
                "deduction_percent": deduction_percent,
                "label_ar": f"{tier_days} يوم بنسبة {deduction_percent}% خصم"
            })
        remaining_calc -= tier_days
    
    return {
        "year": year,
        "total_sick_days_used": total_sick_days,
        "max_sick_days_year": MAX_SICK_DAYS_PER_YEAR,
        "remaining_sick_days": max(0, MAX_SICK_DAYS_PER_YEAR - total_sick_days),
        "current_tier": current_tier_index,
        "current_tier_info": {
            "name_ar": current_tier["label_ar"] if current_tier else "لم يستخدم",
            "salary_percent": current_tier["salary_percent"] if current_tier else 100
        },
        "tier_breakdown": tier_breakdown,
        "salary_deduction_info": salary_deduction_info,
        "sick_entries": sick_entries,
        "message_ar": f"استهلاك الإجازة المرضية: {total_sick_days} من {MAX_SICK_DAYS_PER_YEAR} يوم - الشريحة الحالية: {current_tier['label_ar'] if current_tier else 'لم يستخدم'}"
    }


async def get_sick_leave_tier_for_request(employee_id: str, requested_days: int) -> dict:
    """
    تحديد شريحة الراتب لطلب إجازة مرضية جديد
    
    يُستخدم عند قبول طلب الإجازة المرضية لتحديد:
    - كم يوم سيكون براتب كامل
    - كم يوم بنصف راتب
    - كم يوم بدون راتب
    
    Args:
        employee_id: معرف الموظف
        requested_days: عدد الأيام المطلوبة
    
    Returns:
        dict: تفصيل الشرائح للطلب الجديد
    """
    # جلب الاستهلاك الحالي
    current = await calculate_sick_leave_consumption(employee_id)
    used_days = current.get('total_sick_days_used', 0)
    
    # حساب توزيع الأيام الجديدة على الشرائح
    new_total = used_days + requested_days
    
    if new_total > MAX_SICK_DAYS_PER_YEAR:
        # تجاوز الحد الأقصى
        return {
            "allowed": False,
            "max_allowed_days": MAX_SICK_DAYS_PER_YEAR - used_days,
            "message_ar": f"تجاوز الحد الأقصى للإجازة المرضية. المتبقي: {MAX_SICK_DAYS_PER_YEAR - used_days} يوم"
        }
    
    # توزيع الأيام الجديدة
    distribution = []
    remaining_new = requested_days
    accumulated = 0
    
    for tier in SICK_LEAVE_TIERS:
        accumulated += tier["days"]
        
        # كم يوم مستخدم من هذه الشريحة؟
        tier_start = accumulated - tier["days"]
        tier_end = accumulated
        
        # كم يوم كان مستخدماً قبل هذا الطلب؟
        used_in_tier = max(0, min(used_days, tier_end) - tier_start)
        
        # كم يوم متبقي في هذه الشريحة؟
        remaining_in_tier = tier["days"] - used_in_tier
        
        if remaining_in_tier > 0 and remaining_new > 0:
            days_from_this_tier = min(remaining_new, remaining_in_tier)
            distribution.append({
                "tier_name_ar": tier["label_ar"],
                "days": days_from_this_tier,
                "salary_percent": tier["salary_percent"]
            })
            remaining_new -= days_from_this_tier
    
    return {
        "allowed": True,
        "requested_days": requested_days,
        "distribution": distribution,
        "message_ar": f"توزيع {requested_days} يوم على الشرائح"
    }


async def get_sick_leave_summary_for_admin(employee_id: str) -> dict:
    """
    ملخص الإجازة المرضية للإدارة (STAS/Sultan)
    يُعرض في مرآة STAS وصفحة الموظف
    """
    consumption = await calculate_sick_leave_consumption(employee_id)
    
    return {
        "total_used": consumption.get('total_sick_days_used', 0),
        "max_per_year": MAX_SICK_DAYS_PER_YEAR,
        "remaining": consumption.get('remaining_sick_days', MAX_SICK_DAYS_PER_YEAR),
        "current_tier": consumption.get('current_tier_info', {}),
        "tier_breakdown": consumption.get('tier_breakdown', []),
        "salary_impact": consumption.get('salary_deduction_info', []),
        "entries": consumption.get('sick_entries', [])
    }
