from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from database import db
from utils.auth import get_current_user, require_roles
from utils.workflow import WORKFLOW_MAP, can_initiate_transaction
from routes.transactions import get_next_ref_no
from utils.inkind_custody_pdf import generate_inkind_custody_pdf, generate_custody_return_pdf
from datetime import datetime, timezone
import uuid
import io

router = APIRouter(prefix="/api/custody", tags=["custody"])


class TangibleCustodyRequest(BaseModel):
    employee_id: str
    item_name: str
    item_name_ar: Optional[str] = ""
    description: Optional[str] = ""
    serial_number: Optional[str] = ""
    estimated_value: Optional[float] = 0


class CustodyReturnRequest(BaseModel):
    custody_id: str  # The active custody record ID
    note: Optional[str] = ""


@router.post("/tangible")
async def create_tangible_custody(req: TangibleCustodyRequest, user=Depends(get_current_user)):
    """Create tangible custody assignment. Sultan or Naif only."""
    role = user.get('role')

    perm = await can_initiate_transaction('tangible_custody', role, user['user_id'])
    if not perm['valid']:
        raise HTTPException(status_code=403, detail=perm['error_detail'])

    emp = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="الموظف غير موجود")

    ref_no = await get_next_ref_no()
    workflow = WORKFLOW_MAP["tangible_custody"][:]
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "tangible_custody",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": req.employee_id,
        "data": {
            "item_name": req.item_name,
            "item_name_ar": req.item_name_ar or req.item_name,
            "description": req.description or "",
            "serial_number": req.serial_number or "",
            "estimated_value": req.estimated_value or 0,
            "employee_name": emp['full_name'],
            "employee_name_ar": emp.get('full_name_ar', ''),
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Tangible custody: {req.item_name} assigned to {emp['full_name']}",
            "stage": "created"
        }],
        "approval_chain": [],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx


@router.post("/tangible/return")
async def create_custody_return(req: CustodyReturnRequest, user=Depends(get_current_user)):
    """Sultan confirms received custody item → goes to STAS for execution."""
    role = user.get('role')

    perm = await can_initiate_transaction('tangible_custody_return', role, user['user_id'])
    if not perm['valid']:
        raise HTTPException(status_code=403, detail=perm['error_detail'])

    # Find the active custody record
    custody = await db.custody_ledger.find_one({"id": req.custody_id, "status": "active"}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="سجل العهدة غير موجود")

    ref_no = await get_next_ref_no()
    workflow = WORKFLOW_MAP["tangible_custody_return"][:]
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "tangible_custody_return",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": custody['employee_id'],
        "data": {
            "custody_id": req.custody_id,
            "item_name": custody['item_name'],
            "item_name_ar": custody.get('item_name_ar', ''),
            "serial_number": custody.get('serial_number', ''),
            "employee_name": custody.get('employee_name', ''),
            "employee_name_ar": custody.get('employee_name_ar', ''),
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Custody return: {custody['item_name']} - received from employee",
            "stage": "created"
        }],
        "approval_chain": [],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx


@router.get("/employee/{employee_id}")
async def get_employee_custodies(employee_id: str, user=Depends(get_current_user)):
    """Get all active tangible custodies for an employee."""
    custodies = await db.custody_ledger.find(
        {"employee_id": employee_id, "status": "active"}, {"_id": 0}
    ).sort("assigned_at", -1).to_list(100)
    return custodies


@router.get("/all")
async def get_all_custodies(user=Depends(get_current_user)):
    """Get all custody records (for admins) - includes pending transactions."""
    role = user.get('role')
    
    if role in ('employee', 'supervisor'):
        # Employees see only their own from custody_ledger
        emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
        if not emp:
            return []
        custodies = await db.custody_ledger.find(
            {"employee_id": emp['id']}, {"_id": 0}
        ).sort("assigned_at", -1).to_list(100)
        return custodies
    
    # للإدارة: نجمع من custody_ledger + transactions المعلقة والمنفذة
    result = []
    
    # 1. العهد النشطة من custody_ledger
    active_custodies = await db.custody_ledger.find({}, {"_id": 0}).sort("assigned_at", -1).to_list(500)
    for c in active_custodies:
        c['source'] = 'ledger'
        result.append(c)
    
    # 2. معاملات العهد المعلقة (لم تُنفذ بعد)
    pending_custody_txs = await db.transactions.find({
        "type": "tangible_custody",
        "status": {"$nin": ["executed", "rejected", "cancelled"]}
    }, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for tx in pending_custody_txs:
        data = tx.get('data', {})
        # تحويل المعاملة إلى صيغة العهدة
        custody_item = {
            "id": tx['id'],
            "ref_no": tx.get('ref_no', ''),
            "employee_id": tx.get('employee_id', ''),
            "employee_name": data.get('employee_name', ''),
            "employee_name_ar": data.get('employee_name_ar', ''),
            "item_name": data.get('item_name', ''),
            "item_name_ar": data.get('item_name_ar', ''),
            "description": data.get('description', ''),
            "serial_number": data.get('serial_number', ''),
            "estimated_value": data.get('estimated_value', 0),
            "status": "pending",  # معلقة
            "tx_status": tx.get('status', ''),
            "current_stage": tx.get('current_stage', ''),
            "assigned_at": tx.get('created_at', ''),
            "source": 'transaction'
        }
        result.append(custody_item)
    
    return result


@router.get("/check-clearance/{employee_id}")
async def check_clearance_eligibility(employee_id: str, user=Depends(get_current_user)):
    """Check if employee can have clearance (no active custody)."""
    active_custodies = await db.custody_ledger.find(
        {"employee_id": employee_id, "status": "active"},
        {"_id": 0, "id": 1, "item_name": 1, "item_name_ar": 1, "serial_number": 1}
    ).to_list(100)
    
    active_count = len(active_custodies)
    
    return {
        "eligible": active_count == 0,
        "active_custody_count": active_count,
        "active_custodies": active_custodies,
        "message_ar": f"يوجد {active_count} عهدة عينية لم تُرجَع" if active_count > 0 else "لا توجد عهد عينية نشطة",
        "message_en": f"Employee has {active_count} unreturned custody items" if active_count > 0 else "No active custody"
    }


# ============================================================
# إنشاء PDF للعهدة مع QR
# ============================================================

@router.get("/{custody_id}/pdf")
async def get_custody_pdf(custody_id: str, lang: str = "ar", user=Depends(get_current_user)):
    """Generate PDF for custody with QR Code"""
    # جلب العهدة
    custody = await db.custody_ledger.find_one({"id": custody_id}, {"_id": 0})
    if not custody:
        # محاولة البحث في المعاملات
        custody = await db.transactions.find_one({"id": custody_id, "type": "tangible_custody"}, {"_id": 0})
    
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    # جلب بيانات الموظف
    emp_id = custody.get('employee_id')
    emp = await db.employees.find_one({"id": emp_id}, {"_id": 0}) or {}
    
    # توليد PDF
    pdf_bytes, pdf_hash, integrity_id = generate_inkind_custody_pdf(custody, emp, lang)
    
    # تحديث السجل بـ integrity_id
    if custody.get('type') == 'tangible_custody':
        await db.transactions.update_one(
            {"id": custody_id},
            {"$set": {"pdf_hash": pdf_hash, "integrity_id": integrity_id}}
        )
    else:
        await db.custody_ledger.update_one(
            {"id": custody_id},
            {"$set": {"pdf_hash": pdf_hash, "integrity_id": integrity_id}}
        )
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=custody_{custody_id}.pdf"}
    )


@router.get("/return/{return_id}/pdf")
async def get_custody_return_pdf(return_id: str, lang: str = "ar", user=Depends(get_current_user)):
    """Generate PDF for custody return with STAS signature"""
    # جلب معاملة الإرجاع
    return_tx = await db.transactions.find_one(
        {"id": return_id, "type": "tangible_custody_return"},
        {"_id": 0}
    )
    
    if not return_tx:
        raise HTTPException(status_code=404, detail="معاملة الإرجاع غير موجودة")
    
    # جلب العهدة الأصلية
    custody_id = return_tx.get('data', {}).get('custody_id')
    custody = await db.custody_ledger.find_one({"id": custody_id}, {"_id": 0}) or {}
    
    # توليد PDF
    pdf_bytes, pdf_hash, integrity_id = generate_custody_return_pdf(custody, return_tx, lang)
    
    # تحديث السجل
    await db.transactions.update_one(
        {"id": return_id},
        {"$set": {"pdf_hash": pdf_hash, "integrity_id": integrity_id}}
    )
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=custody_return_{return_id}.pdf"}
    )


# ============================================================
# توقيع الموظف على استلام العهدة
# ============================================================

class EmployeeSignRequest(BaseModel):
    custody_id: str
    signature_data: Optional[str] = ""  # Base64 signature image (optional)


@router.post("/sign-receipt")
async def employee_sign_custody_receipt(req: EmployeeSignRequest, user=Depends(get_current_user)):
    """Employee signs to confirm custody receipt"""
    now = datetime.now(timezone.utc).isoformat()
    
    # جلب العهدة من custody_ledger
    custody = await db.custody_ledger.find_one({"id": req.custody_id}, {"_id": 0})
    if not custody:
        raise HTTPException(status_code=404, detail="العهدة غير موجودة")
    
    # التحقق من أن الموظف هو صاحب العهدة
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp or emp['id'] != custody['employee_id']:
        raise HTTPException(status_code=403, detail="يمكن فقط لصاحب العهدة التوقيع")
    
    # التحقق من أنها لم تُوقَّع مسبقاً
    if custody.get('employee_signed'):
        raise HTTPException(status_code=400, detail="تم التوقيع مسبقاً")
    
    # تحديث السجل
    await db.custody_ledger.update_one(
        {"id": req.custody_id},
        {"$set": {
            "employee_signed": True,
            "employee_signed_at": now,
            "employee_signed_by": user['user_id'],
            "employee_signature_data": req.signature_data,
            "updated_at": now
        }}
    )
    
    return {
        "success": True,
        "message_ar": "تم توقيع استلام العهدة بنجاح",
        "message_en": "Custody receipt signed successfully",
        "signed_at": now
    }


# ============================================================
# توقيع STAS على الإرجاع (تنفيذ الإرجاع)
# ============================================================

@router.post("/execute-return/{return_tx_id}")
async def stas_execute_custody_return(return_tx_id: str, user=Depends(require_roles('stas'))):
    """STAS executes custody return - marks custody as returned"""
    now = datetime.now(timezone.utc).isoformat()
    
    # جلب معاملة الإرجاع
    return_tx = await db.transactions.find_one(
        {"id": return_tx_id, "type": "tangible_custody_return"},
        {"_id": 0}
    )
    
    if not return_tx:
        raise HTTPException(status_code=404, detail="معاملة الإرجاع غير موجودة")
    
    if return_tx.get('status') == 'executed':
        raise HTTPException(status_code=400, detail="تم تنفيذ الإرجاع مسبقاً")
    
    custody_id = return_tx.get('data', {}).get('custody_id')
    
    # تحديث العهدة إلى "مُرجَعة"
    await db.custody_ledger.update_one(
        {"id": custody_id},
        {"$set": {
            "status": "returned",
            "returned_at": now,
            "returned_by": user['user_id'],
            "return_tx_id": return_tx_id,
            "stas_signed": True,
            "stas_signed_at": now,
            "updated_at": now
        }}
    )
    
    # تحديث معاملة الإرجاع
    await db.transactions.update_one(
        {"id": return_tx_id},
        {
            "$set": {
                "status": "executed",
                "executed_at": now,
                "executed_by": user['user_id'],
                "current_stage": "executed",
                "updated_at": now
            },
            "$push": {
                "timeline": {
                    "event": "executed",
                    "actor": user['user_id'],
                    "actor_name": user.get('full_name', 'STAS'),
                    "timestamp": now,
                    "note": "تم تنفيذ إرجاع العهدة بواسطة STAS",
                    "stage": "executed"
                }
            }
        }
    )
    
    return {
        "success": True,
        "message_ar": "تم تنفيذ إرجاع العهدة بنجاح",
        "message_en": "Custody return executed successfully",
        "executed_at": now,
        "custody_id": custody_id
    }


# ============================================================
# التحقق من QR العهدة
# ============================================================

@router.get("/verify/{integrity_id}")
async def verify_custody_qr(integrity_id: str):
    """Verify custody QR code"""
    # البحث في custody_ledger
    custody = await db.custody_ledger.find_one(
        {"integrity_id": integrity_id},
        {"_id": 0}
    )
    
    if custody:
        return {
            "valid": True,
            "type": "custody",
            "data": custody
        }
    
    # البحث في transactions
    tx = await db.transactions.find_one(
        {"integrity_id": integrity_id, "type": {"$in": ["tangible_custody", "tangible_custody_return"]}},
        {"_id": 0}
    )
    
    if tx:
        return {
            "valid": True,
            "type": tx.get('type'),
            "data": tx
        }
    
    return {
        "valid": False,
        "message": "QR Code غير صالح أو غير موجود"
    }

