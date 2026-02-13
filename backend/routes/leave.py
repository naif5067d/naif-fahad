from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database import db
from utils.auth import get_current_user
from utils.workflow import (
    WORKFLOW_MAP, should_skip_supervisor_stage, 
    build_workflow_for_transaction, get_employee_by_user_id
)
from utils.leave_rules import (
    get_employee_with_contract, validate_leave_request, 
    get_leave_balance, get_all_holidays
)
from routes.transactions import get_next_ref_no
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/api/leave", tags=["leave"])


class LeaveRequest(BaseModel):
    leave_type: str  # annual, sick, emergency
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    reason: str


@router.post("/request")
async def create_leave_request(req: LeaveRequest, user=Depends(get_current_user)):
    """
    Create a leave request with full pre-validation.
    Validates:
    - Employee is active with contract
    - Sufficient leave balance
    - No overlapping dates
    - Holiday adjustments
    """
    # Step 1: Validate employee and contract
    emp, contract, errors = await get_employee_with_contract(user['user_id'])
    
    if errors:
        # Return first error
        error = errors[0]
        raise HTTPException(status_code=400, detail=error['message'])
    
    # Step 2: Validate leave request (balance, overlap, dates)
    validation = await validate_leave_request(
        employee=emp,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date
    )
    
    if not validation['valid']:
        error = validation['errors'][0]
        raise HTTPException(status_code=400, detail=error['message'])
    
    # Step 3: Determine workflow (skip supervisor if applicable)
    skip_supervisor = await should_skip_supervisor_stage(emp, user['user_id'])
    base_workflow = WORKFLOW_MAP["leave_request"][:]
    workflow = build_workflow_for_transaction(base_workflow, skip_supervisor)
    
    first_stage = workflow[0]
    now = datetime.now(timezone.utc).isoformat()
    ref_no = await get_next_ref_no()

    tx = {
        "id": str(uuid.uuid4()),
        "ref_no": ref_no,
        "type": "leave_request",
        "status": f"pending_{first_stage}",
        "created_by": user['user_id'],
        "employee_id": emp['id'],
        "data": {
            "leave_type": req.leave_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "adjusted_end_date": validation['adjusted_end_date'],
            "working_days": validation['working_days'],
            "reason": req.reason,
            "employee_name": emp.get('full_name', ''),
            "employee_name_ar": emp.get('full_name_ar', ''),
            "balance_before": validation['balance_before'],
            "balance_after": validation['balance_after'],
            "sick_tier_info": validation.get('sick_tier_info'),
        },
        "current_stage": first_stage,
        "workflow": workflow,
        "workflow_skipped_stages": ['supervisor'] if skip_supervisor else [],
        "timeline": [{
            "event": "created",
            "actor": user['user_id'],
            "actor_name": user.get('full_name', ''),
            "timestamp": now,
            "note": f"Leave request: {req.leave_type}, {validation['working_days']} working days",
            "stage": "created"
        }],
        "approval_chain": [],
        "pdf_hash": None,
        "integrity_id": None,
        "created_at": now,
        "updated_at": now,
    }

    # Add warnings to transaction data if any
    if validation.get('warnings'):
        tx['data']['warnings'] = validation['warnings']

    await db.transactions.insert_one(tx)
    tx.pop('_id', None)
    return tx


@router.get("/balance")
async def get_my_leave_balance(user=Depends(get_current_user)):
    """Get current user's leave balance breakdown"""
    emp = await db.employees.find_one({"user_id": user['user_id']}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="Not an employee")
    
    # Calculate balance for each leave type
    balance = {}
    for leave_type in ['annual', 'sick', 'emergency']:
        balance[leave_type] = await get_leave_balance(emp['id'], leave_type)
    
    return balance


@router.get("/holidays")
async def get_holidays():
    """Get all holidays (system + manual)"""
    holidays = await db.public_holidays.find({}, {"_id": 0}).to_list(100)
    manual_holidays = await db.holidays.find({}, {"_id": 0}).to_list(100)
    
    all_holidays = []
    for h in holidays:
        h['source'] = 'system'
        all_holidays.append(h)
    for h in manual_holidays:
        h['source'] = 'manual'
        all_holidays.append(h)
    
    all_holidays.sort(key=lambda x: x.get('date', ''))
    return all_holidays
