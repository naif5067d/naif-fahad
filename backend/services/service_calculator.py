"""
Service Calculator - حساب مدة الخدمة ومكافأة نهاية الخدمة
============================================================
- يعتمد على start_date من العقد النشط
- في حال الإنهاء يعتمد على termination_date
- الحساب = 365 يوم = سنة
- دعم كسور السنة بدقة (مثال 2.75 سنة)
- لا يتم تخزين - يحسب ديناميكياً
"""

from datetime import datetime, timezone
from typing import Optional, Dict
from database import db


def calculate_service_years(start_date: str, end_date: str = None) -> dict:
    """
    حساب مدة الخدمة بدقة
    
    Args:
        start_date: تاريخ بداية العقد (YYYY-MM-DD)
        end_date: تاريخ النهاية (YYYY-MM-DD) - إذا None يستخدم تاريخ اليوم
        
    Returns:
        dict: {
            total_days: إجمالي الأيام,
            years: السنوات بالكسور (4 خانات عشرية),
            years_int: السنوات الكاملة,
            remaining_months: الأشهر المتبقية,
            remaining_days: الأيام المتبقية,
            formatted: صيغة نصية (X سنة و Y شهر و Z يوم)
        }
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    total_days = (end - start).days
    
    if total_days < 0:
        total_days = 0
    
    # 365 يوم = سنة واحدة
    years = total_days / 365
    years_int = total_days // 365
    remaining_after_years = total_days % 365
    remaining_months = remaining_after_years // 30
    remaining_days = remaining_after_years % 30
    
    # صيغة نصية
    formatted_ar = f"{years_int} سنة"
    if remaining_months > 0:
        formatted_ar += f" و {remaining_months} شهر"
    if remaining_days > 0:
        formatted_ar += f" و {remaining_days} يوم"
    
    formatted_en = f"{years_int} year(s)"
    if remaining_months > 0:
        formatted_en += f", {remaining_months} month(s)"
    if remaining_days > 0:
        formatted_en += f", {remaining_days} day(s)"
    
    return {
        "total_days": total_days,
        "years": round(years, 4),  # 4 خانات عشرية للدقة
        "years_int": years_int,
        "remaining_months": remaining_months,
        "remaining_days": remaining_days,
        "formatted_ar": formatted_ar,
        "formatted_en": formatted_en
    }


def calculate_monthly_wage(contract: dict) -> dict:
    """
    حساب الأجر الشهري المعتمد حسب تعريف العقد
    
    Args:
        contract: بيانات العقد
        
    Returns:
        dict: {
            basic: الراتب الأساسي,
            housing: بدل السكن,
            transport: بدل النقل,
            other: بدلات أخرى,
            total_allowances: مجموع البدلات,
            wage_definition: تعريف الأجر,
            monthly_wage: الأجر الشهري المعتمد للحسابات
        }
    """
    basic = contract.get('basic_salary', 0) or 0
    housing = contract.get('housing_allowance', 0) or 0
    transport = contract.get('transport_allowance', 0) or 0
    other = contract.get('other_allowances', 0) or 0
    
    total_allowances = housing + transport + other
    wage_definition = contract.get('wage_definition', 'basic_only')
    
    if wage_definition == 'basic_plus_fixed':
        monthly_wage = basic + housing + transport
    else:  # basic_only
        monthly_wage = basic
    
    return {
        "basic": basic,
        "housing": housing,
        "transport": transport,
        "other": other,
        "total_allowances": total_allowances,
        "wage_definition": wage_definition,
        "monthly_wage": monthly_wage,
        "daily_wage": round(monthly_wage / 30, 2) if monthly_wage > 0 else 0
    }


def calculate_eos(service_years: float, monthly_wage: float, termination_reason: str) -> dict:
    """
    حساب مكافأة نهاية الخدمة حسب نظام العمل السعودي
    
    المعادلات:
    - أقل من 5 سنوات: 0.5 × الأجر × عدد السنوات
    - 5 سنوات فأكثر: (0.5 × 5) + (1 × الباقي)
    
    نسب الاستقالة:
    - أقل من سنتين: 0%
    - 2-5 سنوات: 33%
    - 5-10 سنوات: 66%
    - 10+ سنوات: 100%
    
    Args:
        service_years: مدة الخدمة بالسنوات (كسور)
        monthly_wage: الأجر الشهري المعتمد
        termination_reason: سبب الإنهاء
        
    Returns:
        dict: تفاصيل الحساب والمبلغ النهائي
    """
    # حساب المكافأة الأساسية
    if service_years <= 0:
        base_amount = 0
    elif service_years <= 5:
        # أقل من 5 سنوات: نصف راتب عن كل سنة
        base_amount = 0.5 * monthly_wage * service_years
    else:
        # 5 سنوات فأكثر
        first_five = 0.5 * monthly_wage * 5
        remaining_years = service_years - 5
        remaining_amount = 1.0 * monthly_wage * remaining_years
        base_amount = first_five + remaining_amount
    
    # تحديد نسبة الاستحقاق حسب سبب الإنهاء
    percentage = 100  # الافتراضي
    percentage_reason = "استحقاق كامل"
    
    if termination_reason == 'resignation':
        if service_years < 2:
            percentage = 0
            percentage_reason = "أقل من سنتين - لا استحقاق"
        elif service_years < 5:
            percentage = 33
            percentage_reason = "2-5 سنوات - ثلث المكافأة"
        elif service_years < 10:
            percentage = 66
            percentage_reason = "5-10 سنوات - ثلثي المكافأة"
        else:
            percentage = 100
            percentage_reason = "10 سنوات فأكثر - كامل المكافأة"
    elif termination_reason in ['termination', 'contract_expiry', 'retirement', 'death', 'mutual_agreement']:
        percentage = 100
        percentage_reason = "استحقاق كامل"
    
    final_amount = base_amount * (percentage / 100)
    
    # المعادلة النصية
    if service_years <= 5:
        formula = f"0.5 × {monthly_wage:,.2f} × {service_years:.4f} = {base_amount:,.2f}"
    else:
        formula = f"(0.5 × {monthly_wage:,.2f} × 5) + (1 × {monthly_wage:,.2f} × {service_years - 5:.4f}) = {base_amount:,.2f}"
    
    if percentage != 100:
        formula += f" × {percentage}% = {final_amount:,.2f}"
    
    return {
        "service_years": service_years,
        "monthly_wage": monthly_wage,
        "termination_reason": termination_reason,
        "base_amount": round(base_amount, 2),
        "percentage": percentage,
        "percentage_reason": percentage_reason,
        "final_amount": round(final_amount, 2),
        "formula": formula,
        "reference": "نظام العمل السعودي - المادة 84-85"
    }


async def get_employee_service_info(employee_id: str) -> Optional[dict]:
    """
    جلب معلومات الخدمة للموظف من العقد النشط
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict أو None
    """
    # البحث عن العقد النشط أو المنتهي
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": {"$in": ["active", "terminated"]}
    }, {"_id": 0})
    
    if not contract:
        return None
    
    # تحديد تاريخ النهاية
    if contract.get('status') == 'terminated' and contract.get('termination_date'):
        end_date = contract['termination_date']
    else:
        end_date = None  # سيستخدم تاريخ اليوم
    
    # حساب مدة الخدمة
    service = calculate_service_years(contract['start_date'], end_date)
    
    # حساب الأجر
    wages = calculate_monthly_wage(contract)
    
    return {
        "employee_id": employee_id,
        "contract_id": contract['id'],
        "contract_serial": contract['contract_serial'],
        "contract_status": contract['status'],
        "start_date": contract['start_date'],
        "end_date": end_date,
        "termination_reason": contract.get('termination_reason'),
        "service": service,
        "wages": wages
    }


async def calculate_employee_eos(employee_id: str) -> Optional[dict]:
    """
    حساب مكافأة نهاية الخدمة للموظف
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict كامل بحساب EOS أو None
    """
    service_info = await get_employee_service_info(employee_id)
    
    if not service_info:
        return None
    
    if service_info['contract_status'] not in ['terminated', 'active']:
        return None
    
    termination_reason = service_info.get('termination_reason') or 'contract_expiry'
    
    eos = calculate_eos(
        service_years=service_info['service']['years'],
        monthly_wage=service_info['wages']['monthly_wage'],
        termination_reason=termination_reason
    )
    
    return {
        **service_info,
        "eos": eos
    }
