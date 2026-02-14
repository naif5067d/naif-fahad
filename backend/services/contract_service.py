"""
Contract Service - Business Logic Layer
Handles all contract-related operations including:
- Serial generation (DAC-YYYY-XXX)
- Lifecycle management (draft → pending_stas → active → terminated → closed)
- Activation rules
- Termination logic
- User creation on execution
- Leave balance initialization
"""

from database import db
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
import uuid


# ============================================================
# CONTRACT SERIAL GENERATOR
# ============================================================

async def generate_contract_serial() -> str:
    """
    Generate unique contract serial: DAC-YYYY-XXX
    - Resets sequence at the start of each year
    - Format: DAC-2026-001, DAC-2026-002, etc.
    """
    current_year = datetime.now(timezone.utc).year
    counter_id = f"contract_serial_{current_year}"
    
    result = await db.counters.find_one_and_update(
        {"id": counter_id},
        {"$inc": {"seq": 1}},
        return_document=True,
        upsert=True
    )
    
    seq = result.get("seq", 1) if result else 1
    return f"DAC-{current_year}-{seq:03d}"


async def get_next_contract_version(employee_id: str) -> int:
    """Get next version number for employee's contracts"""
    existing = await db.contracts_v2.find(
        {"employee_id": employee_id}
    ).sort("version", -1).limit(1).to_list(1)
    
    if existing:
        return existing[0].get("version", 0) + 1
    return 1


# ============================================================
# CONTRACT VALIDATION
# ============================================================

async def validate_no_active_contract(employee_id: str, exclude_contract_id: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that employee doesn't have another active contract.
    Returns (is_valid, error_message)
    """
    query = {
        "employee_id": employee_id,
        "status": "active"
    }
    if exclude_contract_id:
        query["id"] = {"$ne": exclude_contract_id}
    
    existing = await db.contracts_v2.find_one(query)
    if existing:
        return False, f"الموظف لديه عقد نشط بالفعل: {existing.get('contract_serial')}"
    return True, None


async def validate_contract_for_activation(contract: dict) -> Tuple[bool, List[str]]:
    """
    Validate all conditions for contract activation.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # 1. Check status is pending_stas
    if contract.get("status") != "pending_stas":
        errors.append(f"حالة العقد غير صالحة للتنفيذ: {contract.get('status')}")
    
    # 2. Check no other active contract
    is_valid, error = await validate_no_active_contract(
        contract["employee_id"], 
        exclude_contract_id=contract["id"]
    )
    if not is_valid:
        errors.append(error)
    
    # 3. Check required fields
    required_fields = ["employee_id", "employee_code", "contract_category", "start_date", "basic_salary"]
    for field in required_fields:
        if not contract.get(field):
            errors.append(f"حقل مطلوب ناقص: {field}")
    
    # 4. Validate dates
    if contract.get("end_date") and contract.get("start_date"):
        if contract["end_date"] < contract["start_date"]:
            errors.append("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
    
    return len(errors) == 0, errors


# ============================================================
# CONTRACT LIFECYCLE
# ============================================================

CONTRACT_STATUS_TRANSITIONS = {
    "draft": ["pending_stas"],
    "pending_stas": ["active", "draft"],  # Can go back to draft or forward to active
    "active": ["terminated"],
    "terminated": ["closed"],
    "closed": []  # Terminal state
}


def can_transition(current_status: str, new_status: str) -> bool:
    """Check if status transition is allowed"""
    allowed = CONTRACT_STATUS_TRANSITIONS.get(current_status, [])
    return new_status in allowed


async def transition_contract_status(
    contract_id: str, 
    new_status: str, 
    actor_id: str,
    note: str = None
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Transition contract to new status with validation.
    Returns (success, error_message, updated_contract)
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return False, "العقد غير موجود", None
    
    current_status = contract.get("status", "draft")
    
    if not can_transition(current_status, new_status):
        return False, f"لا يمكن الانتقال من {current_status} إلى {new_status}", None
    
    now = datetime.now(timezone.utc).isoformat()
    
    update = {
        "$set": {
            "status": new_status,
            "updated_at": now
        },
        "$push": {
            "status_history": {
                "from_status": current_status,
                "to_status": new_status,
                "actor_id": actor_id,
                "timestamp": now,
                "note": note or f"Status changed to {new_status}"
            }
        }
    }
    
    await db.contracts_v2.update_one({"id": contract_id}, update)
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return True, None, updated


# ============================================================
# CONTRACT ACTIVATION (STAS ONLY)
# ============================================================

async def activate_contract(
    contract_id: str,
    executor_id: str,
    executor_name: str = "STAS"
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Activate a contract - STAS exclusive operation.
    This will:
    1. Validate all conditions
    2. Check no other active contract
    3. Create User if not exists
    4. Enable attendance
    5. Initialize leave balance
    6. Create audit log
    7. Generate PDF snapshot
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return False, "العقد غير موجود", None
    
    # Validate
    is_valid, errors = await validate_contract_for_activation(contract)
    if not is_valid:
        return False, " | ".join(errors), None
    
    now = datetime.now(timezone.utc).isoformat()
    employee_id = contract["employee_id"]
    employee_code = contract["employee_code"]
    
    # 1. Check for existing user
    existing_user = await db.users.find_one({"employee_id": employee_id})
    
    # 2. If no user exists, create one
    if not existing_user:
        from utils.auth import hash_password
        
        # Generate username from employee code
        username = employee_code.lower().replace("-", "")
        
        # Check if username exists
        username_exists = await db.users.find_one({"username": username})
        if username_exists:
            username = f"{username}_{str(uuid.uuid4())[:4]}"
        
        new_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "password_hash": hash_password("DarAlCode2026!"),  # Default password
            "full_name": contract.get("employee_name", ""),
            "full_name_ar": contract.get("employee_name_ar", ""),
            "role": "employee",  # Default role
            "email": f"{username}@daralcode.com",
            "is_active": True,
            "employee_id": employee_id,
            "created_at": now,
            "created_by_contract": contract_id
        }
        await db.users.insert_one(new_user)
    else:
        # Activate existing user
        await db.users.update_one(
            {"employee_id": employee_id},
            {"$set": {"is_active": True, "updated_at": now}}
        )
    
    # 3. Update employee to active
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"is_active": True, "has_active_contract": True, "updated_at": now}}
    )
    
    # 4. Initialize leave balance if migrated or new
    if contract.get("is_migrated") and contract.get("leave_opening_balance"):
        opening = contract["leave_opening_balance"]
        for leave_type, days in opening.items():
            if days > 0:
                await db.leave_ledger.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": employee_id,
                    "transaction_id": None,
                    "contract_id": contract_id,
                    "type": "credit",
                    "leave_type": leave_type,
                    "days": days,
                    "note": f"رصيد افتتاحي من العقد المُهاجر {contract['contract_serial']}",
                    "date": now,
                    "created_at": now
                })
    else:
        # Standard leave entitlement from contract start
        leave_entitlement = {"annual": 25, "sick": 30, "emergency": 5}
        for leave_type, days in leave_entitlement.items():
            await db.leave_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "transaction_id": None,
                "contract_id": contract_id,
                "type": "credit",
                "leave_type": leave_type,
                "days": days,
                "note": f"رصيد ابتدائي من العقد {contract['contract_serial']}",
                "date": now,
                "created_at": now
            })
    
    # 5. Update contract to active
    update = {
        "$set": {
            "status": "active",
            "executed_by": executor_id,
            "executed_at": now,
            "updated_at": now
        },
        "$push": {
            "status_history": {
                "from_status": "pending_stas",
                "to_status": "active",
                "actor_id": executor_id,
                "actor_name": executor_name,
                "timestamp": now,
                "note": "تم تنفيذ وتفعيل العقد"
            }
        }
    }
    
    await db.contracts_v2.update_one({"id": contract_id}, update)
    
    # 6. Create audit log
    await db.contract_audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "contract_id": contract_id,
        "contract_serial": contract["contract_serial"],
        "employee_id": employee_id,
        "action": "activate",
        "actor_id": executor_id,
        "actor_name": executor_name,
        "details": {
            "basic_salary": contract.get("basic_salary"),
            "start_date": contract.get("start_date"),
            "is_migrated": contract.get("is_migrated", False),
        },
        "timestamp": now
    })
    
    # 7. Create snapshot
    snapshot = await create_contract_snapshot(contract_id, "activation", executor_id)
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return True, None, updated


# ============================================================
# CONTRACT TERMINATION (STAS ONLY)
# ============================================================

TERMINATION_REASONS = {
    "resignation": {"name_en": "Resignation", "name_ar": "استقالة"},
    "termination": {"name_en": "Termination", "name_ar": "إنهاء من الشركة"},
    "contract_expiry": {"name_en": "Contract Expiry", "name_ar": "انتهاء العقد"},
    "retirement": {"name_en": "Retirement", "name_ar": "تقاعد"},
    "death": {"name_en": "Death", "name_ar": "وفاة"},
    "mutual_agreement": {"name_en": "Mutual Agreement", "name_ar": "اتفاق متبادل"},
}


async def terminate_contract(
    contract_id: str,
    termination_date: str,
    termination_reason: str,
    executor_id: str,
    executor_name: str = "STAS",
    note: str = None
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Terminate a contract - STAS exclusive operation.
    This will:
    1. Validate contract is active
    2. Set termination date and reason
    3. Disable attendance and requests
    4. NOT deactivate user yet (settlement pending)
    5. Create audit log
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return False, "العقد غير موجود", None
    
    if contract.get("status") != "active":
        return False, f"لا يمكن إنهاء عقد بحالة: {contract.get('status')}", None
    
    if termination_reason not in TERMINATION_REASONS:
        return False, f"سبب الإنهاء غير صالح: {termination_reason}", None
    
    now = datetime.now(timezone.utc).isoformat()
    employee_id = contract["employee_id"]
    
    # 1. Update contract
    update = {
        "$set": {
            "status": "terminated",
            "termination_date": termination_date,
            "termination_reason": termination_reason,
            "termination_note": note,
            "terminated_by": executor_id,
            "terminated_at": now,
            "updated_at": now
        },
        "$push": {
            "status_history": {
                "from_status": "active",
                "to_status": "terminated",
                "actor_id": executor_id,
                "actor_name": executor_name,
                "timestamp": now,
                "note": note or f"تم إنهاء العقد - السبب: {TERMINATION_REASONS[termination_reason]['name_ar']}"
            }
        }
    }
    
    await db.contracts_v2.update_one({"id": contract_id}, update)
    
    # 2. Update employee - disable attendance but keep user active until settlement
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "has_active_contract": False,
            "contract_terminated": True,
            "termination_date": termination_date,
            "updated_at": now
        }}
    )
    
    # 3. Create audit log
    await db.contract_audit_log.insert_one({
        "id": str(uuid.uuid4()),
        "contract_id": contract_id,
        "contract_serial": contract["contract_serial"],
        "employee_id": employee_id,
        "action": "terminate",
        "actor_id": executor_id,
        "actor_name": executor_name,
        "details": {
            "termination_date": termination_date,
            "termination_reason": termination_reason,
            "termination_reason_ar": TERMINATION_REASONS[termination_reason]['name_ar'],
            "note": note
        },
        "timestamp": now
    })
    
    # 4. Create snapshot
    await create_contract_snapshot(contract_id, "termination", executor_id)
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return True, None, updated


# ============================================================
# CONTRACT CLOSE (After Settlement)
# ============================================================

async def close_contract(
    contract_id: str,
    executor_id: str,
    settlement_ref: str = None
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Close a terminated contract after settlement is complete.
    This is the final state.
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return False, "العقد غير موجود", None
    
    if contract.get("status") != "terminated":
        return False, f"لا يمكن إغلاق عقد بحالة: {contract.get('status')}", None
    
    now = datetime.now(timezone.utc).isoformat()
    employee_id = contract["employee_id"]
    
    # 1. Update contract to closed
    update = {
        "$set": {
            "status": "closed",
            "closed_at": now,
            "settlement_ref": settlement_ref,
            "updated_at": now
        },
        "$push": {
            "status_history": {
                "from_status": "terminated",
                "to_status": "closed",
                "actor_id": executor_id,
                "timestamp": now,
                "note": f"تم إغلاق العقد بعد المخالصة" + (f" رقم {settlement_ref}" if settlement_ref else "")
            }
        }
    }
    
    await db.contracts_v2.update_one({"id": contract_id}, update)
    
    # 2. Deactivate user completely
    await db.users.update_one(
        {"employee_id": employee_id},
        {"$set": {"is_active": False, "updated_at": now}}
    )
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"is_active": False, "updated_at": now}}
    )
    
    # 3. Final snapshot
    await create_contract_snapshot(contract_id, "closure", executor_id)
    
    updated = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    return True, None, updated


# ============================================================
# CONTRACT SNAPSHOT
# ============================================================

async def create_contract_snapshot(
    contract_id: str,
    snapshot_type: str,  # "activation", "termination", "closure", "version_change"
    creator_id: str
) -> dict:
    """
    Create an immutable snapshot of the contract at a point in time.
    """
    contract = await db.contracts_v2.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return None
    
    now = datetime.now(timezone.utc).isoformat()
    
    snapshot = {
        "id": str(uuid.uuid4()),
        "contract_id": contract_id,
        "contract_serial": contract.get("contract_serial"),
        "snapshot_type": snapshot_type,
        "data": contract,  # Full contract data at this moment
        "created_by": creator_id,
        "created_at": now
    }
    
    await db.contract_snapshots.insert_one(snapshot)
    
    # Update contract with snapshot reference
    await db.contracts_v2.update_one(
        {"id": contract_id},
        {"$push": {"snapshots": {"snapshot_id": snapshot["id"], "type": snapshot_type, "created_at": now}}}
    )
    
    snapshot.pop("_id", None)
    return snapshot


# ============================================================
# CHECK ACTIVE CONTRACT FOR EMPLOYEE
# ============================================================

async def has_active_contract(employee_id: str) -> Tuple[bool, Optional[dict]]:
    """
    Check if employee has an active contract.
    Returns (has_active, contract_if_active)
    """
    contract = await db.contracts_v2.find_one({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0})
    
    return contract is not None, contract


async def can_perform_attendance(employee_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if employee can perform attendance based on contract status.
    Returns (can_attend, error_message)
    """
    has_active, contract = await has_active_contract(employee_id)
    
    if not has_active:
        return False, "لا يوجد عقد نشط - لا يمكن تسجيل الحضور"
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Check start date
    if contract.get("start_date") and contract["start_date"] > today:
        return False, f"العقد يبدأ في {contract['start_date']} - لا يمكن تسجيل الحضور قبل ذلك"
    
    # Check if terminated
    if contract.get("termination_date") and contract["termination_date"] < today:
        return False, "تم إنهاء العقد - لا يمكن تسجيل الحضور"
    
    return True, None


async def can_submit_request(employee_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if employee can submit requests (leave, etc.) based on contract status.
    Returns (can_submit, error_message)
    """
    has_active, contract = await has_active_contract(employee_id)
    
    if not has_active:
        return False, "لا يوجد عقد نشط - لا يمكن تقديم طلبات"
    
    # Check category - internship_unpaid might have restrictions
    if contract.get("contract_category") == "internship_unpaid":
        # For now, allow requests but this can be restricted
        pass
    
    return True, None


# ============================================================
# CONTRACT SEARCH
# ============================================================

async def search_contracts(
    query: str = None,
    status: str = None,
    category: str = None,
    limit: int = 100
) -> List[dict]:
    """
    Search contracts by:
    - Contract serial (full or last 3 digits)
    - Employee code
    - Employee name
    """
    filter_query = {}
    
    if status:
        filter_query["status"] = status
    
    if category:
        filter_query["contract_category"] = category
    
    if query:
        query = query.strip()
        # Check if searching by last 3 digits of serial
        if query.isdigit() and len(query) <= 3:
            filter_query["contract_serial"] = {"$regex": f"-{query.zfill(3)}$"}
        else:
            # Full text search on multiple fields
            filter_query["$or"] = [
                {"contract_serial": {"$regex": query, "$options": "i"}},
                {"employee_code": {"$regex": query, "$options": "i"}},
                {"employee_name": {"$regex": query, "$options": "i"}},
                {"employee_name_ar": {"$regex": query, "$options": "i"}}
            ]
    
    contracts = await db.contracts_v2.find(
        filter_query, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return contracts
