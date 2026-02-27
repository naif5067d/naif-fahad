"""
Deduction Transactions - معاملات الخصم الرسمية
============================================================
نظام معاملات مثل الإجازات تماماً:
- رقم مرجعي: DED-2026-0001
- سلسلة موافقات: ops → ceo → stas
- PDF قابل للطباعة
- تفاصيل كاملة
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import db
from utils.auth import get_current_user, require_roles
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/deduction-transactions", tags=["deduction-transactions"])


# ============================================================
# MODELS
# ============================================================

class DeductionTransactionCreate(BaseModel):
    """إنشاء معاملة خصم جديدة"""
    employee_id: str
    amount: float
    reason: str
    month: str  # YYYY-MM
    breakdown: Optional[dict] = None  # تفصيل الحساب
    note: Optional[str] = ""


class ApprovalAction(BaseModel):
    """إجراء الموافقة"""
    action: str  # approve_salary | approve_settlement | reject
    note: Optional[str] = ""


class ExecuteAction(BaseModel):
    """إجراء التنفيذ"""
    confirm: bool = False
    note: Optional[str] = ""


# ============================================================
# WORKFLOW & STATUS
# ============================================================

WORKFLOW = ["ops", "ceo", "stas"]  # سلطان/نايف → محمد → ستاس

STAGE_ROLES = {
    "ops": ["sultan", "naif"],
    "ceo": ["mohammed"],
    "stas": ["stas"]
}

STATUS_LABELS = {
    "pending_ceo": {"ar": "بانتظار قرار محمد", "en": "Pending Mohammed's Decision"},
    "approved_salary": {"ar": "معتمد للخصم من الراتب", "en": "Approved - Deduct from Salary"},
    "approved_settlement": {"ar": "مؤجل للمخالصة", "en": "Deferred to Settlement"},
    "pending_execution": {"ar": "بانتظار التنفيذ", "en": "Pending Execution"},
    "executed": {"ar": "تم التنفيذ", "en": "Executed"},
    "rejected": {"ar": "مرفوض", "en": "Rejected"}
}


# ============================================================
# HELPERS
# ============================================================

async def get_next_ref_no():
    """إنشاء رقم مرجعي جديد"""
    year = datetime.now().year
    result = await db.counters.find_one_and_update(
        {"id": f"deduction_ref_{year}"},
        {"$inc": {"seq": 1}},
        return_document=True,
        upsert=True
    )
    seq = result.get("seq", 1)
    return f"DED-{year}-{seq:04d}"


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("")
async def list_deduction_transactions(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """
    قائمة معاملات الخصم
    - سلطان/نايف/ستاس: يرون الكل
    - محمد: يرى المعلقة له فقط
    - الموظف: يرى معاملاته فقط
    """
    role = user.get("role")
    query = {}
    
    if role == "mohammed":
        # محمد يرى المعلقة له
        query["$or"] = [
            {"status": "pending_ceo"},
            {"approval_chain": {"$elemMatch": {"actor_id": user["user_id"]}}}
        ]
    elif role == "employee":
        emp = await db.employees.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if emp:
            query["employee_id"] = emp["id"]
    
    if status:
        query["status"] = status
    if employee_id and role not in ["employee"]:
        query["employee_id"] = employee_id
    
    items = await db.deduction_transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    return items


@router.get("/pending")
async def get_pending_for_user(user=Depends(get_current_user)):
    """جلب المعاملات المعلقة للمستخدم الحالي"""
    role = user.get("role")
    
    if role == "mohammed":
        items = await db.deduction_transactions.find(
            {"status": "pending_ceo"}, 
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    elif role == "stas":
        items = await db.deduction_transactions.find(
            {"status": "pending_execution"}, 
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    elif role in ["sultan", "naif"]:
        # المعاملات التي أنشأها
        items = await db.deduction_transactions.find(
            {"created_by": user["user_id"]}, 
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    else:
        items = []
    
    return items


@router.get("/{ref_no}")
async def get_deduction_transaction(ref_no: str, user=Depends(get_current_user)):
    """جلب معاملة خصم بالرقم المرجعي"""
    item = await db.deduction_transactions.find_one({"ref_no": ref_no}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")
    return item


@router.post("")
async def create_deduction_transaction(
    req: DeductionTransactionCreate,
    user=Depends(require_roles('sultan', 'naif'))
):
    """
    إنشاء معاملة خصم جديدة
    - فقط سلطان/نايف يمكنهم الإنشاء
    - تُرسل تلقائياً لمحمد للموافقة
    """
    # التحقق من الموظف
    employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # جلب العقد للراتب
    contract = await db.contracts_v2.find_one({
        "employee_id": req.employee_id,
        "status": "active"
    }, {"_id": 0})
    
    daily_salary = 0
    if contract:
        monthly_salary = contract.get("basic_salary", 0)
        daily_salary = monthly_salary / 30
    
    now = datetime.now(timezone.utc).isoformat()
    ref_no = await get_next_ref_no()
    
    transaction = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "deduction",
        
        # بيانات الموظف
        "employee_id": req.employee_id,
        "employee_name_ar": employee.get("full_name_ar") or employee.get("full_name"),
        "employee_number": employee.get("employee_number"),
        
        # تفاصيل الخصم
        "amount": req.amount,
        "reason": req.reason,
        "month": req.month,
        "breakdown": req.breakdown or {},
        "daily_salary": daily_salary,
        
        # الحالة
        "status": "pending_ceo",
        "current_stage": "ceo",
        "workflow": WORKFLOW,
        
        # سلسلة الموافقات
        "approval_chain": [
            {
                "stage": "ops",
                "action": "created",
                "actor_id": user["user_id"],
                "actor_name": user.get("full_name_ar") or user.get("full_name"),
                "actor_role": user.get("role"),
                "timestamp": now,
                "note": req.note
            }
        ],
        
        # قرار محمد
        "ceo_decision": None,  # approve_salary | approve_settlement | reject
        "ceo_decision_note": None,
        "ceo_decided_at": None,
        
        # التنفيذ
        "executed_by": None,
        "executed_at": None,
        "execution_note": None,
        
        # أين ينعكس
        "deduct_from": None,  # salary | settlement
        "reflected_in_ledger": False,
        "ledger_entry_id": None,
        
        # Metadata
        "created_by": user["user_id"],
        "created_by_name": user.get("full_name_ar") or user.get("full_name"),
        "created_at": now,
        "updated_at": now
    }
    
    await db.deduction_transactions.insert_one(transaction)
    transaction.pop("_id", None)
    
    # إرسال إشعار لمحمد
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        await create_notification(
            recipient_id="mohammed",
            notification_type=NotificationType.TRANSACTION,
            title_ar=f"معاملة خصم جديدة - {ref_no}",
            title_en=f"New Deduction Transaction - {ref_no}",
            message_ar=f"معاملة خصم بمبلغ {req.amount} ر.س للموظف {employee.get('full_name_ar')} بانتظار قرارك",
            message_en=f"Deduction of {req.amount} SAR for {employee.get('full_name')} awaiting your decision",
            priority=NotificationPriority.HIGH,
            data={"ref_no": ref_no, "type": "deduction_transaction"}
        )
    except Exception as e:
        print(f"Notification error: {e}")
    
    return {
        "success": True,
        "message_ar": f"تم إنشاء معاملة الخصم برقم {ref_no} وإرسالها لمحمد",
        "message_en": f"Deduction transaction {ref_no} created and sent to Mohammed",
        "transaction": transaction
    }


@router.post("/{ref_no}/ceo-decision")
async def ceo_decision(
    ref_no: str,
    req: ApprovalAction,
    user=Depends(require_roles('mohammed'))
):
    """
    قرار محمد على معاملة الخصم
    
    الخيارات:
    - approve_salary: موافقة - خصم من الراتب (يُرسل لستاس للتنفيذ)
    - approve_settlement: موافقة - ترحيل للمخالصة (يُرسل لستاس للتنفيذ)
    - reject: رفض المعاملة
    """
    if req.action not in ['approve_salary', 'approve_settlement', 'reject']:
        raise HTTPException(status_code=400, detail="الإجراء غير صحيح")
    
    item = await db.deduction_transactions.find_one({"ref_no": ref_no}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")
    
    if item["status"] != "pending_ceo":
        raise HTTPException(status_code=400, detail="هذه المعاملة تم اتخاذ قرار عليها مسبقاً")
    
    now = datetime.now(timezone.utc).isoformat()
    
    approval_entry = {
        "stage": "ceo",
        "action": req.action,
        "actor_id": user["user_id"],
        "actor_name": user.get("full_name_ar") or user.get("full_name"),
        "actor_role": "mohammed",
        "timestamp": now,
        "note": req.note
    }
    
    if req.action == 'reject':
        new_status = "rejected"
        deduct_from = None
        message_ar = "تم رفض معاملة الخصم"
    else:
        new_status = "pending_execution"
        deduct_from = "salary" if req.action == "approve_salary" else "settlement"
        message_ar = f"تم اعتماد الخصم {'من الراتب' if deduct_from == 'salary' else 'مؤجل للمخالصة'} - بانتظار تنفيذ ستاس"
    
    await db.deduction_transactions.update_one(
        {"ref_no": ref_no},
        {
            "$set": {
                "status": new_status,
                "current_stage": "stas" if new_status == "pending_execution" else None,
                "ceo_decision": req.action,
                "ceo_decision_note": req.note,
                "ceo_decided_at": now,
                "deduct_from": deduct_from,
                "updated_at": now
            },
            "$push": {"approval_chain": approval_entry}
        }
    )
    
    # إشعار لستاس إذا تمت الموافقة
    if new_status == "pending_execution":
        try:
            from services.notification_service import create_notification
            from models.notifications import NotificationType, NotificationPriority
            
            await create_notification(
                recipient_id="stas",
                notification_type=NotificationType.TRANSACTION,
                title_ar=f"معاملة خصم للتنفيذ - {ref_no}",
                title_en=f"Deduction Transaction for Execution - {ref_no}",
                message_ar=f"معاملة خصم {ref_no} بانتظار تنفيذك",
                message_en=f"Deduction {ref_no} awaiting your execution",
                priority=NotificationPriority.HIGH,
                data={"ref_no": ref_no, "type": "deduction_transaction"}
            )
        except Exception as e:
            print(f"Notification error: {e}")
    
    return {
        "success": True,
        "message_ar": message_ar,
        "status": new_status
    }


@router.post("/{ref_no}/execute")
async def execute_deduction(
    ref_no: str,
    req: ExecuteAction,
    user=Depends(require_roles('stas'))
):
    """
    تنفيذ معاملة الخصم - ستاس فقط
    
    يتم:
    1. تأكيد التنفيذ
    2. إضافة للسجل المالي (finance_ledger)
    3. إشعار الموظف
    """
    if not req.confirm:
        raise HTTPException(
            status_code=400, 
            detail="يجب تأكيد التنفيذ بتحديد confirm: true"
        )
    
    item = await db.deduction_transactions.find_one({"ref_no": ref_no}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")
    
    if item["status"] != "pending_execution":
        raise HTTPException(status_code=400, detail="هذه المعاملة ليست بانتظار التنفيذ")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # إضافة للسجل المالي
    ledger_entry = {
        "id": str(uuid.uuid4()),
        "employee_id": item["employee_id"],
        "type": "debit",
        "category": "deduction",
        "amount": item["amount"],
        "description_ar": f"خصم - {item['reason']}",
        "description_en": f"Deduction - {item['reason']}",
        "reference_type": "deduction_transaction",
        "reference_id": ref_no,
        "month": item["month"],
        "deferred_to_settlement": item["deduct_from"] == "settlement",
        "settled": False,
        "created_at": now,
        "created_by": user["user_id"]
    }
    
    await db.finance_ledger.insert_one(ledger_entry)
    ledger_id = ledger_entry["id"]
    ledger_entry.pop("_id", None)
    
    # تحديث المعاملة
    approval_entry = {
        "stage": "stas",
        "action": "executed",
        "actor_id": user["user_id"],
        "actor_name": user.get("full_name_ar") or user.get("full_name"),
        "actor_role": "stas",
        "timestamp": now,
        "note": req.note
    }
    
    await db.deduction_transactions.update_one(
        {"ref_no": ref_no},
        {
            "$set": {
                "status": "executed",
                "current_stage": None,
                "executed_by": user["user_id"],
                "executed_at": now,
                "execution_note": req.note,
                "reflected_in_ledger": True,
                "ledger_entry_id": ledger_id,
                "updated_at": now
            },
            "$push": {"approval_chain": approval_entry}
        }
    )
    
    # إشعار الموظف
    try:
        from services.notification_service import create_notification
        from models.notifications import NotificationType, NotificationPriority
        
        emp = await db.employees.find_one({"id": item["employee_id"]}, {"_id": 0})
        if emp and emp.get("user_id"):
            deduct_location = "من راتبك" if item["deduct_from"] == "salary" else "عند المخالصة"
            
            await create_notification(
                recipient_id=emp["user_id"],
                notification_type=NotificationType.DEDUCTION,
                title_ar=f"تم تنفيذ خصم - {ref_no}",
                title_en=f"Deduction Executed - {ref_no}",
                message_ar=f"تم خصم {item['amount']} ر.س بسبب: {item['reason']}. سيتم الخصم {deduct_location}",
                message_en=f"Deduction of {item['amount']} SAR for: {item['reason']}",
                priority=NotificationPriority.HIGH,
                data={"ref_no": ref_no, "type": "deduction_transaction", "amount": item["amount"]}
            )
    except Exception as e:
        print(f"Notification error: {e}")
    
    return {
        "success": True,
        "message_ar": f"تم تنفيذ معاملة الخصم {ref_no} وإضافتها للسجل المالي",
        "message_en": f"Deduction {ref_no} executed and added to finance ledger",
        "ledger_entry": ledger_entry
    }


@router.get("/{ref_no}/summary")
async def get_transaction_summary(ref_no: str, user=Depends(get_current_user)):
    """
    ملخص المعاملة للعرض والطباعة
    يشمل كل التفاصيل اللازمة
    """
    item = await db.deduction_transactions.find_one({"ref_no": ref_no}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="المعاملة غير موجودة")
    
    # جلب بيانات الموظف
    employee = await db.employees.find_one({"id": item["employee_id"]}, {"_id": 0})
    
    # جلب العقد
    contract = await db.contracts_v2.find_one({
        "employee_id": item["employee_id"],
        "status": {"$in": ["active", "terminated"]}
    }, {"_id": 0})
    
    return {
        "transaction": item,
        "employee": {
            "id": employee.get("id") if employee else "",
            "name_ar": employee.get("full_name_ar") if employee else "",
            "name_en": employee.get("full_name") if employee else "",
            "employee_number": employee.get("employee_number") if employee else "",
            "national_id": employee.get("national_id") or employee.get("iqama_number", "") if employee else "",
            "job_title": contract.get("job_title_ar") if contract else "",
            "department": contract.get("department_ar") if contract else ""
        },
        "contract": {
            "basic_salary": contract.get("basic_salary", 0) if contract else 0,
            "daily_salary": (contract.get("basic_salary", 0) / 30) if contract else 0
        },
        "status_label": STATUS_LABELS.get(item["status"], {"ar": item["status"], "en": item["status"]}),
        "deduct_from_label": {
            "salary": {"ar": "خصم من الراتب", "en": "Deduct from Salary"},
            "settlement": {"ar": "ترحيل للمخالصة", "en": "Defer to Settlement"}
        }.get(item.get("deduct_from"), {"ar": "-", "en": "-"})
    }
