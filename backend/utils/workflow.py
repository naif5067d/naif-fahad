"""
Workflow Engine - Strict Order Enforcement
Transaction path: Employee → Supervisor → Sultan → Mohammed (if escalated) → STAS → Execute

Rules:
- If requester has no supervisor → go directly to Sultan (ops)
- If requester IS supervisor → skip supervisor step
- A stage cannot review itself
- Transaction must exist in only ONE stage at a time
- No backward jump except STAS return or CEO rejection
- Only STAS can Execute or Cancel
- After Execute → immutable (read-only)
- Escalation: Sultan can escalate to Mohammed (CEO), freezing Sultan's permissions
- CEO can only accept (→ STAS) or reject (→ back to ops)
"""

from database import db
from fastapi import HTTPException

# Strict workflow definitions
WORKFLOW_MAP = {
    "leave_request": ["supervisor", "ops", "stas"],
    "finance_60": ["finance", "ceo", "stas"],  # Sultan creates → Salah audits → Mohammed approves → STAS executes
    "settlement": ["ceo", "stas"],  # Only Sultan initiates, Mohammed approves
    "warning": ["ops", "stas"],
    "contract": ["ops", "stas"],
    "asset": ["ops", "stas"],
    "attendance_correction": ["ops", "stas"],
    "add_finance_code": ["ops", "stas"],
    "tangible_custody": ["employee_accept", "stas"],  # Sultan/Naif create → Employee accepts → STAS executes
    "tangible_custody_return": ["stas"],  # Sultan creates return → STAS executes
}

# Role to stage mapping
STAGE_ROLES = {
    "supervisor": ["supervisor"],
    "ops": ["sultan", "naif"],
    "finance": ["salah"],
    "ceo": ["mohammed"],
    "stas": ["stas"],
    "employee_accept": [],  # Special: validated by employee_id match
}

# Valid transitions (from_stage -> allowed_to_stages)
VALID_TRANSITIONS = {
    "created": ["supervisor", "ops", "finance", "employee_accept"],
    "supervisor": ["ops"],
    "ops": ["finance", "ceo", "stas"],  # Depends on workflow; escalation adds ceo
    "finance": ["ceo", "stas"],
    "ceo": ["stas", "ops"],  # CEO can reject back to ops
    "employee_accept": ["stas"],
    "stas": ["executed", "rejected", "return"],
    "executed": [],  # Immutable
    "rejected": [],  # Immutable
}


async def get_employee_by_user_id(user_id: str):
    """Get employee record by user_id"""
    return await db.employees.find_one({"user_id": user_id}, {"_id": 0})


async def get_employee_supervisor(employee):
    """Get the supervisor's employee record"""
    if not employee or not employee.get('supervisor_id'):
        return None
    return await db.employees.find_one({"id": employee['supervisor_id']}, {"_id": 0})


async def should_skip_supervisor_stage(employee, requester_user_id: str) -> bool:
    """
    Determine if supervisor stage should be skipped.
    Skip if:
    1. Employee has no supervisor assigned
    2. Requester IS the supervisor (self-supervision scenario)
    3. Employee's actual supervisor is NOT a 'supervisor' role (e.g., ops/sultan)
    """
    if not employee:
        return True
    if not employee.get('supervisor_id'):
        return True
    supervisor_emp = await get_employee_supervisor(employee)
    if not supervisor_emp:
        return True
    if supervisor_emp.get('user_id') == requester_user_id:
        return True
    supervisor_user = await db.users.find_one({"id": supervisor_emp.get('user_id')}, {"_id": 0})
    if not supervisor_user:
        return True
    if supervisor_user.get('role') != 'supervisor':
        return True
    return False


def build_workflow_for_transaction(base_workflow: list, skip_supervisor: bool) -> list:
    """Build the actual workflow based on conditions"""
    workflow = base_workflow[:]
    if skip_supervisor and 'supervisor' in workflow:
        workflow = [s for s in workflow if s != 'supervisor']
    return workflow


async def validate_stage_actor(transaction: dict, actor_user_id: str, actor_role: str) -> dict:
    """
    Validate that the actor can perform actions on the current stage.
    Returns validation result with details.
    """
    current_stage = transaction.get('current_stage')
    status = transaction.get('status')

    # Check if transaction is already finalized
    if status in ('executed', 'rejected', 'cancelled'):
        return {
            "valid": False,
            "error": "error.transaction_finalized",
            "error_detail": f"Transaction is already {status} and cannot be modified"
        }

    # Special handling for employee_accept stage
    if current_stage == 'employee_accept':
        emp = await db.employees.find_one({"id": transaction.get('employee_id')}, {"_id": 0})
        if not emp or emp.get('user_id') != actor_user_id:
            return {
                "valid": False,
                "error": "error.not_assigned_employee",
                "error_detail": "Only the assigned employee can accept or reject this custody"
            }
        return {"valid": True, "stage": current_stage}

    # Check if escalated and actor is the escalator (frozen)
    if transaction.get('escalated') and current_stage == 'ceo':
        if actor_role in ('sultan', 'naif'):
            return {
                "valid": False,
                "error": "error.escalation_frozen",
                "error_detail": "Your permissions are frozen for this escalated transaction"
            }

    # Check if actor's role is allowed for current stage
    allowed_roles = STAGE_ROLES.get(current_stage, [])

    # STAS can act on any stage (override capability)
    if actor_role == 'stas':
        return {"valid": True, "stage": current_stage}

    if actor_role not in allowed_roles:
        return {
            "valid": False,
            "error": "error.unauthorized_stage",
            "error_detail": f"Role {actor_role} cannot act on stage {current_stage}"
        }

    # Prevent self-approval: actor cannot approve their own transaction
    if transaction.get('created_by') == actor_user_id:
        return {
            "valid": False,
            "error": "error.self_approval",
            "error_detail": "You cannot approve your own transaction"
        }

    # For supervisor stage: verify actor is actually the supervisor
    if current_stage == 'supervisor':
        emp = await db.employees.find_one({"id": transaction.get('employee_id')}, {"_id": 0})
        if emp:
            supervisor = await get_employee_supervisor(emp)
            if not supervisor or supervisor.get('user_id') != actor_user_id:
                return {
                    "valid": False,
                    "error": "error.not_supervisor",
                    "error_detail": "You are not the supervisor of this employee"
                }

    return {"valid": True, "stage": current_stage}


def get_next_stage(workflow: list, current_stage: str) -> str:
    """Get the next stage in the workflow"""
    if current_stage not in workflow:
        return None
    current_idx = workflow.index(current_stage)
    if current_idx < len(workflow) - 1:
        return workflow[current_idx + 1]
    return None


async def validate_transition(from_stage: str, to_stage: str, workflow: list) -> bool:
    """Validate that a transition is allowed"""
    allowed = VALID_TRANSITIONS.get(from_stage, [])
    next_in_workflow = get_next_stage(workflow, from_stage)
    return to_stage in allowed or to_stage == next_in_workflow


async def can_initiate_transaction(tx_type: str, user_role: str, user_id: str) -> dict:
    """Validate if user can initiate a specific transaction type."""
    if tx_type == 'settlement':
        if user_role not in ['sultan', 'stas']:
            return {
                "valid": False,
                "error": "error.settlement_ops_only",
                "error_detail": "Only Sultan can initiate settlement"
            }

    if tx_type == 'finance_60':
        if user_role not in ['sultan', 'stas']:
            return {
                "valid": False,
                "error": "error.finance_60_sultan_only",
                "error_detail": "Only Sultan can create financial custody (60 Code)"
            }

    if tx_type == 'tangible_custody':
        if user_role not in ['sultan', 'naif', 'stas']:
            return {
                "valid": False,
                "error": "error.tangible_custody_ops_only",
                "error_detail": "Only Sultan or Naif can create tangible custody"
            }

    if tx_type == 'tangible_custody_return':
        if user_role not in ['sultan', 'stas']:
            return {
                "valid": False,
                "error": "error.tangible_return_sultan_only",
                "error_detail": "Only Sultan can initiate custody return"
            }

    if tx_type == 'add_finance_code':
        if user_role not in ['sultan', 'naif', 'stas']:
            return {
                "valid": False,
                "error": "error.finance_code_ops_only",
                "error_detail": "Only Operations or STAS can add finance codes"
            }

    if tx_type == 'warning':
        if user_role not in ['sultan', 'naif', 'stas']:
            return {
                "valid": False,
                "error": "error.warning_ops_only",
                "error_detail": "Only Operations can issue warnings"
            }

    return {"valid": True}


async def validate_only_stas_can_execute(actor_role: str) -> dict:
    """Ensure only STAS can execute or cancel transactions"""
    if actor_role != 'stas':
        return {
            "valid": False,
            "error": "error.stas_only_execute",
            "error_detail": "Only STAS can execute or cancel transactions"
        }
    return {"valid": True}
