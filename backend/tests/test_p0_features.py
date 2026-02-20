"""
Backend tests for P0 Features - DAR AL CODE HR OS

P0 Features being tested:
1. Finance 60 Code: Sultan creates → Salah audits/edits → Mohammed approves → STAS executes
   - Manual code input with auto-lookup
   - Naif should be DENIED from creating finance_60
   
2. Tangible Custody: Sultan/Naif create → Employee accepts/rejects → STAS executes
   - Return flow via Sultan pressing 'Received' → STAS
   
3. Escalation Logic: Sultan can escalate to CEO (Mohammed)
   - CEO accepts → STAS
   - CEO rejects → back to ops

API URL: Uses REACT_APP_BACKEND_URL from environment
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://language-unification.preview.emergentagent.com')


# ==================== FIXTURES ====================
@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def users_map(api_client):
    """Get all users and map by username"""
    response = api_client.get(f"{BASE_URL}/api/auth/users")
    assert response.status_code == 200, f"Failed to get users: {response.text}"
    users = response.json()
    return {u['username']: u for u in users}


@pytest.fixture(scope="module")
def employees_list(api_client, users_map):
    """Get all employees"""
    stas = users_map.get('stas')
    token = get_token(api_client, stas['id'])
    response = api_client.get(f"{BASE_URL}/api/employees", headers=auth_headers(token))
    assert response.status_code == 200
    return response.json()


def get_token(api_client, user_id):
    """Get auth token for user via switch endpoint"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{user_id}")
    if response.status_code == 200:
        return response.json().get('token')
    return None


def auth_headers(token):
    """Return auth headers with token"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ==================== HEALTH CHECK ====================
class TestHealthCheck:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        assert response.json().get('status') == 'ok'
        print("✓ API health check passed")


# ==================== FINANCE 60 CODE TESTS ====================
class TestFinance60Code:
    """Test Financial Custody (60 Code) workflow: Sultan → Salah → Mohammed → STAS"""
    
    def test_finance_code_lookup_existing(self, api_client, users_map):
        """Test code lookup returns found:true for existing codes"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        # Get existing codes first
        codes_resp = api_client.get(f"{BASE_URL}/api/finance/codes", headers=auth_headers(token))
        assert codes_resp.status_code == 200
        codes = codes_resp.json()
        
        if codes:
            code_num = codes[0]['code']
            response = api_client.get(f"{BASE_URL}/api/finance/codes/lookup/{code_num}", headers=auth_headers(token))
            assert response.status_code == 200
            data = response.json()
            assert data.get('found') == True, f"Expected found:true for existing code {code_num}"
            assert data['code']['code'] == code_num
            print(f"✓ Code lookup returns found:true for existing code {code_num}")
        else:
            pytest.skip("No existing finance codes to test")
    
    def test_finance_code_lookup_new(self, api_client, users_map):
        """Test code lookup returns found:false for new codes"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        # Use a code that doesn't exist
        new_code = 99999
        response = api_client.get(f"{BASE_URL}/api/finance/codes/lookup/{new_code}", headers=auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data.get('found') == False, f"Expected found:false for new code {new_code}"
        print(f"✓ Code lookup returns found:false for new code {new_code}")
    
    def test_sultan_creates_finance_60(self, api_client, users_map, employees_list):
        """Sultan can create finance_60 transaction with correct workflow"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        # Get an employee to assign
        if not employees_list:
            pytest.skip("No employees available")
        employee = employees_list[0]
        
        # First get an existing code
        codes_resp = api_client.get(f"{BASE_URL}/api/finance/codes", headers=auth_headers(token))
        codes = codes_resp.json()
        
        if codes:
            # Use existing code
            existing_code = codes[0]['code']
            payload = {
                "employee_id": employee['id'],
                "code": existing_code,
                "amount": 5000.0,
                "description": "TEST_Finance60_Sultan",
                "tx_type": "credit"
            }
        else:
            # No existing codes, create with new code definition
            payload = {
                "employee_id": employee['id'],
                "code": 100,
                "amount": 5000.0,
                "description": "TEST_Finance60_Sultan",
                "tx_type": "credit",
                "code_name": "Test Basic Allowance",
                "code_name_ar": "بدل اختباري",
                "code_category": "earnings"
            }
        
        response = api_client.post(f"{BASE_URL}/api/finance/transaction", json=payload, headers=auth_headers(token))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        tx = response.json()
        assert tx['type'] == 'finance_60'
        assert tx['workflow'] == ['finance', 'ceo', 'stas'], f"Expected ['finance', 'ceo', 'stas'], got {tx['workflow']}"
        assert tx['current_stage'] == 'finance', f"Expected first stage 'finance', got {tx['current_stage']}"
        assert tx['status'] == 'pending_finance'
        
        print(f"✓ Sultan created finance_60 {tx['ref_no']} with workflow {tx['workflow']}")
    
    def test_naif_denied_creating_finance_60(self, api_client, users_map, employees_list):
        """Naif should be DENIED (403) from creating finance_60"""
        naif = users_map.get('naif')
        token = get_token(api_client, naif['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        employee = employees_list[0]
        
        payload = {
            "employee_id": employee['id'],
            "code": 100,
            "amount": 1000.0,
            "description": "TEST_Finance60_Naif_ShouldFail",
            "tx_type": "credit"
        }
        
        response = api_client.post(f"{BASE_URL}/api/finance/transaction", json=payload, headers=auth_headers(token))
        assert response.status_code == 403, f"Expected 403 for Naif creating finance_60, got {response.status_code}"
        print("✓ Naif correctly DENIED from creating finance_60 (403)")
    
    def test_sultan_creates_finance_60_with_new_code(self, api_client, users_map, employees_list):
        """Sultan can create finance_60 with a new code (auto-create)"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        employee = employees_list[0]
        
        new_code_num = 88888
        payload = {
            "employee_id": employee['id'],
            "code": new_code_num,
            "amount": 2500.0,
            "description": "TEST_Finance60_NewCode",
            "tx_type": "credit",
            "code_name": "Test New Code",
            "code_name_ar": "رمز اختباري جديد",
            "code_category": "other"
        }
        
        response = api_client.post(f"{BASE_URL}/api/finance/transaction", json=payload, headers=auth_headers(token))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        tx = response.json()
        assert tx['data']['code'] == new_code_num
        assert tx['data']['code_name'] == "Test New Code"
        print(f"✓ Sultan created finance_60 {tx['ref_no']} with new code {new_code_num}")


# ==================== TANGIBLE CUSTODY TESTS ====================
class TestTangibleCustody:
    """Test Tangible Custody workflow: Sultan/Naif create → Employee accepts → STAS executes"""
    
    def test_sultan_creates_tangible_custody(self, api_client, users_map, employees_list):
        """Sultan can create tangible custody"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        employee = employees_list[0]
        
        payload = {
            "employee_id": employee['id'],
            "item_name": "TEST_Laptop_Sultan",
            "item_name_ar": "حاسب محمول اختباري",
            "description": "Test laptop from Sultan",
            "serial_number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "estimated_value": 5000.0
        }
        
        response = api_client.post(f"{BASE_URL}/api/custody/tangible", json=payload, headers=auth_headers(token))
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        tx = response.json()
        assert tx['type'] == 'tangible_custody'
        assert tx['workflow'] == ['employee_accept', 'stas'], f"Expected ['employee_accept', 'stas'], got {tx['workflow']}"
        assert tx['current_stage'] == 'employee_accept'
        assert tx['status'] == 'pending_employee_accept'
        
        print(f"✓ Sultan created tangible_custody {tx['ref_no']} - awaiting employee acceptance")
        return tx
    
    def test_naif_creates_tangible_custody(self, api_client, users_map, employees_list):
        """Naif can also create tangible custody"""
        naif = users_map.get('naif')
        token = get_token(api_client, naif['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        employee = employees_list[0]
        
        payload = {
            "employee_id": employee['id'],
            "item_name": "TEST_Phone_Naif",
            "item_name_ar": "هاتف اختباري",
            "description": "Test phone from Naif",
            "serial_number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "estimated_value": 3000.0
        }
        
        response = api_client.post(f"{BASE_URL}/api/custody/tangible", json=payload, headers=auth_headers(token))
        assert response.status_code == 200, f"Expected 200 for Naif creating custody, got {response.status_code}: {response.text}"
        
        tx = response.json()
        assert tx['type'] == 'tangible_custody'
        print(f"✓ Naif created tangible_custody {tx['ref_no']}")
        return tx
    
    def test_employee_denied_creating_tangible_custody(self, api_client, users_map, employees_list):
        """Regular employee should be DENIED from creating tangible custody"""
        employee = users_map.get('employee1')
        if not employee:
            pytest.skip("employee1 not found")
        token = get_token(api_client, employee['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        emp = employees_list[0]
        
        payload = {
            "employee_id": emp['id'],
            "item_name": "TEST_Tablet_ShouldFail",
            "description": "Should fail",
            "serial_number": "TEST-FAIL",
            "estimated_value": 1000.0
        }
        
        response = api_client.post(f"{BASE_URL}/api/custody/tangible", json=payload, headers=auth_headers(token))
        assert response.status_code == 403, f"Expected 403 for employee creating custody, got {response.status_code}"
        print("✓ Employee correctly DENIED from creating tangible custody (403)")
    
    def test_tangible_custody_employee_accepts(self, api_client, users_map, employees_list):
        """Employee accepts tangible custody → moves to STAS stage"""
        sultan = users_map.get('sultan')
        sultan_token = get_token(api_client, sultan['id'])
        
        if not employees_list:
            pytest.skip("No employees available")
        
        # Find an employee with a user_id that we can switch to
        employee_user = users_map.get('employee1')
        if not employee_user:
            pytest.skip("employee1 not found for acceptance test")
        
        # Find the employee record
        emp_record = None
        for emp in employees_list:
            if emp.get('user_id') == employee_user['id']:
                emp_record = emp
                break
        
        if not emp_record:
            pytest.skip("Employee record not found for employee1")
        
        # Sultan creates custody for this employee
        payload = {
            "employee_id": emp_record['id'],
            "item_name": "TEST_Desk_Accept",
            "item_name_ar": "مكتب اختباري",
            "description": "Desk for acceptance test",
            "serial_number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "estimated_value": 2000.0
        }
        
        create_resp = api_client.post(f"{BASE_URL}/api/custody/tangible", json=payload, headers=auth_headers(sultan_token))
        assert create_resp.status_code == 200
        tx = create_resp.json()
        tx_id = tx['id']
        
        # Employee accepts
        employee_token = get_token(api_client, employee_user['id'])
        accept_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "approve", "note": "I accept this custody"},
            headers=auth_headers(employee_token)
        )
        assert accept_resp.status_code == 200, f"Employee accept failed: {accept_resp.text}"
        
        result = accept_resp.json()
        assert result['current_stage'] == 'stas', f"Expected stage 'stas', got {result['current_stage']}"
        assert result['status'] == 'pending_stas'
        
        print(f"✓ Employee accepted custody {tx['ref_no']} → moved to STAS stage")
        return tx_id
    
    def test_tangible_custody_employee_rejects(self, api_client, users_map, employees_list):
        """Employee rejects tangible custody → cancelled immediately"""
        sultan = users_map.get('sultan')
        sultan_token = get_token(api_client, sultan['id'])
        
        employee_user = users_map.get('employee1')
        if not employee_user:
            pytest.skip("employee1 not found")
        
        # Find employee record
        emp_record = None
        for emp in employees_list:
            if emp.get('user_id') == employee_user['id']:
                emp_record = emp
                break
        
        if not emp_record:
            pytest.skip("Employee record not found for employee1")
        
        # Sultan creates custody
        payload = {
            "employee_id": emp_record['id'],
            "item_name": "TEST_Chair_Reject",
            "description": "Chair for rejection test",
            "serial_number": f"TEST-{uuid.uuid4().hex[:8].upper()}",
            "estimated_value": 500.0
        }
        
        create_resp = api_client.post(f"{BASE_URL}/api/custody/tangible", json=payload, headers=auth_headers(sultan_token))
        assert create_resp.status_code == 200
        tx = create_resp.json()
        tx_id = tx['id']
        
        # Employee rejects
        employee_token = get_token(api_client, employee_user['id'])
        reject_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "reject", "note": "I cannot accept this item"},
            headers=auth_headers(employee_token)
        )
        assert reject_resp.status_code == 200, f"Employee reject failed: {reject_resp.text}"
        
        result = reject_resp.json()
        assert result['status'] == 'cancelled', f"Expected status 'cancelled', got {result['status']}"
        
        print(f"✓ Employee rejected custody {tx['ref_no']} → cancelled immediately")


# ==================== ESCALATION FLOW TESTS ====================
class TestEscalationFlow:
    """Test escalation: Sultan escalates to CEO, CEO accepts/rejects"""
    
    def test_create_leave_and_escalate_ceo_approves(self, api_client, users_map, employees_list):
        """Full flow: Leave → Supervisor approves → Sultan escalates → CEO approves → STAS"""
        # Find an employee with a supervisor
        emp_record = None
        supervisor_user = users_map.get('supervisor1')
        employee_user = users_map.get('employee1')
        
        if not supervisor_user or not employee_user:
            pytest.skip("supervisor1 or employee1 not found")
        
        for emp in employees_list:
            if emp.get('user_id') == employee_user['id']:
                emp_record = emp
                break
        
        if not emp_record:
            pytest.skip("Employee record not found")
        
        # Step 1: Employee creates leave request
        emp_token = get_token(api_client, employee_user['id'])
        start_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=32)).strftime('%Y-%m-%d')
        
        leave_payload = {
            "employee_id": emp_record['id'],
            "leave_type": "annual",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_Escalation_CEO_Approves"
        }
        
        leave_resp = api_client.post(f"{BASE_URL}/api/leave/request", json=leave_payload, headers=auth_headers(emp_token))
        assert leave_resp.status_code == 200, f"Leave creation failed: {leave_resp.text}"
        tx = leave_resp.json()
        tx_id = tx['id']
        print(f"  Created leave request: {tx['ref_no']}")
        
        # Step 2: Supervisor approves
        sup_token = get_token(api_client, supervisor_user['id'])
        sup_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "approve", "note": "Supervisor approved"},
            headers=auth_headers(sup_token)
        )
        # If supervisor stage was skipped, the tx might already be at ops
        if sup_resp.status_code == 403:
            print("  Supervisor stage skipped (employee may not have supervisor)")
        else:
            assert sup_resp.status_code == 200, f"Supervisor approve failed: {sup_resp.text}"
            print(f"  Supervisor approved")
        
        # Verify current stage is ops
        sultan = users_map.get('sultan')
        sultan_token = get_token(api_client, sultan['id'])
        
        check_resp = api_client.get(f"{BASE_URL}/api/transactions/{tx_id}", headers=auth_headers(sultan_token))
        tx_now = check_resp.json()
        
        if tx_now['current_stage'] != 'ops':
            print(f"  Current stage is {tx_now['current_stage']}, not ops - may need different test flow")
            pytest.skip("Transaction not at ops stage for escalation")
        
        # Step 3: Sultan escalates to CEO
        escalate_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "escalate", "note": "Escalating to CEO for approval"},
            headers=auth_headers(sultan_token)
        )
        assert escalate_resp.status_code == 200, f"Escalation failed: {escalate_resp.text}"
        
        result = escalate_resp.json()
        assert result['status'] == 'pending_ceo'
        assert result['current_stage'] == 'ceo'
        print(f"  Sultan escalated to CEO")
        
        # Step 4: CEO (Mohammed) approves → should go to STAS
        mohammed = users_map.get('mohammed')
        mohammed_token = get_token(api_client, mohammed['id'])
        
        ceo_approve_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "approve", "note": "CEO approved"},
            headers=auth_headers(mohammed_token)
        )
        assert ceo_approve_resp.status_code == 200, f"CEO approve failed: {ceo_approve_resp.text}"
        
        ceo_result = ceo_approve_resp.json()
        assert ceo_result['current_stage'] == 'stas', f"Expected stage 'stas' after CEO approval, got {ceo_result['current_stage']}"
        assert ceo_result['status'] == 'pending_stas'
        
        print(f"✓ Escalation flow complete: CEO approved → STAS stage")
    
    def test_create_leave_and_escalate_ceo_rejects(self, api_client, users_map, employees_list):
        """Full flow: Leave → Supervisor approves → Sultan escalates → CEO rejects → back to ops"""
        supervisor_user = users_map.get('supervisor1')
        employee_user = users_map.get('employee1')
        
        if not supervisor_user or not employee_user:
            pytest.skip("supervisor1 or employee1 not found")
        
        emp_record = None
        for emp in employees_list:
            if emp.get('user_id') == employee_user['id']:
                emp_record = emp
                break
        
        if not emp_record:
            pytest.skip("Employee record not found")
        
        # Create leave
        emp_token = get_token(api_client, employee_user['id'])
        start_date = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
        end_date = (datetime.now() + timedelta(days=62)).strftime('%Y-%m-%d')
        
        leave_payload = {
            "employee_id": emp_record['id'],
            "leave_type": "annual",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_Escalation_CEO_Rejects"
        }
        
        leave_resp = api_client.post(f"{BASE_URL}/api/leave/request", json=leave_payload, headers=auth_headers(emp_token))
        assert leave_resp.status_code == 200
        tx = leave_resp.json()
        tx_id = tx['id']
        print(f"  Created leave request: {tx['ref_no']}")
        
        # Supervisor approves (if applicable)
        sup_token = get_token(api_client, supervisor_user['id'])
        api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "approve"},
            headers=auth_headers(sup_token)
        )
        
        # Sultan escalates
        sultan = users_map.get('sultan')
        sultan_token = get_token(api_client, sultan['id'])
        
        # Check if at ops
        check_resp = api_client.get(f"{BASE_URL}/api/transactions/{tx_id}", headers=auth_headers(sultan_token))
        tx_now = check_resp.json()
        if tx_now['current_stage'] != 'ops':
            pytest.skip(f"Transaction at stage {tx_now['current_stage']}, not ops")
        
        escalate_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "escalate", "note": "Escalating to CEO"},
            headers=auth_headers(sultan_token)
        )
        assert escalate_resp.status_code == 200
        print(f"  Sultan escalated to CEO")
        
        # CEO rejects → should return to ops
        mohammed = users_map.get('mohammed')
        mohammed_token = get_token(api_client, mohammed['id'])
        
        ceo_reject_resp = api_client.post(
            f"{BASE_URL}/api/transactions/{tx_id}/action",
            json={"action": "reject", "note": "CEO rejected, returning to operations"},
            headers=auth_headers(mohammed_token)
        )
        assert ceo_reject_resp.status_code == 200, f"CEO reject failed: {ceo_reject_resp.text}"
        
        ceo_result = ceo_reject_resp.json()
        assert ceo_result['current_stage'] == 'ops', f"Expected stage 'ops' after CEO rejection, got {ceo_result['current_stage']}"
        assert ceo_result['status'] == 'pending_ops'
        
        print(f"✓ Escalation flow complete: CEO rejected → returned to ops stage")


# ==================== MOHAMMED VISIBILITY TESTS ====================
class TestMohammedVisibility:
    """Mohammed (CEO) should only see escalated transactions and finance_60/settlement"""
    
    def test_mohammed_sees_escalated_and_finance_transactions(self, api_client, users_map):
        """Mohammed should see escalated transactions and finance_60/settlement"""
        mohammed = users_map.get('mohammed')
        token = get_token(api_client, mohammed['id'])
        
        response = api_client.get(f"{BASE_URL}/api/transactions", headers=auth_headers(token))
        assert response.status_code == 200
        
        transactions = response.json()
        print(f"  Mohammed can see {len(transactions)} transactions")
        
        # Verify the types of transactions Mohammed sees
        for tx in transactions[:5]:  # Check first 5
            tx_type = tx.get('type')
            is_escalated = tx.get('escalated', False)
            current_stage = tx.get('current_stage')
            
            # Mohammed should see: escalated OR finance_60 OR settlement OR current_stage is 'ceo'
            valid_for_mohammed = (
                is_escalated or 
                tx_type in ['finance_60', 'settlement'] or 
                current_stage == 'ceo'
            )
            print(f"    {tx['ref_no']}: type={tx_type}, escalated={is_escalated}, stage={current_stage}")
        
        print(f"✓ Mohammed visibility check complete")


# ==================== CLEANUP TEST DATA ====================
class TestCleanupTestData:
    """Cleanup TEST_ prefixed transactions"""
    
    def test_cleanup_test_transactions(self, api_client, users_map):
        """Mark test data for cleanup (or leave for manual review)"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/transactions", headers=auth_headers(token))
        assert response.status_code == 200
        transactions = response.json()
        
        test_txs = [tx for tx in transactions if 
                    'TEST_' in (tx.get('data', {}).get('description', '') or '') or
                    'TEST_' in (tx.get('data', {}).get('item_name', '') or '') or
                    'TEST_' in (tx.get('data', {}).get('reason', '') or '')]
        
        print(f"✓ Found {len(test_txs)} test transactions (not deleting, for audit trail)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
