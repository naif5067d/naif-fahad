"""
Workflow Engine - Strict Order Enforcement
Transaction path: Employee → Supervisor → Sultan → Mohammed (if escalated) → STAS → Execute

Rules:
- If requester has no supervisor → go directly to Sultan (ops)
- If requester IS supervisor → skip supervisor step
- A stage cannot review itself
- Transaction must exist in only ONE stage at a time
- No backward jump except STAS return
- Only STAS can Execute or Cancel
- After Execute → immutable (read-only)
"""

from database import db
from fastapi import HTTPException

# Strict workflow definitions
WORKFLOW_MAP = {
    "leave_request": ["supervisor", "ops", "stas"],
    "finance_60": ["supervisor", "ops", "finance", "stas"],
    "settlement": ["ops", "ceo", "stas"],  # Only Sultan initiates, Mohammed approves
    "warning": ["ops", "stas"],
    "contract": ["ops", "stas"],
    "asset": ["ops", "stas"],
    "attendance_correction": ["ops", "stas"],
    "add_finance_code": ["ops", "stas"],
}

# Role to stage mapping
STAGE_ROLES = {
    "supervisor": ["supervisor"],
    "ops": ["sultan", "naif"],
    "finance": ["salah"],
    "ceo": ["mohammed"],
    "stas": ["stas"],
}

# Valid transitions (from_stage -> allowed_to_stages)
VALID_TRANSITIONS = {
    "created": ["supervisor", "ops"],  # Can skip supervisor
    "supervisor": ["ops"],
    "ops": ["finance", "ceo", "stas"],  # Depends on workflow
    "finance": ["stas"],
    "ceo": ["stas"],
    "stas": ["executed", "rejected", "return"],  # STAS can return to previous
    "executed": [],  # Immutable - no transitions
    "rejected": [],  # Immutable - no transitions
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
       In this case, the workflow should go directly to 'ops' stage
    """
    if not employee:
        return True
    
    # No supervisor assigned
    if not employee.get('supervisor_id'):
        return True
    
    # Get the supervisor's employee record
    supervisor_emp = await get_employee_supervisor(employee)
    if not supervisor_emp:
        return True
    
    # Check if requester is the supervisor (self-approval prevention)
    if supervisor_emp.get('user_id') == requester_user_id:
        return True
    
    # Get the supervisor's user record to check their role
    supervisor_user = await db.users.find_one({"id": supervisor_emp.get('user_id')}, {"_id": 0})
    if not supervisor_user:
        return True
    
    # If the supervisor has a role OTHER than 'supervisor' (e.g., sultan, naif),
    # skip the supervisor stage - it will go directly to 'ops'
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
    employee_id = transaction.get('employee_id')
    
    # Check if transaction is already finalized
    if status in ('executed', 'rejected'):
        return {
            "valid": False,
            "error": "error.transaction_finalized",
            "error_detail": f"Transaction is already {status} and cannot be modified"
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
        emp = await db.employees.find_one({"id": employee_id}, {"_id": 0})
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
    # Check if transition is in valid transitions
    allowed = VALID_TRANSITIONS.get(from_stage, [])
    
    # Also allow transitioning to the next stage in workflow
    next_in_workflow = get_next_stage(workflow, from_stage)
    
    return to_stage in allowed or to_stage == next_in_workflow


async def can_initiate_transaction(tx_type: str, user_role: str, user_id: str) -> dict:
    """
    Validate if user can initiate a specific transaction type.
    """
    # Settlement can only be initiated by Sultan (ops)
    if tx_type == 'settlement':
        if user_role not in ['sultan', 'naif', 'stas']:
            return {
                "valid": False,
                "error": "error.settlement_ops_only",
                "error_detail": "Only Operations Admin (Sultan) can initiate settlement"
            }
    
    # Finance codes can only be added by ops or stas
    if tx_type == 'add_finance_code':
        if user_role not in ['sultan', 'naif', 'stas']:
            return {
                "valid": False,
                "error": "error.finance_code_ops_only",
                "error_detail": "Only Operations or STAS can add finance codes"
            }
    
    # Warning can only be issued by ops
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
