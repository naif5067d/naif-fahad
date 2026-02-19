"""
Contract Routes V2 - Complete Contract Management System
Implements:
- Contract CRUD with proper lifecycle
- Serial generation (DAC-YYYY-XXX)
- Role-based permissions (Sultan/Naif: create+edit+submit | STAS: everything)
- Activation, Termination, Close
- Search and filtering
- PDF generation
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from database import db
from utils.auth import get_current_user, require_roles
from services.contract_service import (
    generate_contract_serial,
    get_next_contract_version,
    validate_no_active_contract,
    validate_contract_for_activation,
    activate_contract,
    terminate_contract,
    close_contract,
    search_contracts,
    has_active_contract,
    TERMINATION_REASONS,
    create_contract_snapshot
)
from services.contract_template import generate_contract_pdf
from datetime import datetime, timezone
import uuid
import io

router = APIRouter(prefix="/api/contracts-v2", tags=["contracts-v2"])


# ============================================================
# MODELS
# ============================================================

class ContractCreate(BaseModel):
    # موظف جديد أو قديم
    is_new_employee: bool = False
    employee_id: Optional[str] = ""
    employee_code: str = ""
    employee_name: str = ""
    employee_name_ar: str = ""
    email: str = ""
    phone: str = ""
    national_id: str = ""
    
    contract_category: str = "employment"  # employment | internship_unpaid
    employment_type: str = "unlimited"  # unlimited | fixed_term | trial_paid
    
    job_title: str = ""
    job_title_ar: str = ""
    department: str = ""
    department_ar: str = ""
    
    start_date: str  # YYYY-MM-DD
    end_date: Optional[str] = None
    
    probation_months: int = 3
    notice_period_days: int = 30
    
    # الراتب والبدلات
    basic_salary: float = 0
    housing_allowance: float = 0
    transport_allowance: float = 0
    nature_of_work_allowance: float = 0  # بدل طبيعة العمل
    other_allowances: float = 0
    
    wage_definition: str = "basic_only"  # basic_only | basic_plus_fixed
    
    # الإجازة السنوية: 21 أو 30 يوم فقط
    annual_leave_days: int = 21  # للواجهة الحالية
    annual_policy_days: int = 21  # السياسة الرسمية - 21 أو 30 فقط
    # رصيد الاستئذان الشهري (0-3 ساعات)
    monthly_permission_hours: int = 2
    
    is_migrated: bool = False
    leave_opening_balance: Optional[Dict[str, float]] = None  # {"annual": 10.5, "sick": 5, "permission_hours": 2}
    
    supervisor_id: Optional[str] = None
    notes: str = ""
    
    # معلومات البنك (إلزامية)
    bank_name: str = ""
    bank_iban: str = ""


class ContractUpdate(BaseModel):
    employee_name: Optional[str] = None
    employee_name_ar: Optional[str] = None
    
    job_title: Optional[str] = None
    job_title_ar: Optional[str] = None
    department: Optional[str] = None
    department_ar: Optional[str] = None
    
    employment_type: Optional[str] = None
    end_date: Optional[str] = None
    
    probation_months: Optional[int] = None
    notice_period_days: Optional[int] = None
    
    basic_salary: Optional[float] = None
    housing_allowance: Optional[float] = None
    transport_allowance: Optional[float] = None
    nature_of_work_allowance: Optional[float] = None  # بدل طبيعة العمل
    other_allowances: Optional[float] = None
    
    wage_definition: Optional[str] = None
    leave_opening_balance: Optional[Dict[str, int]] = None
    
    supervisor_id: Optional[str] = None
    notes: Optional[str] = None
    
    # معلومات البنك (قابلة للتعديل دائماً)
    bank_name: Optional[str] = None
    bank_iban: Optional[str] = None


class SubmitToSTAS(BaseModel):
    note: Optional[str] = None


class TerminateContract(BaseModel):
    termination_date: str  # YYYY-MM-DD
    termination_reason: str  # resignation | termination | contract_expiry | retirement | death | mutual_agreement
    note: Optional[str] = None


# ============================================================
# LIST & SEARCH
# ============================================================

@router.get("")
async def list_contracts(
    status: Optional[str] = None,
    category: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 100,
    user=Depends(get_current_user)
):
    """
    List all contracts with optional filtering.
    Accessible by: sultan, naif, stas, salah, mohammed
    """
    role = user.get("role")
    
    if role == "employee":
        # Employee can only see their own contracts
        emp = await db.employees.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not emp:
            return []
        contracts = await db.contracts_v2.find(
            {"employee_id": emp["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        return contracts
    
    elif role == "supervisor":
        # Supervisor can see their team's contracts
        emp = await db.employees.find_one({"user_id": user["user_id"]}, {"_id": 0})
        if not emp:
            return []
        reports = await db.employees.find({"supervisor_id": emp["id"]}, {"_id": 0}).to_list(100)
        report_ids = [r["id"] for r in reports] + [emp["id"]]
        contracts = await db.contracts_v2.find(
            {"employee_id": {"$in": report_ids}}, {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        return contracts
    
    # Admin roles can search
    return await search_contracts(query=query, status=status, category=category, limit=limit)


@router.get("/search")
async def search_contracts_endpoint(
    q: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    user=Depends(require_roles('sultan', 'naif', 'stas', 'salah', 'mohammed'))
):
    """
    Advanced search for contracts.
    Search by: contract_serial, employee_code, employee_name
    """
    return await search_contracts(query=q, status=status, category=category, limit=limit)


@router.get("/pending-stas")
async def get_pending_stas_contracts(user=Depends(require_roles('stas'))):
    """Get contracts pending STAS execution"""
    contracts = await db.contracts_v2.find(
        {"status": "pending_stas"}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    return contracts


# ============================================================
# GET SINGLE CONTRACT
# ============================================================

@router.get("/{contract_id}")
async def get_contract(contract_id: str, user=Depends(get_current_user)):
    """Get a single contract by ID"""
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        # Try by serial
        contract = await db.contracts_v2.find_one({"contract_serial": contract_id}, {"_id": 0})
    
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    return contract


@router.get("/employee/{employee_id}")
async def get_employee_contracts(employee_id: str, user=Depends(get_current_user)):
    """Get all contracts for an employee"""
    contracts = await db.contracts_v2.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).sort("version", -1).to_list(50)
    return contracts


# ============================================================
# CREATE CONTRACT
# ============================================================

@router.post("")
async def create_contract(
    req: ContractCreate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Create a new contract.
    If is_new_employee=True, creates the employee first.
    Status will be 'draft'.
    Sultan/Naif can create, only STAS can execute.
    """
    now = datetime.now(timezone.utc).isoformat()
    employee = None
    
    # إذا موظف جديد، أنشئه أولاً
    if req.is_new_employee:
        if not req.employee_name_ar:
            raise HTTPException(status_code=400, detail="اسم الموظف بالعربي مطلوب")
        
        # إنشاء موظف جديد
        new_employee_id = str(uuid.uuid4())
        employee_number = req.employee_code or f"EMP-{new_employee_id[:8].upper()}"
        
        employee = {
            "id": new_employee_id,
            "user_id": new_employee_id,  # سيتم ربطه لاحقاً
            "employee_number": employee_number,
            "full_name": req.employee_name or req.employee_name_ar,
            "full_name_ar": req.employee_name_ar,
            "email": req.email,
            "phone": req.phone,
            "national_id": req.national_id,
            "position": req.job_title,
            "position_ar": req.job_title_ar,
            "department": req.department,
            "department_ar": req.department_ar,
            "join_date": req.start_date,
            "supervisor_id": req.supervisor_id,
            "is_active": True,
            "role": "employee",
            "created_at": now,
            "updated_at": now
        }
        
        await db.employees.insert_one(employee)
        req.employee_id = new_employee_id
        req.employee_code = employee_number
    else:
        # تحقق من وجود الموظف
        employee = await db.employees.find_one({"id": req.employee_id}, {"_id": 0})
        if not employee:
            raise HTTPException(status_code=404, detail="الموظف غير موجود")
    
    # Validate no other active contract if this will be activated
    is_valid, error = await validate_no_active_contract(req.employee_id)
    # Note: We allow creating draft contracts even if active exists
    
    # Validate category and employment_type combination
    if req.contract_category == "internship_unpaid" and req.employment_type != "unlimited":
        req.employment_type = "unlimited"  # Internships are always unlimited term
    
    if req.contract_category == "internship_unpaid":
        # No salary for unpaid internship
        req.basic_salary = 0
        req.housing_allowance = 0
        req.transport_allowance = 0
        req.other_allowances = 0
    
    # Generate serial
    contract_serial = await generate_contract_serial()
    
    # Get version
    version = await get_next_contract_version(req.employee_id)
    
    contract = {
        "id": str(uuid.uuid4()),
        "contract_serial": contract_serial,
        "version": version,
        
        "employee_id": req.employee_id,
        "employee_code": req.employee_code,
        "employee_name": req.employee_name or req.employee_name_ar,
        "employee_name_ar": req.employee_name_ar or req.employee_name,
        
        "contract_category": req.contract_category,
        "employment_type": req.employment_type,
        
        "job_title": req.job_title or employee.get("position", ""),
        "job_title_ar": req.job_title_ar or employee.get("position_ar", ""),
        "department": req.department or employee.get("department", ""),
        "department_ar": req.department_ar or employee.get("department_ar", ""),
        
        "start_date": req.start_date,
        "end_date": req.end_date,
        
        "probation_months": req.probation_months,
        "notice_period_days": req.notice_period_days,
        
        "basic_salary": req.basic_salary,
        "housing_allowance": req.housing_allowance,
        "transport_allowance": req.transport_allowance,
        "nature_of_work_allowance": req.nature_of_work_allowance if hasattr(req, 'nature_of_work_allowance') else 0,
        "other_allowances": req.other_allowances,
        
        "wage_definition": req.wage_definition,
        
        # معلومات البنك
        "bank_name": req.bank_name,
        "bank_iban": req.bank_iban,
        
        # الإجازة السنوية والاستئذان
        "annual_leave_days": req.annual_leave_days,
        "annual_policy_days": req.annual_policy_days if req.annual_policy_days in [21, 30] else 21,  # السياسة الرسمية
        "monthly_permission_hours": min(req.monthly_permission_hours, 3),  # الحد الأقصى 3
        
        "is_migrated": req.is_migrated,
        "leave_opening_balance": req.leave_opening_balance,
        
        "supervisor_id": req.supervisor_id or employee.get("supervisor_id"),
        "notes": req.notes,
        
        "status": "draft",
        "status_history": [{
            "from_status": None,
            "to_status": "draft",
            "actor_id": user["user_id"],
            "actor_name": user.get("full_name", ""),
            "timestamp": now,
            "note": "تم إنشاء العقد"
        }],
        
        "termination_date": None,
        "termination_reason": None,
        
        "created_by": user["user_id"],
        "created_at": now,
        "updated_at": now,
        
        "executed_by": None,
        "executed_at": None,
        
        "snapshots": []
    }
    
    await db.contracts_v2.insert_one(contract)
    contract.pop("_id", None)
    
    return contract


# ============================================================
# UPDATE CONTRACT (Before Execution Only)
# ============================================================

@router.put("/{contract_id}")
async def update_contract(
    contract_id: str,
    req: ContractUpdate,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Update a contract.
    - Draft/Pending: All fields can be edited
    - Active: Only bank_name, bank_iban, notes can be edited (للمخالصة)
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Build update dict
    update_data = {"updated_at": now}
    
    # Fields that can ALWAYS be updated (even for active contracts)
    always_editable = ["bank_name", "bank_iban", "notes"]
    
    if contract["status"] in ("draft", "pending_stas"):
        # Draft/Pending: All fields can be edited
        for field, value in req.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
    elif contract["status"] == "active":
        # Active: Only bank/notes fields can be edited
        for field in always_editable:
            value = getattr(req, field, None)
            if value is not None:
                update_data[field] = value
        
        # Check if user tried to update other fields
        for field, value in req.dict(exclude_unset=True).items():
            if field not in always_editable and value is not None:
                if contract.get(field) != value:
                    # Silently ignore non-bank fields for active contracts
                    pass
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"لا يمكن تعديل عقد بحالة {contract['status']}."
        )
    
    # If salary fields updated and category is internship_unpaid, reset to 0
    if contract["contract_category"] == "internship_unpaid":
        for salary_field in ["basic_salary", "housing_allowance", "transport_allowance", "other_allowances"]:
            if salary_field in update_data:
                update_data[salary_field] = 0
    
    await db.contracts_v2.update_one(
        {"id": contract_id},
        {"$set": update_data}
    )
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return updated


# ============================================================
# SUBMIT TO STAS
# ============================================================

@router.post("/{contract_id}/submit")
async def submit_to_stas(
    contract_id: str,
    req: SubmitToSTAS = SubmitToSTAS(),
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Submit a draft contract to STAS for execution.
    Changes status from draft to pending_stas.
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    if contract["status"] != "draft":
        raise HTTPException(
            status_code=400, 
            detail=f"يمكن إرسال العقود بحالة draft فقط. الحالة الحالية: {contract['status']}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.contracts_v2.update_one(
        {"id": contract_id},
        {
            "$set": {
                "status": "pending_stas",
                "submitted_at": now,
                "submitted_by": user["user_id"],
                "updated_at": now
            },
            "$push": {
                "status_history": {
                    "from_status": "draft",
                    "to_status": "pending_stas",
                    "actor_id": user["user_id"],
                    "actor_name": user.get("full_name", ""),
                    "timestamp": now,
                    "note": req.note or "تم إرسال العقد إلى STAS للتنفيذ"
                }
            }
        }
    )
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return updated


# ============================================================
# RETURN TO DRAFT (STAS)
# ============================================================

@router.post("/{contract_id}/return-to-draft")
async def return_to_draft(
    contract_id: str,
    note: str = "تم إرجاع العقد للمراجعة",
    user=Depends(require_roles('stas'))
):
    """
    Return a pending_stas contract back to draft for corrections.
    STAS only.
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    if contract["status"] != "pending_stas":
        raise HTTPException(
            status_code=400, 
            detail=f"يمكن إرجاع العقود بحالة pending_stas فقط. الحالة الحالية: {contract['status']}"
        )
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.contracts_v2.update_one(
        {"id": contract_id},
        {
            "$set": {
                "status": "draft",
                "updated_at": now
            },
            "$push": {
                "status_history": {
                    "from_status": "pending_stas",
                    "to_status": "draft",
                    "actor_id": user["user_id"],
                    "actor_name": "STAS",
                    "timestamp": now,
                    "note": note
                }
            }
        }
    )
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return updated


# ============================================================
# EXECUTE/ACTIVATE CONTRACT (STAS ONLY)
# ============================================================

@router.post("/{contract_id}/execute")
async def execute_contract(
    contract_id: str,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """
    Execute and activate a contract.
    سلطان و STAS يستطيعون التنفيذ.
    
    This will:
    1. Validate all conditions
    2. Check no other active contract
    3. Create User if not exists
    4. Enable attendance
    5. Initialize leave balance
    6. Create audit log
    7. Generate PDF snapshot
    """
    success, error, contract = await activate_contract(
        contract_id=contract_id,
        executor_id=user["user_id"],
        executor_name=user.get("full_name", user.get("username", "Admin"))
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {
        "message": "تم تنفيذ وتفعيل العقد بنجاح",
        "contract": contract
    }


# ============================================================
# TERMINATE CONTRACT (Sultan, Naif, STAS)
# ============================================================

@router.post("/{contract_id}/terminate")
async def terminate_contract_endpoint(
    contract_id: str,
    req: TerminateContract,
    user=Depends(require_roles('stas', 'sultan', 'naif'))
):
    """
    Terminate an active contract.
    STAS exclusive operation.
    
    This will:
    1. Set termination date and reason
    2. Disable attendance and requests
    3. Keep user active for settlement process
    """
    success, error, contract = await terminate_contract(
        contract_id=contract_id,
        termination_date=req.termination_date,
        termination_reason=req.termination_reason,
        executor_id=user["user_id"],
        executor_name=user.get("full_name", "STAS"),
        note=req.note
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {
        "message": "تم إنهاء العقد بنجاح",
        "contract": contract
    }


# ============================================================
# CLOSE CONTRACT (After Settlement)
# ============================================================

@router.post("/{contract_id}/close")
async def close_contract_endpoint(
    contract_id: str,
    settlement_ref: Optional[str] = None,
    user=Depends(require_roles('stas'))
):
    """
    Close a terminated contract after settlement.
    Final state - no more changes allowed.
    """
    success, error, contract = await close_contract(
        contract_id=contract_id,
        executor_id=user["user_id"],
        settlement_ref=settlement_ref
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {
        "message": "تم إغلاق العقد نهائياً",
        "contract": contract
    }


# ============================================================
# DELETE CONTRACT (Draft Only)
# ============================================================

@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """
    Delete a contract.
    Only allowed for draft status.
    Executed contracts cannot be deleted.
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    if contract["status"] not in ("draft", "pending_stas"):
        raise HTTPException(
            status_code=400, 
            detail=f"لا يمكن حذف عقد بحالة {contract['status']}. يمكن حذف العقود بحالة draft أو pending_stas فقط."
        )
    
    await db.contracts_v2.delete_one({"id": contract_id})
    
    return {"message": "تم حذف العقد", "contract_serial": contract["contract_serial"]}


# ============================================================
# PDF GENERATION
# ============================================================

@router.get("/{contract_id}/pdf")
async def get_contract_pdf(
    contract_id: str,
    lang: str = "ar",
    user=Depends(get_current_user)
):
    """Generate and return contract PDF"""
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")
    
    # Get branding
    branding = await db.settings.find_one({"type": "company_branding"}, {"_id": 0})
    
    # Generate PDF
    pdf_bytes, pdf_hash, integrity_id = generate_contract_pdf(
        contract=contract,
        branding=branding,
        lang=lang
    )
    
    filename = f"contract_{contract['contract_serial']}_{lang}.pdf"
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "X-PDF-Hash": pdf_hash,
            "X-Integrity-ID": integrity_id
        }
    )


# ============================================================
# TERMINATION REASONS LIST
# ============================================================

@router.get("/meta/termination-reasons")
async def get_termination_reasons(user=Depends(get_current_user)):
    """Get list of valid termination reasons"""
    return TERMINATION_REASONS


# ============================================================
# CONTRACT STATISTICS
# ============================================================

@router.get("/stats/summary")
async def get_contract_stats(user=Depends(require_roles('sultan', 'naif', 'stas', 'salah', 'mohammed'))):
    """Get contract statistics"""
    
    pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    
    results = await db.contracts_v2.aggregate(pipeline).to_list(100)
    
    stats = {
        "draft": 0,
        "pending_stas": 0,
        "active": 0,
        "terminated": 0,
        "closed": 0,
        "total": 0
    }
    
    for r in results:
        status = r["_id"]
        if status in stats:
            stats[status] = r["count"]
        stats["total"] += r["count"]
    
    # Category breakdown
    cat_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$contract_category", "count": {"$sum": 1}}}
    ]
    
    cat_results = await db.contracts_v2.aggregate(cat_pipeline).to_list(100)
    
    stats["by_category"] = {r["_id"]: r["count"] for r in cat_results}
    
    return stats


# ============================================================
# AUDIT LOG
# ============================================================

@router.get("/{contract_id}/audit-log")
async def get_contract_audit_log(
    contract_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """Get audit log for a contract"""
    logs = await db.contract_audit_log.find(
        {"contract_id": contract_id}, {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    return logs


# ============================================================
# SNAPSHOTS
# ============================================================

@router.get("/{contract_id}/snapshots")
async def get_contract_snapshots(
    contract_id: str,
    user=Depends(require_roles('sultan', 'naif', 'stas'))
):
    """Get all snapshots for a contract"""
    snapshots = await db.contract_snapshots.find(
        {"contract_id": contract_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return snapshots
