"""
Warning & Violation Ledger - سجل الإنذارات والمخالفات

نظام العمل السعودي - المادة 80:
- الإنذار الأول: تحذير كتابي
- الإنذار الثاني: خصم من الراتب
- الإنذار الثالث: إنهاء خدمات (بموافقة الإدارة)

حالات الفصل (المادة 80):
- غياب 15 يوم متصل بدون عذر
- غياب 30 يوم متفرق في السنة

لا فصل تلقائي - النظام ينشئ Case للمراجعة فقط.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from enum import Enum
from database import db


class WarningType(str, Enum):
    """أنواع الإنذارات"""
    FIRST_WARNING = "first_warning"       # إنذار أول
    SECOND_WARNING = "second_warning"     # إنذار ثاني
    THIRD_WARNING = "third_warning"       # إنذار ثالث
    TERMINATION_CASE = "termination_case" # حالة فصل


class ViolationType(str, Enum):
    """أنواع المخالفات"""
    ABSENCE = "absence"                   # غياب
    REPEATED_LATE = "repeated_late"       # تكرار التأخير
    EARLY_LEAVE = "early_leave"           # خروج مبكر متكرر
    MISCONDUCT = "misconduct"             # سوء سلوك
    POLICY_VIOLATION = "policy_violation" # مخالفة سياسة


WARNING_TYPE_AR = {
    WarningType.FIRST_WARNING: "إنذار أول",
    WarningType.SECOND_WARNING: "إنذار ثاني",
    WarningType.THIRD_WARNING: "إنذار ثالث (نهائي)",
    WarningType.TERMINATION_CASE: "حالة إنهاء خدمات"
}

VIOLATION_TYPE_AR = {
    ViolationType.ABSENCE: "غياب",
    ViolationType.REPEATED_LATE: "تكرار التأخير",
    ViolationType.EARLY_LEAVE: "خروج مبكر متكرر",
    ViolationType.MISCONDUCT: "سوء سلوك",
    ViolationType.POLICY_VIOLATION: "مخالفة سياسة"
}


async def get_employee_warnings_count(employee_id: str, year: str = None) -> dict:
    """
    حساب عدد الإنذارات للموظف في السنة
    """
    if not year:
        year = datetime.now(timezone.utc).strftime("%Y")
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # عدد الإنذارات المنفذة
    warnings = await db.warning_ledger.find({
        "employee_id": employee_id,
        "status": "executed",
        "created_at": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "warning_type": 1}).to_list(100)
    
    count = {
        "first_warning": 0,
        "second_warning": 0,
        "third_warning": 0,
        "termination_case": 0,
        "total": len(warnings)
    }
    
    for w in warnings:
        wtype = w.get('warning_type')
        if wtype in count:
            count[wtype] += 1
    
    return count


async def get_employee_absence_pattern(employee_id: str, year: str = None) -> dict:
    """
    تحليل نمط الغياب للموظف
    
    يحسب:
    - أيام الغياب المتصلة
    - أيام الغياب المتفرقة في السنة
    """
    if not year:
        year = datetime.now(timezone.utc).strftime("%Y")
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # جلب أيام الغياب
    absences = await db.daily_status.find({
        "employee_id": employee_id,
        "final_status": "ABSENT",
        "date": {"$gte": start_date, "$lte": end_date}
    }, {"_id": 0, "date": 1}).sort("date", 1).to_list(365)
    
    if not absences:
        return {
            "total_absent_days": 0,
            "max_consecutive_days": 0,
            "current_consecutive_days": 0,
            "reaches_15_consecutive": False,
            "reaches_30_scattered": False,
            "absent_dates": []
        }
    
    dates = [a['date'] for a in absences]
    total_absent = len(dates)
    
    # حساب الأيام المتصلة
    max_consecutive = 0
    current_consecutive = 1
    
    for i in range(1, len(dates)):
        prev_date = datetime.strptime(dates[i-1], "%Y-%m-%d")
        curr_date = datetime.strptime(dates[i], "%Y-%m-%d")
        
        if (curr_date - prev_date).days == 1:
            current_consecutive += 1
        else:
            max_consecutive = max(max_consecutive, current_consecutive)
            current_consecutive = 1
    
    max_consecutive = max(max_consecutive, current_consecutive)
    
    # التحقق من الحدود
    reaches_15 = max_consecutive >= 15
    reaches_30 = total_absent >= 30
    
    return {
        "total_absent_days": total_absent,
        "max_consecutive_days": max_consecutive,
        "current_consecutive_days": current_consecutive,
        "reaches_15_consecutive": reaches_15,
        "reaches_30_scattered": reaches_30,
        "absent_dates": dates
    }


async def create_warning(
    employee_id: str,
    warning_type: WarningType,
    violation_type: ViolationType,
    reason: str,
    reason_ar: str,
    source_records: List[str],
    details: dict = None
) -> dict:
    """
    إنشاء إنذار جديد
    
    الإنذار يُنشأ كمقترح يحتاج موافقة قبل التنفيذ
    """
    now = datetime.now(timezone.utc).isoformat()
    
    warning = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "warning_type": warning_type.value,
        "warning_type_ar": WARNING_TYPE_AR.get(warning_type, warning_type.value),
        "violation_type": violation_type.value,
        "violation_type_ar": VIOLATION_TYPE_AR.get(violation_type, violation_type.value),
        "reason": reason,
        "reason_ar": reason_ar,
        "source_records": source_records,
        "details": details or {},
        "status": "pending",  # pending → approved → executed OR rejected
        "created_at": now,
        "created_by": "system",
        "status_history": [{
            "from_status": None,
            "to_status": "pending",
            "actor": "system",
            "timestamp": now,
            "note": "تم إنشاء الإنذار تلقائياً"
        }]
    }
    
    await db.warning_ledger.insert_one(warning)
    warning.pop('_id', None)
    
    return warning


async def review_warning(warning_id: str, approved: bool, reviewer_id: str, note: str = "") -> dict:
    """مراجعة الإنذار (سلطان/نايف)"""
    warning = await db.warning_ledger.find_one({"id": warning_id}, {"_id": 0})
    
    if not warning:
        return {"error": "الإنذار غير موجود"}
    
    if warning['status'] != 'pending':
        return {"error": "الإنذار ليس في حالة انتظار"}
    
    now = datetime.now(timezone.utc).isoformat()
    new_status = "approved" if approved else "rejected"
    
    status_entry = {
        "from_status": warning['status'],
        "to_status": new_status,
        "actor": reviewer_id,
        "timestamp": now,
        "note": note or ("تمت الموافقة" if approved else "تم الرفض")
    }
    
    await db.warning_ledger.update_one(
        {"id": warning_id},
        {
            "$set": {
                "status": new_status,
                "reviewed_by": reviewer_id,
                "reviewed_at": now,
                "review_note": note
            },
            "$push": {"status_history": status_entry}
        }
    )
    
    warning['status'] = new_status
    return warning


async def execute_warning(warning_id: str, executor_id: str, note: str = "") -> dict:
    """تنفيذ الإنذار (STAS فقط)"""
    warning = await db.warning_ledger.find_one({"id": warning_id}, {"_id": 0})
    
    if not warning:
        return {"error": "الإنذار غير موجود"}
    
    if warning['status'] != 'approved':
        return {"error": "الإنذار غير موافق عليه"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    status_entry = {
        "from_status": warning['status'],
        "to_status": "executed",
        "actor": executor_id,
        "timestamp": now,
        "note": note or "تم تنفيذ الإنذار"
    }
    
    await db.warning_ledger.update_one(
        {"id": warning_id},
        {
            "$set": {
                "status": "executed",
                "executed_by": executor_id,
                "executed_at": now,
                "execution_note": note
            },
            "$push": {"status_history": status_entry}
        }
    )
    
    # إرسال إشعار للموظف
    from services.notification_service import create_notification
    await create_notification(
        recipient_id=warning['employee_id'],
        recipient_role="employee",
        title="إنذار جديد",
        message=f"تم تسجيل {warning['warning_type_ar']} بسبب: {warning['reason_ar']}",
        link=f"/my-finances"
    )
    
    warning['status'] = "executed"
    return warning


async def check_and_create_warnings(employee_id: str) -> List[dict]:
    """
    فحص الموظف وإنشاء الإنذارات اللازمة تلقائياً
    
    يُستدعى بعد كل غياب جديد أو في الـ Job الشهري
    """
    year = datetime.now(timezone.utc).strftime("%Y")
    
    # تحليل نمط الغياب
    pattern = await get_employee_absence_pattern(employee_id, year)
    
    # عدد الإنذارات الحالية
    current_warnings = await get_employee_warnings_count(employee_id, year)
    
    created_warnings = []
    
    # التحقق من حالة الـ 15 يوم متصل
    if pattern['reaches_15_consecutive']:
        # إنشاء حالة فصل
        existing = await db.warning_ledger.find_one({
            "employee_id": employee_id,
            "warning_type": WarningType.TERMINATION_CASE.value,
            "details.reason_code": "15_consecutive",
            "created_at": {"$regex": f"^{year}"}
        })
        
        if not existing:
            warning = await create_warning(
                employee_id=employee_id,
                warning_type=WarningType.TERMINATION_CASE,
                violation_type=ViolationType.ABSENCE,
                reason="15 consecutive absent days",
                reason_ar="غياب 15 يوم متصل بدون عذر (المادة 80)",
                source_records=pattern['absent_dates'][-15:],
                details={
                    "reason_code": "15_consecutive",
                    "consecutive_days": pattern['max_consecutive_days'],
                    "policy_reference": "نظام العمل السعودي - المادة 80"
                }
            )
            created_warnings.append(warning)
    
    # التحقق من حالة الـ 30 يوم متفرق
    if pattern['reaches_30_scattered']:
        existing = await db.warning_ledger.find_one({
            "employee_id": employee_id,
            "warning_type": WarningType.TERMINATION_CASE.value,
            "details.reason_code": "30_scattered",
            "created_at": {"$regex": f"^{year}"}
        })
        
        if not existing:
            warning = await create_warning(
                employee_id=employee_id,
                warning_type=WarningType.TERMINATION_CASE,
                violation_type=ViolationType.ABSENCE,
                reason="30 scattered absent days",
                reason_ar="غياب 30 يوم متفرق في السنة (المادة 80)",
                source_records=pattern['absent_dates'],
                details={
                    "reason_code": "30_scattered",
                    "total_absent_days": pattern['total_absent_days'],
                    "policy_reference": "نظام العمل السعودي - المادة 80"
                }
            )
            created_warnings.append(warning)
    
    # التحقق من الإنذارات التدريجية (كل 5 أيام غياب = إنذار)
    absence_threshold = [3, 7, 12]  # 3 أيام = إنذار أول، 7 = إنذار ثاني، 12 = إنذار ثالث
    
    total_absences = pattern['total_absent_days']
    
    if total_absences >= absence_threshold[0] and current_warnings['first_warning'] == 0:
        warning = await create_warning(
            employee_id=employee_id,
            warning_type=WarningType.FIRST_WARNING,
            violation_type=ViolationType.ABSENCE,
            reason="3+ absent days",
            reason_ar=f"تجاوز {total_absences} أيام غياب - إنذار أول",
            source_records=pattern['absent_dates'][:3],
            details={
                "total_absent_days": total_absences,
                "threshold": absence_threshold[0]
            }
        )
        created_warnings.append(warning)
    
    if total_absences >= absence_threshold[1] and current_warnings['second_warning'] == 0:
        warning = await create_warning(
            employee_id=employee_id,
            warning_type=WarningType.SECOND_WARNING,
            violation_type=ViolationType.ABSENCE,
            reason="7+ absent days",
            reason_ar=f"تجاوز {total_absences} أيام غياب - إنذار ثاني",
            source_records=pattern['absent_dates'][:7],
            details={
                "total_absent_days": total_absences,
                "threshold": absence_threshold[1]
            }
        )
        created_warnings.append(warning)
    
    if total_absences >= absence_threshold[2] and current_warnings['third_warning'] == 0:
        warning = await create_warning(
            employee_id=employee_id,
            warning_type=WarningType.THIRD_WARNING,
            violation_type=ViolationType.ABSENCE,
            reason="12+ absent days",
            reason_ar=f"تجاوز {total_absences} أيام غياب - إنذار ثالث (نهائي)",
            source_records=pattern['absent_dates'][:12],
            details={
                "total_absent_days": total_absences,
                "threshold": absence_threshold[2]
            }
        )
        created_warnings.append(warning)
    
    return created_warnings


async def get_employee_warnings(employee_id: str, year: str = None) -> List[dict]:
    """جلب إنذارات الموظف"""
    query = {"employee_id": employee_id}
    
    if year:
        query["created_at"] = {"$regex": f"^{year}"}
    
    warnings = await db.warning_ledger.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return warnings


async def get_pending_warnings() -> List[dict]:
    """جلب الإنذارات المعلقة للمراجعة"""
    warnings = await db.warning_ledger.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # إضافة أسماء الموظفين
    for w in warnings:
        emp = await db.employees.find_one(
            {"id": w['employee_id']},
            {"_id": 0, "full_name_ar": 1, "full_name": 1}
        )
        w['employee_name'] = emp.get('full_name_ar', emp.get('full_name', '')) if emp else ''
    
    return warnings


async def get_approved_warnings() -> List[dict]:
    """جلب الإنذارات الموافق عليها للتنفيذ"""
    warnings = await db.warning_ledger.find(
        {"status": "approved"},
        {"_id": 0}
    ).sort("reviewed_at", -1).to_list(100)
    
    for w in warnings:
        emp = await db.employees.find_one(
            {"id": w['employee_id']},
            {"_id": 0, "full_name_ar": 1, "full_name": 1}
        )
        w['employee_name'] = emp.get('full_name_ar', emp.get('full_name', '')) if emp else ''
    
    return warnings
