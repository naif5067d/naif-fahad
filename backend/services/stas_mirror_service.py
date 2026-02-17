"""
STAS Mirror Service - مرآة STAS الشاملة (محدث)
============================================================
Version: 2.0.0 - HR Policy Integration
============================================================
مرآة STAS = ضمان الحوكمة
- هو لا يثق في قرارات اللي قبله
- هو يتحقق منهم
- ثم ينفذ وهو مطمئن

تعرض المرآة:
- العقد + سياسة الإجازة (21/30)
- مدة الخدمة
- تعريف الأجر
- رصيد الإجازات قبل وبعد (Pro-Rata)
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
from services.hr_policy import (
    calculate_pro_rata_entitlement,
    get_employee_annual_policy,
    get_status_for_viewer,
    format_datetime_riyadh,
    format_date_arabic
)


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
    """فحوصات طلب الإجازة - محدث Pro-Rata"""
    checks = []
    leave_type = data.get('leave_type', 'annual')
    working_days = data.get('working_days', 0)
    
    # فحص الرصيد باستخدام Pro-Rata
    if leave_type == 'annual':
        pro_rata = await calculate_pro_rata_entitlement(emp_id)
        balance = pro_rata.get('available_balance', 0)
        policy = await get_employee_annual_policy(emp_id)
        
        checks.append({
            "name": "Annual Leave Policy",
            "name_ar": "سياسة الإجازة السنوية",
            "status": "PASS",
            "detail": f"السياسة: {policy['days']} يوم ({policy['source_ar']})",
            "category": "policy"
        })
        
        checks.append({
            "name": "Pro-Rata Calculation",
            "name_ar": "حساب الاستحقاق التدريجي",
            "status": "PASS",
            "detail": pro_rata.get('formula', ''),
            "category": "leave"
        })
        
        checks.append({
            "name": "Leave Balance Sufficient",
            "name_ar": "رصيد الإجازات كافٍ",
            "status": "PASS" if balance >= working_days else "FAIL",
            "detail": f"المكتسب: {pro_rata.get('earned_to_date', 0):.2f}, المستخدم: {pro_rata.get('used_executed', 0)}, المتاح: {balance:.2f}, المطلوب: {working_days}",
            "category": "leave",
            "before_after": {
                "before": round(balance, 2),
                "after": round(balance - working_days, 2),
                "change": -working_days
            }
        })
    else:
        # الإجازات الإدارية - لا رصيد، مسار إداري فقط
        checks.append({
            "name": "Administrative Leave",
            "name_ar": "إجازة إدارية",
            "status": "PASS",
            "detail": f"نوع الإجازة: {data.get('leave_type_ar', leave_type)} - مسار إداري",
            "category": "leave"
        })
    
    # فحص التقرير الطبي للإجازة المرضية + استهلاك الـ 120 يوم
    if leave_type == 'sick':
        medical_file_url = data.get('medical_file_url')
        checks.append({
            "name": "Medical Report Attached",
            "name_ar": "التقرير الطبي مرفق",
            "status": "PASS" if medical_file_url else "FAIL",
            "detail": "تم رفع التقرير الطبي" if medical_file_url else "⚠️ لم يتم رفع التقرير الطبي - مطلوب قبل التنفيذ",
            "category": "document",
            "medical_file_url": medical_file_url
        })
        
        # فحص استهلاك الإجازة المرضية (المادة 117)
        from services.hr_policy import calculate_sick_leave_consumption, get_sick_leave_tier_for_request
        
        consumption = await calculate_sick_leave_consumption(emp_id)
        current_used = consumption.get('total_sick_days_used', 0)
        current_tier = consumption.get('current_tier_info', {})
        
        tier_info = await get_sick_leave_tier_for_request(emp_id, working_days)
        
        # تحديد مستوى التحذير
        warning_level = "PASS"
        detail_msg = f"استهلاك: {current_used}/120 يوم"
        
        if tier_info.get('distribution'):
            for tier in tier_info['distribution']:
                if tier['salary_percent'] == 0:
                    warning_level = "FAIL"
                    detail_msg += f" | ⚠️ سيُخصم 100% من الراتب لـ {tier['days']} يوم"
                    break
                elif tier['salary_percent'] == 50:
                    warning_level = "WARN"
                    detail_msg += f" | ⚠️ سيُخصم 50% من الراتب لـ {tier['days']} يوم"
        
        checks.append({
            "name": "Sick Leave Article 117",
            "name_ar": "الإجازة المرضية - المادة 117",
            "status": warning_level,
            "detail": detail_msg,
            "category": "leave",
            "sick_leave_info": {
                "current_used": current_used,
                "max_per_year": 120,
                "remaining": 120 - current_used,
                "current_tier": current_tier,
                "tier_distribution": tier_info.get('distribution', []),
                "tier_breakdown": consumption.get('tier_breakdown', [])
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
    """بناء بيانات قبل وبعد التنفيذ - محدث Pro-Rata"""
    
    if tx_type == 'leave_request':
        lt = data.get('leave_type', 'annual')
        wd = data.get('working_days', 0)
        
        if lt == 'annual':
            # استخدام Pro-Rata
            pro_rata = await calculate_pro_rata_entitlement(emp_id)
            policy = await get_employee_annual_policy(emp_id)
            
            balance = pro_rata.get('available_balance', 0)
            earned = pro_rata.get('earned_to_date', 0)
            used = pro_rata.get('used_executed', 0)
            
            return {
                "type": "leave",
                "policy": {
                    "days": policy['days'],
                    "source": policy['source'],
                    "source_ar": policy['source_ar']
                },
                "formula": pro_rata.get('formula', ''),
                "before": {
                    "annual_policy": policy['days'],
                    "daily_accrual": pro_rata.get('daily_accrual', 0),
                    "days_worked": pro_rata.get('days_worked', 0),
                    "earned_to_date": round(earned, 2),
                    "used": used,
                    "remaining": round(balance, 2)
                },
                "after": {
                    "annual_policy": policy['days'],
                    "daily_accrual": pro_rata.get('daily_accrual', 0),
                    "days_worked": pro_rata.get('days_worked', 0),
                    "earned_to_date": round(earned, 2),
                    "used": used + wd,
                    "remaining": round(balance - wd, 2)
                },
                "change": {
                    "days": -wd,
                    "leave_type": lt,
                    "leave_type_ar": "الإجازة السنوية"
                },
                "note_ar": "الخصم يتم فقط عند تنفيذ STAS"
            }
        else:
            # الإجازات الإدارية - لا خصم من الرصيد
            return {
                "type": "leave_admin",
                "leave_type": lt,
                "leave_type_ar": data.get('leave_type_ar', lt),
                "days": wd,
                "note_ar": "إجازة إدارية - لا تُخصم من الرصيد السنوي",
                "before": {},
                "after": {}
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
