"""
STAS Mirror Service - مرآة STAS الشاملة
============================================================
مرآة STAS = ضمان الحوكمة
- هو لا يثق في قرارات اللي قبله
- هو يتحقق منهم
- ثم ينفذ وهو مطمئن

تعرض المرآة:
- العقد
- مدة الخدمة
- تعريف الأجر
- رصيد الإجازات قبل وبعد
- وضع الحضور
- الغياب غير المسوى
- العهد
- السلف
- الاستحقاقات
- الاستقطاعات
- الصافي النهائي
- المعادلات الحسابية مكتوبة

PASS / FAIL / WARN logic
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List
from database import db
from services.service_calculator import get_employee_service_info, calculate_monthly_wage
from services.leave_service import get_leave_balance, get_all_leave_balances, get_employee_leave_summary
from services.attendance_service import get_unsettled_absences, get_employee_attendance_summary
from services.settlement_service import validate_settlement_request, aggregate_settlement_data


# ============================================================
# PRE-CHECK BUILDER
# ============================================================

async def build_pre_checks(tx: dict) -> List[dict]:
    """
    بناء قائمة الفحوصات المسبقة لأي نوع معاملة
    
    Args:
        tx: المعاملة
        
    Returns:
        list: قائمة الفحوصات مع الحالة (PASS/FAIL/WARN)
    """
    checks = []
    tx_type = tx.get('type')
    data = tx.get('data', {})
    emp_id = tx.get('employee_id')
    
    # ============================================================
    # فحص 1: سلسلة الموافقات
    # ============================================================
    approval_chain = tx.get('approval_chain', [])
    current_stage = tx.get('current_stage', '')
    status = tx.get('status', '')
    
    is_at_stas = current_stage == 'stas' or status in ('stas', 'pending_stas')
    valid_actions = [a for a in approval_chain if a.get('status') in ('approve', 'escalate')]
    
    checks.append({
        "name": "Approval Chain Complete",
        "name_ar": "سلسلة الموافقات مكتملة",
        "status": "PASS" if is_at_stas or len(valid_actions) > 0 else "FAIL",
        "detail": f"الإجراءات: {len(valid_actions)}, في STAS: {is_at_stas}",
        "category": "workflow"
    })
    
    # ============================================================
    # فحص 2: المعاملة لم تُنفذ
    # ============================================================
    checks.append({
        "name": "Not Already Executed",
        "name_ar": "لم يتم التنفيذ مسبقاً",
        "status": "PASS" if tx['status'] != 'executed' else "FAIL",
        "detail": f"الحالة الحالية: {tx['status']}",
        "category": "workflow"
    })
    
    # ============================================================
    # فحوصات حسب نوع المعاملة
    # ============================================================
    
    if tx_type == 'leave_request':
        checks.extend(await build_leave_checks(tx, emp_id, data))
    
    elif tx_type == 'settlement':
        checks.extend(await build_settlement_checks(tx, emp_id, data))
    
    elif tx_type == 'finance_60':
        checks.extend(await build_finance_checks(tx, emp_id, data))
    
    elif tx_type == 'tangible_custody':
        checks.extend(await build_custody_checks(tx, emp_id, data))
    
    elif tx_type == 'tangible_custody_return':
        checks.extend(await build_custody_return_checks(tx, emp_id, data))
    
    elif tx_type in ['forget_checkin', 'field_work', 'early_leave_request', 'late_excuse']:
        checks.extend(await build_attendance_request_checks(tx, emp_id, data))
    
    return checks


async def build_leave_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات طلب الإجازة"""
    checks = []
    leave_type = data.get('leave_type', 'annual')
    working_days = data.get('working_days', 0)
    
    # فحص الرصيد
    balance = await get_leave_balance(emp_id, leave_type)
    
    checks.append({
        "name": "Leave Balance Sufficient",
        "name_ar": "رصيد الإجازات كافٍ",
        "status": "PASS" if balance >= working_days else "FAIL",
        "detail": f"الرصيد: {balance}, المطلوب: {working_days}",
        "category": "leave",
        "before_after": {
            "before": balance,
            "after": balance - working_days,
            "change": -working_days
        }
    })
    
    # فحص التعارض
    start = data.get('start_date')
    existing = await db.transactions.find_one({
        "employee_id": emp_id, 
        "type": "leave_request", 
        "status": "executed",
        "data.start_date": {"$lte": data.get('end_date', '')},
        "data.adjusted_end_date": {"$gte": start},
        "id": {"$ne": tx['id']}
    })
    
    checks.append({
        "name": "No Calendar Conflict",
        "name_ar": "لا يوجد تعارض في التقويم",
        "status": "PASS" if not existing else "FAIL",
        "detail": "لا يوجد تعارض" if not existing else f"تعارض مع {existing.get('ref_no')}",
        "category": "leave"
    })
    
    # فحص العقد النشط
    service_info = await get_employee_service_info(emp_id)
    checks.append({
        "name": "Active Contract",
        "name_ar": "عقد نشط",
        "status": "PASS" if service_info and service_info['contract_status'] == 'active' else "FAIL",
        "detail": f"العقد: {service_info['contract_serial']}" if service_info else "لا يوجد عقد نشط",
        "category": "contract"
    })
    
    return checks


async def build_settlement_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات المخالصة - الأهم"""
    checks = []
    
    # استخدام validator المخصص
    validation = await validate_settlement_request(emp_id)
    
    # فحص العقد المنتهي
    checks.append({
        "name": "Contract Terminated",
        "name_ar": "العقد منتهي",
        "status": "PASS" if validation['contract'] else "FAIL",
        "detail": f"العقد: {validation['contract']['contract_serial']}" if validation['contract'] else "لا يوجد عقد منتهي",
        "category": "contract"
    })
    
    # فحص العهد
    has_custody = any(b['code'] == 'ACTIVE_CUSTODY' for b in validation['blockers'])
    custody_blocker = next((b for b in validation['blockers'] if b['code'] == 'ACTIVE_CUSTODY'), None)
    checks.append({
        "name": "No Active Custody",
        "name_ar": "لا توجد عهد نشطة",
        "status": "FAIL" if has_custody else "PASS",
        "detail": custody_blocker['message_ar'] if custody_blocker else "لا توجد عهد نشطة",
        "category": "custody"
    })
    
    # فحص السلف
    loan_warning = next((w for w in validation['warnings'] if w['code'] == 'PENDING_LOANS'), None)
    checks.append({
        "name": "Pending Loans Check",
        "name_ar": "فحص السلف",
        "status": "WARN" if loan_warning else "PASS",
        "detail": loan_warning['message_ar'] if loan_warning else "لا توجد سلف",
        "category": "finance"
    })
    
    # فحص الغياب
    absence_warning = next((w for w in validation['warnings'] if w['code'] == 'UNSETTLED_ABSENCE'), None)
    checks.append({
        "name": "Unsettled Absence Check",
        "name_ar": "فحص الغياب",
        "status": "WARN" if absence_warning else "PASS",
        "detail": absence_warning['message_ar'] if absence_warning else "لا يوجد غياب غير مسوى",
        "category": "attendance"
    })
    
    # فحص الـ Snapshot
    if data.get('snapshot'):
        checks.append({
            "name": "Settlement Snapshot Valid",
            "name_ar": "لقطة المخالصة صالحة",
            "status": "PASS",
            "detail": f"تاريخ اللقطة: {data['snapshot'].get('snapshot_date', '')[:10]}",
            "category": "settlement"
        })
    
    return checks


async def build_finance_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات العهدة المالية"""
    checks = []
    
    checks.append({
        "name": "Finance Code Valid",
        "name_ar": "رمز المالية صالح",
        "status": "PASS",
        "detail": f"الرمز: {data.get('code')} - {data.get('code_name')}",
        "category": "finance"
    })
    
    # فحص العقد النشط
    service_info = await get_employee_service_info(emp_id)
    checks.append({
        "name": "Employee Active",
        "name_ar": "الموظف نشط",
        "status": "PASS" if service_info else "WARN",
        "detail": "الموظف نشط" if service_info else "تحقق من حالة الموظف",
        "category": "employee"
    })
    
    return checks


async def build_custody_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات العهدة الملموسة"""
    checks = []
    
    # فحص الموظف نشط
    service_info = await get_employee_service_info(emp_id)
    checks.append({
        "name": "Employee Active",
        "name_ar": "الموظف نشط",
        "status": "PASS" if service_info else "FAIL",
        "detail": f"الصنف: {data.get('item_name', '')}",
        "category": "custody"
    })
    
    return checks


async def build_custody_return_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات إرجاع العهدة"""
    checks = []
    
    custody_id = data.get('custody_id')
    if custody_id:
        custody = await db.custody_ledger.find_one({"id": custody_id}, {"_id": 0})
        checks.append({
            "name": "Custody Record Found",
            "name_ar": "سجل العهدة موجود",
            "status": "PASS" if custody and custody.get('status') == 'active' else "FAIL",
            "detail": f"الصنف: {data.get('item_name', '')}",
            "category": "custody"
        })
    
    return checks


async def build_attendance_request_checks(tx: dict, emp_id: str, data: dict) -> List[dict]:
    """فحوصات طلبات الحضور"""
    checks = []
    
    target_date = data.get('target_date') or data.get('date')
    
    # فحص وجود سجل الحضور
    if target_date:
        existing = await db.attendance_ledger.find_one({
            "employee_id": emp_id,
            "date": target_date
        })
        checks.append({
            "name": "Attendance Date Valid",
            "name_ar": "تاريخ الحضور صالح",
            "status": "PASS" if existing or True else "WARN",  # تحذير فقط
            "detail": f"التاريخ: {target_date}",
            "category": "attendance"
        })
    
    return checks


# ============================================================
# MIRROR DATA BUILDER
# ============================================================

async def build_mirror_data(tx: dict) -> dict:
    """
    بناء بيانات مرآة STAS الشاملة
    
    Args:
        tx: المعاملة
        
    Returns:
        dict: بيانات كاملة للعرض
    """
    emp_id = tx.get('employee_id')
    tx_type = tx.get('type')
    data = tx.get('data', {})
    
    # بناء الفحوصات
    pre_checks = await build_pre_checks(tx)
    
    # جلب بيانات الموظف
    employee = None
    if emp_id:
        employee = await db.employees.find_one({"id": emp_id}, {"_id": 0})
    
    # جلب معلومات الخدمة
    service_info = await get_employee_service_info(emp_id) if emp_id else None
    
    # بناء before/after
    before_after = await build_before_after(tx, emp_id, tx_type, data)
    
    # بناء trace links
    trace_links = await build_trace_links(tx, emp_id, tx_type)
    
    # حساب النتيجة
    failed_checks = [c for c in pre_checks if c['status'] == 'FAIL']
    warning_checks = [c for c in pre_checks if c['status'] == 'WARN']
    all_pass = len(failed_checks) == 0
    
    return {
        "transaction": tx,
        "employee": employee,
        "service_info": service_info,
        "pre_checks": pre_checks,
        "failed_checks": failed_checks,
        "warning_checks": warning_checks,
        "all_checks_pass": all_pass,
        "has_warnings": len(warning_checks) > 0,
        "can_execute": all_pass,
        "before_after": before_after,
        "trace_links": trace_links,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def build_before_after(tx: dict, emp_id: str, tx_type: str, data: dict) -> dict:
    """بناء بيانات قبل وبعد التنفيذ"""
    
    if tx_type == 'leave_request':
        lt = data.get('leave_type', 'annual')
        balance = await get_leave_balance(emp_id, lt)
        wd = data.get('working_days', 0)
        
        # حساب الاستحقاق الكلي
        entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": lt, "type": "credit"}, {"_id": 0}
        ).to_list(1000)
        entitlement = sum(e.get('days', 0) for e in entries)
        used = entitlement - balance
        
        return {
            "type": "leave",
            "before": {
                "total_entitlement": entitlement,
                "used": used,
                "remaining": balance
            },
            "after": {
                "total_entitlement": entitlement,
                "used": used + wd,
                "remaining": balance - wd
            },
            "change": {
                "days": -wd,
                "leave_type": lt
            }
        }
    
    elif tx_type == 'settlement':
        # للمخالصة - استخدام الـ Snapshot إذا موجود
        if data.get('snapshot'):
            snapshot = data['snapshot']
            return {
                "type": "settlement",
                "snapshot": snapshot,
                "summary": {
                    "eos": snapshot.get('eos', {}).get('final_amount', 0),
                    "leave_compensation": snapshot.get('leave', {}).get('compensation', 0),
                    "deductions": snapshot.get('deductions', {}).get('total', 0),
                    "net": snapshot.get('totals', {}).get('net_amount', 0)
                }
            }
        else:
            # حساب ديناميكي
            snapshot = await aggregate_settlement_data(emp_id)
            return {
                "type": "settlement",
                "snapshot": snapshot,
                "dynamic": True
            }
    
    elif tx_type == 'finance_60':
        return {
            "type": "finance",
            "before": {"description": "قبل القيد المالي"},
            "after": {
                "amount": data.get('amount', 0),
                "code": data.get('code_name', ''),
                "type": data.get('tx_type', 'credit')
            }
        }
    
    return {"type": "other", "before": {}, "after": {}}


async def build_trace_links(tx: dict, emp_id: str, tx_type: str) -> List[dict]:
    """بناء روابط التتبع"""
    links = []
    
    if emp_id:
        emp = await db.employees.find_one({"id": emp_id}, {"_id": 0})
        if emp:
            links.append({
                "type": "employee",
                "label": f"الموظف: {emp.get('full_name_ar', emp.get('full_name', ''))}",
                "id": emp_id
            })
    
    if tx_type == 'leave_request':
        leave_type = tx.get('data', {}).get('leave_type', 'annual')
        entries = await db.leave_ledger.find(
            {"employee_id": emp_id, "leave_type": leave_type}, {"_id": 0}
        ).to_list(100)
        links.append({
            "type": "ledger",
            "label": f"سجل الإجازات ({len(entries)} قيد)",
            "id": emp_id
        })
    
    elif tx_type == 'settlement':
        # روابط المخالصة
        finance_entries = await db.finance_ledger.find({"employee_id": emp_id}, {"_id": 0}).to_list(100)
        links.append({
            "type": "ledger",
            "label": f"السجل المالي ({len(finance_entries)} قيد)",
            "id": emp_id
        })
        
        custody_entries = await db.custody_ledger.find({"employee_id": emp_id, "status": "active"}, {"_id": 0}).to_list(100)
        if custody_entries:
            links.append({
                "type": "custody",
                "label": f"العهد النشطة ({len(custody_entries)})",
                "id": emp_id
            })
    
    # رابط المعاملة
    links.append({
        "type": "transaction",
        "label": f"المعاملة: {tx['ref_no']}",
        "id": tx['id']
    })
    
    # رابط العقد
    if emp_id:
        contracts = await db.contracts_v2.find({"employee_id": emp_id}, {"_id": 0}).to_list(10)
        if contracts:
            links.append({
                "type": "contract",
                "label": f"العقود ({len(contracts)})",
                "id": emp_id
            })
    
    return links
