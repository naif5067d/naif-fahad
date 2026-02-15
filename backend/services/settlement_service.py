"""
Settlement Service - خدمة المخالصة
============================================================
آلية المخالصة:
1. إنهاء العقد
2. إنشاء طلب مخالصة
3. عند إنشاء الطلب يتم تجميع Snapshot كامل
4. Snapshot لا يتغير بعد إنشائه
5. التنفيذ يعتمد فقط على Snapshot

يتم تجميع من:
- contracts_v2 (العقد)
- leave_ledger (الإجازات)
- attendance_ledger (الحضور)
- finance_ledger (المالية)
- custody_ledger (العهد)
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from database import db
from services.service_calculator import (
    calculate_service_years, 
    calculate_monthly_wage, 
    calculate_eos,
    get_employee_service_info
)
from services.leave_service import get_leave_balance, get_all_leave_balances
from services.attendance_service import get_unsettled_absences, get_employee_attendance_summary
import uuid


# ============================================================
# SETTLEMENT VALIDATOR
# ============================================================

async def validate_settlement_request(employee_id: str) -> dict:
    """
    التحقق الشامل قبل المخالصة
    يُحدد: PASS / FAIL / WARN
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: نتيجة التحقق مع التفاصيل
    """
    blockers = []  # FAIL - يمنع التنفيذ
    warnings = []  # WARN - تحذير فقط
    
    # 1. التحقق من العقد المنتهي
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "terminated"
    }, {"_id": 0})
    
    if not contract:
        # تحقق إذا كان نشط
        active_contract = await db.contracts_v2.find_one({
            "employee_id": employee_id,
            "status": "active"
        }, {"_id": 0})
        
        if active_contract:
            blockers.append({
                "code": "CONTRACT_NOT_TERMINATED",
                "message_ar": "العقد لم يُنهَ بعد. يجب إنهاء العقد أولاً.",
                "message_en": "Contract not terminated. Must terminate first.",
                "severity": "FAIL"
            })
        else:
            blockers.append({
                "code": "NO_CONTRACT",
                "message_ar": "لا يوجد عقد للموظف",
                "message_en": "No contract found for employee",
                "severity": "FAIL"
            })
    
    # 2. التحقق من العهد الملموسة النشطة
    active_custody = await db.custody_ledger.find({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0}).to_list(100)
    
    if active_custody:
        custody_items = [c.get('item_name', 'غير محدد') for c in active_custody]
        blockers.append({
            "code": "ACTIVE_CUSTODY",
            "message_ar": f"يوجد {len(active_custody)} عهدة ملموسة لم تُرجع: {', '.join(custody_items[:3])}",
            "message_en": f"{len(active_custody)} unreturned custody items",
            "items": custody_items,
            "count": len(active_custody),
            "severity": "FAIL"
        })
    
    # 3. التحقق من السلف غير المسددة
    pending_loans = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": {"$in": ["loan", "loan_issued", "advance"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    total_loans = sum(l.get('amount', 0) for l in pending_loans)
    if total_loans > 0:
        warnings.append({
            "code": "PENDING_LOANS",
            "message_ar": f"يوجد سلف غير مسددة: {total_loans:,.2f} ر.س (ستُخصم من المخالصة)",
            "message_en": f"Pending loans: {total_loans:,.2f} SAR (will be deducted)",
            "amount": total_loans,
            "severity": "WARN"
        })
    
    # 4. التحقق من الغياب غير المسوى
    unsettled = await get_unsettled_absences(employee_id)
    if unsettled:
        warnings.append({
            "code": "UNSETTLED_ABSENCE",
            "message_ar": f"يوجد {len(unsettled)} يوم غياب غير مسوى (سيُحسب خصم)",
            "message_en": f"{len(unsettled)} unsettled absence days",
            "count": len(unsettled),
            "severity": "WARN"
        })
    
    # 5. التحقق من الجزاءات غير المنفذة
    pending_penalties = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": "penalty",
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    total_penalties = sum(p.get('amount', 0) for p in pending_penalties)
    if total_penalties > 0:
        warnings.append({
            "code": "PENDING_PENALTIES",
            "message_ar": f"يوجد جزاءات غير منفذة: {total_penalties:,.2f} ر.س",
            "message_en": f"Pending penalties: {total_penalties:,.2f} SAR",
            "amount": total_penalties,
            "severity": "WARN"
        })
    
    return {
        "valid": len(blockers) == 0,
        "can_proceed": len(blockers) == 0,
        "blockers": blockers,
        "warnings": warnings,
        "contract": contract,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# SETTLEMENT AGGREGATOR (SNAPSHOT CREATION)
# ============================================================

async def aggregate_settlement_data(employee_id: str) -> dict:
    """
    تجميع جميع البيانات للمخالصة وإنشاء Snapshot
    يُستدعى عند إنشاء طلب المخالصة
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: Snapshot كامل لا يتغير
    """
    now = datetime.now(timezone.utc).isoformat()
    
    # 1. جلب العقد
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": {"$in": ["terminated", "active"]}
    }, {"_id": 0})
    
    if not contract:
        return None
    
    # 2. جلب بيانات الموظف
    employee = await db.employees.find_one(
        {"id": employee_id}, 
        {"_id": 0}
    )
    
    # 3. حساب مدة الخدمة
    end_date = contract.get('termination_date') or now[:10]
    service = calculate_service_years(contract['start_date'], end_date)
    
    # 4. حساب الأجر
    wages = calculate_monthly_wage(contract)
    
    # 5. حساب مكافأة نهاية الخدمة
    termination_reason = contract.get('termination_reason', 'contract_expiry')
    eos = calculate_eos(
        service_years=service['years'],
        monthly_wage=wages['monthly_wage'],
        termination_reason=termination_reason
    )
    
    # 6. حساب بدل الإجازات
    leave_balance = await get_leave_balance(employee_id, 'annual')
    leave_compensation = leave_balance * wages['daily_wage'] if leave_balance > 0 else 0
    
    # 7. تجميع الاستقطاعات من finance_ledger
    deductions = await aggregate_deductions(employee_id)
    
    # 8. حساب الغياب
    unsettled_absences = await get_unsettled_absences(employee_id)
    absence_deduction = len(unsettled_absences) * wages['daily_wage']
    
    if absence_deduction > 0:
        deductions['items'].append({
            "category": "absence_deduction",
            "description_ar": f"خصم غياب ({len(unsettled_absences)} يوم)",
            "description_en": f"Absence deduction ({len(unsettled_absences)} days)",
            "amount": round(absence_deduction, 2),
            "days": len(unsettled_absences)
        })
        deductions['total'] += absence_deduction
    
    # 9. حساب المجاميع
    total_entitlements = eos['final_amount'] + leave_compensation
    total_deductions = deductions['total']
    net_amount = total_entitlements - total_deductions
    
    # 10. إنشاء الـ Snapshot
    snapshot = {
        "snapshot_id": str(uuid.uuid4()),
        "snapshot_date": now,
        "snapshot_version": "v1",
        
        "employee": {
            "id": employee_id,
            "name": employee.get('full_name', '') if employee else '',
            "name_ar": employee.get('full_name_ar', '') if employee else '',
            "employee_number": employee.get('employee_number', '') if employee else ''
        },
        
        "contract": {
            "id": contract['id'],
            "serial": contract['contract_serial'],
            "start_date": contract['start_date'],
            "termination_date": contract.get('termination_date'),
            "termination_reason": termination_reason,
            "wage_definition": contract.get('wage_definition', 'basic_only')
        },
        
        "service": service,
        "wages": wages,
        "eos": eos,
        
        "leave": {
            "balance": leave_balance,
            "daily_wage": wages['daily_wage'],
            "compensation": round(leave_compensation, 2),
            "formula": f"{leave_balance} يوم × {wages['daily_wage']:,.2f} ر.س = {leave_compensation:,.2f} ر.س"
        },
        
        "deductions": deductions,
        
        "totals": {
            "entitlements": {
                "eos": eos['final_amount'],
                "leave_compensation": round(leave_compensation, 2),
                "total": round(total_entitlements, 2)
            },
            "deductions": {
                "items_count": len(deductions['items']),
                "total": round(total_deductions, 2)
            },
            "net_amount": round(net_amount, 2),
            "currency": "SAR"
        },
        
        "checksum": None  # سيُحسب لاحقاً
    }
    
    # حساب checksum للتحقق من عدم التغيير
    import hashlib
    import json
    
    data_str = json.dumps(snapshot['totals'], sort_keys=True)
    snapshot['checksum'] = hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    return snapshot


async def aggregate_deductions(employee_id: str) -> dict:
    """
    تجميع جميع الاستقطاعات من finance_ledger
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: تفاصيل الاستقطاعات
    """
    # السلف
    loans = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": {"$in": ["loan", "loan_issued", "advance"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    # الجزاءات
    penalties = await db.finance_ledger.find({
        "employee_id": employee_id,
        "category": "penalty",
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    # خصومات أخرى
    other_deductions = await db.finance_ledger.find({
        "employee_id": employee_id,
        "type": "debit",
        "category": {"$nin": ["loan", "loan_issued", "advance", "penalty", "salary"]},
        "settled": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    items = []
    total = 0
    
    # إضافة السلف
    for loan in loans:
        amount = loan.get('amount', 0)
        items.append({
            "category": "loan",
            "description_ar": loan.get('description', 'سلفة'),
            "description_en": "Loan",
            "amount": amount,
            "reference_id": loan.get('id')
        })
        total += amount
    
    # إضافة الجزاءات
    for penalty in penalties:
        amount = penalty.get('amount', 0)
        items.append({
            "category": "penalty",
            "description_ar": penalty.get('description', 'جزاء'),
            "description_en": "Penalty",
            "amount": amount,
            "reference_id": penalty.get('id')
        })
        total += amount
    
    # إضافة الخصومات الأخرى
    for deduction in other_deductions:
        amount = deduction.get('amount', 0)
        items.append({
            "category": deduction.get('category', 'other'),
            "description_ar": deduction.get('description', 'خصم آخر'),
            "description_en": "Other deduction",
            "amount": amount,
            "reference_id": deduction.get('id')
        })
        total += amount
    
    return {
        "items": items,
        "total": round(total, 2),
        "loans_count": len(loans),
        "penalties_count": len(penalties),
        "other_count": len(other_deductions)
    }


# ============================================================
# SETTLEMENT EXECUTION
# ============================================================

async def execute_settlement(
    transaction_id: str,
    snapshot: dict,
    executor_id: str
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    تنفيذ المخالصة بناءً على الـ Snapshot
    
    Args:
        transaction_id: معرف المعاملة
        snapshot: الـ Snapshot المُجمد
        executor_id: معرف المنفذ (STAS)
        
    Returns:
        tuple: (success, error_message, result)
    """
    now = datetime.now(timezone.utc).isoformat()
    employee_id = snapshot['employee']['id']
    
    # 1. تسجيل مكافأة نهاية الخدمة في finance_ledger
    if snapshot['eos']['final_amount'] > 0:
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "transaction_id": transaction_id,
            "type": "credit",
            "category": "eos_payout",
            "amount": snapshot['eos']['final_amount'],
            "description": f"مكافأة نهاية خدمة - {snapshot['service']['formatted_ar']}",
            "description_en": f"End of Service - {snapshot['service']['formatted_en']}",
            "settlement_ref": snapshot['snapshot_id'],
            "date": now,
            "created_at": now
        })
    
    # 2. تسجيل بدل الإجازات
    if snapshot['leave']['compensation'] > 0:
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "transaction_id": transaction_id,
            "type": "credit",
            "category": "leave_compensation",
            "amount": snapshot['leave']['compensation'],
            "description": f"بدل إجازات - {snapshot['leave']['balance']} يوم",
            "description_en": f"Leave compensation - {snapshot['leave']['balance']} days",
            "settlement_ref": snapshot['snapshot_id'],
            "date": now,
            "created_at": now
        })
    
    # 3. تسجيل الاستقطاعات وتحديث حالتها
    for item in snapshot['deductions']['items']:
        # تسجيل الخصم
        await db.finance_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "transaction_id": transaction_id,
            "type": "debit",
            "category": f"settlement_{item['category']}",
            "amount": item['amount'],
            "description": item['description_ar'],
            "description_en": item.get('description_en', ''),
            "settlement_ref": snapshot['snapshot_id'],
            "date": now,
            "created_at": now
        })
        
        # تحديث السجل الأصلي كـ settled
        if item.get('reference_id'):
            await db.finance_ledger.update_one(
                {"id": item['reference_id']},
                {"$set": {"settled": True, "settled_at": now, "settlement_ref": snapshot['snapshot_id']}}
            )
    
    # 4. تسجيل المخالصة النهائية
    await db.finance_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "transaction_id": transaction_id,
        "type": "settlement",
        "category": "settlement_final",
        "amount": snapshot['totals']['net_amount'],
        "description": f"المخالصة النهائية - {snapshot['contract']['serial']}",
        "description_en": f"Final Settlement - {snapshot['contract']['serial']}",
        "settlement_ref": snapshot['snapshot_id'],
        "snapshot": snapshot,  # حفظ الـ Snapshot الكامل
        "date": now,
        "created_at": now
    })
    
    # 5. تسوية الغياب
    await db.attendance_ledger.update_many(
        {"employee_id": employee_id, "type": "absence", "settled": {"$ne": True}},
        {"$set": {"settled": True, "settled_at": now, "settlement_ref": snapshot['snapshot_id']}}
    )
    
    # 6. إغلاق العقد
    from services.contract_service import close_contract
    await close_contract(
        contract_id=snapshot['contract']['id'],
        executor_id=executor_id,
        settlement_ref=transaction_id
    )
    
    # 7. تعطيل المستخدم
    await db.users.update_one(
        {"employee_id": employee_id},
        {"$set": {"is_active": False, "deactivated_at": now}}
    )
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"is_active": False, "deactivated_at": now}}
    )
    
    return True, None, {
        "settlement_ref": snapshot['snapshot_id'],
        "net_amount": snapshot['totals']['net_amount'],
        "executed_at": now
    }


# ============================================================
# SETTLEMENT MIRROR DATA (FOR STAS VIEW)
# ============================================================

async def get_settlement_mirror_data(employee_id: str) -> dict:
    """
    بناء بيانات مرآة STAS للمخالصة
    
    Args:
        employee_id: معرف الموظف
        
    Returns:
        dict: بيانات كاملة للعرض في المرآة
    """
    # التحقق
    validation = await validate_settlement_request(employee_id)
    
    # تجميع البيانات
    if validation['contract']:
        snapshot = await aggregate_settlement_data(employee_id)
    else:
        snapshot = None
    
    # بناء Pre-Checks
    pre_checks = []
    
    # فحص العقد
    pre_checks.append({
        "name": "Contract Status",
        "name_ar": "حالة العقد",
        "status": "PASS" if validation['contract'] else "FAIL",
        "detail": f"Status: {validation['contract']['status']}" if validation['contract'] else "No terminated contract"
    })
    
    # فحص العهد
    has_custody = any(b['code'] == 'ACTIVE_CUSTODY' for b in validation['blockers'])
    pre_checks.append({
        "name": "No Active Custody",
        "name_ar": "لا توجد عهد نشطة",
        "status": "FAIL" if has_custody else "PASS",
        "detail": next((b['message_ar'] for b in validation['blockers'] if b['code'] == 'ACTIVE_CUSTODY'), "لا توجد عهد نشطة")
    })
    
    # فحص السلف
    has_loans = any(w['code'] == 'PENDING_LOANS' for w in validation['warnings'])
    loan_warning = next((w for w in validation['warnings'] if w['code'] == 'PENDING_LOANS'), None)
    pre_checks.append({
        "name": "Pending Loans",
        "name_ar": "السلف",
        "status": "WARN" if has_loans else "PASS",
        "detail": loan_warning['message_ar'] if loan_warning else "لا توجد سلف"
    })
    
    # فحص الغياب
    has_absence = any(w['code'] == 'UNSETTLED_ABSENCE' for w in validation['warnings'])
    absence_warning = next((w for w in validation['warnings'] if w['code'] == 'UNSETTLED_ABSENCE'), None)
    pre_checks.append({
        "name": "Unsettled Absence",
        "name_ar": "الغياب غير المسوى",
        "status": "WARN" if has_absence else "PASS",
        "detail": absence_warning['message_ar'] if absence_warning else "لا يوجد غياب"
    })
    
    # النتيجة النهائية
    all_pass = all(c['status'] != 'FAIL' for c in pre_checks)
    has_warnings = any(c['status'] == 'WARN' for c in pre_checks)
    
    return {
        "employee_id": employee_id,
        "validation": validation,
        "pre_checks": pre_checks,
        "all_checks_pass": all_pass,
        "has_warnings": has_warnings,
        "can_execute": all_pass,
        "snapshot": snapshot,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
