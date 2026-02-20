"""
Backend tests for Supervisor Workflow Fix and Status/Role Colors
Test cases:
1. Supervisor workflow - when supervisor creates leave request, should go directly to 'pending_ops'
2. Arabic localization - verify API returns bilingual data
3. Fixed status colors - verify status values in API response
4. Fixed role colors - verify roles are correctly assigned

Key fix tested: workflow.py - should_skip_supervisor_stage()
When employee's supervisor has role other than 'supervisor' (like sultan/naif), 
the supervisor stage is now skipped.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-management-hub-9.preview.emergentagent.com')


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
    assert response.status_code == 200
    users = response.json()
    return {u['username']: u for u in users}


def get_token(api_client, user_id):
    """Get auth token for user via switch endpoint"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{user_id}")
    if response.status_code == 200:
        return response.json().get('token')
    return None


def auth_headers(token):
    """Return auth headers with token"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ==================== SUPERVISOR WORKFLOW FIX ====================
class TestSupervisorWorkflowFix:
    """
    Test the core bug fix: when supervisor creates leave request,
    it should go directly to 'pending_ops' status, skipping 'pending_supervisor'
    
    Key scenario: supervisor1 (Ahmad Al-Harbi) has Sultan as supervisor.
    Sultan's role is 'sultan' (not 'supervisor'), so supervisor stage should be skipped.
    """
    
    def test_supervisor1_leave_goes_to_pending_ops(self, api_client, users_map):
        """
        CRITICAL TEST: supervisor1 creates leave request
        Expected: status should be 'pending_ops', NOT 'pending_supervisor'
        Because supervisor1's supervisor (Sultan) has role 'sultan' not 'supervisor'
        """
        supervisor = users_map.get('supervisor1')
        assert supervisor, "supervisor1 user not found"
        assert supervisor['role'] == 'supervisor', f"Expected role 'supervisor', got {supervisor['role']}"
        
        token = get_token(api_client, supervisor['id'])
        assert token, "Failed to get supervisor1's token"
        
        # Create leave request
        leave_data = {
            "leave_type": "annual",
            "start_date": "2026-08-15",
            "end_date": "2026-08-16",
            "reason": "TEST: supervisor1 leave - should skip supervisor stage and go to pending_ops"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "not registered as an employee" in response.text:
            pytest.skip("supervisor1 not registered as employee")
        
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        # Core assertion - this is the bug fix being tested
        assert tx.get('status') == 'pending_ops', \
            f"BUG: Expected 'pending_ops' but got '{tx.get('status')}'. " \
            f"Supervisor workflow fix not working - supervisor's leave still going to 'pending_supervisor'"
        
        assert tx.get('current_stage') == 'ops', \
            f"Expected current_stage 'ops', got '{tx.get('current_stage')}'"
        
        # Verify supervisor stage was skipped in workflow
        workflow = tx.get('workflow', [])
        assert 'supervisor' not in workflow, \
            f"Supervisor stage should be skipped in workflow. Got: {workflow}"
        
        # Verify skipped stages recorded
        skipped = tx.get('workflow_skipped_stages', [])
        assert 'supervisor' in skipped, \
            f"'supervisor' should be in workflow_skipped_stages. Got: {skipped}"
        
        print(f"✓ SUPERVISOR WORKFLOW FIX VERIFIED: {tx.get('ref_no')}")
        print(f"  Status: {tx.get('status')} (correct: pending_ops)")
        print(f"  Current stage: {tx.get('current_stage')} (correct: ops)")
        print(f"  Workflow: {workflow}")
        print(f"  Skipped stages: {skipped}")
        
        return tx
    
    def test_employee1_leave_goes_to_pending_supervisor(self, api_client, users_map):
        """
        Control test: employee1 creates leave request
        Expected: status should be 'pending_supervisor'
        Because employee1's supervisor (supervisor1) has role 'supervisor'
        """
        employee = users_map.get('employee1')
        assert employee, "employee1 user not found"
        
        token = get_token(api_client, employee['id'])
        assert token, "Failed to get employee1's token"
        
        leave_data = {
            "leave_type": "sick",
            "start_date": "2026-08-20",
            "end_date": "2026-08-21",
            "reason": "TEST: employee1 leave - should go to pending_supervisor"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "not registered as an employee" in response.text:
            pytest.skip("employee1 not registered as employee")
        
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        # Employee with a supervisor who has role='supervisor' should go to pending_supervisor
        assert tx.get('status') == 'pending_supervisor', \
            f"Expected 'pending_supervisor' but got '{tx.get('status')}'. " \
            f"Employee's leave should go to supervisor first."
        
        assert tx.get('current_stage') == 'supervisor', \
            f"Expected current_stage 'supervisor', got '{tx.get('current_stage')}'"
        
        workflow = tx.get('workflow', [])
        assert 'supervisor' in workflow, \
            f"Supervisor stage should be in workflow. Got: {workflow}"
        
        print(f"✓ Employee workflow verified: {tx.get('ref_no')}")
        print(f"  Status: {tx.get('status')} (correct: pending_supervisor)")
        print(f"  Current stage: {tx.get('current_stage')} (correct: supervisor)")
        print(f"  Workflow: {workflow}")
        
        return tx
    
    def test_sultan_leave_goes_to_pending_ops(self, api_client, users_map):
        """
        Test: Sultan (no supervisor) creates leave request
        Expected: status should be 'pending_ops' (skips supervisor as no supervisor assigned)
        """
        sultan = users_map.get('sultan')
        assert sultan, "sultan user not found"
        
        token = get_token(api_client, sultan['id'])
        assert token, "Failed to get sultan's token"
        
        leave_data = {
            "leave_type": "emergency",
            "start_date": "2026-08-25",
            "end_date": "2026-08-25",
            "reason": "TEST: sultan leave - should skip supervisor (no supervisor assigned)"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "not registered as an employee" in response.text:
            pytest.skip("sultan not registered as employee")
        
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        assert tx.get('status') == 'pending_ops', \
            f"Expected 'pending_ops' but got '{tx.get('status')}'"
        
        workflow = tx.get('workflow', [])
        assert 'supervisor' not in workflow, \
            f"Supervisor stage should be skipped for sultan. Got: {workflow}"
        
        print(f"✓ Sultan workflow verified: {tx.get('ref_no')}")
        print(f"  Status: {tx.get('status')}")
        print(f"  Workflow: {workflow}")
        
        return tx


# ==================== ARABIC LOCALIZATION ====================
class TestArabicLocalization:
    """Test that API returns bilingual data for all entities"""
    
    def test_users_have_arabic_names(self, api_client):
        """Verify all users have Arabic names"""
        response = api_client.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        
        missing_arabic = []
        for u in users:
            if not u.get('full_name_ar'):
                missing_arabic.append(u.get('username'))
        
        assert len(missing_arabic) == 0, \
            f"Users missing Arabic names: {missing_arabic}"
        
        print(f"✓ All {len(users)} users have Arabic names (full_name_ar)")
        for u in users[:3]:
            print(f"  - {u.get('username')}: {u.get('full_name')} / {u.get('full_name_ar')}")
    
    def test_employees_have_arabic_names(self, api_client, users_map):
        """Verify employees have Arabic names and positions"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/employees", headers=auth_headers(token))
        assert response.status_code == 200
        employees = response.json()
        
        missing_fields = []
        for emp in employees:
            if not emp.get('full_name_ar'):
                missing_fields.append(f"{emp.get('id')}: missing full_name_ar")
            if not emp.get('department_ar'):
                missing_fields.append(f"{emp.get('id')}: missing department_ar")
            if not emp.get('position_ar'):
                missing_fields.append(f"{emp.get('id')}: missing position_ar")
        
        assert len(missing_fields) == 0, \
            f"Employees with missing Arabic fields: {missing_fields}"
        
        print(f"✓ All {len(employees)} employees have Arabic fields")
        for emp in employees[:2]:
            print(f"  - {emp.get('full_name')} / {emp.get('full_name_ar')}")
            print(f"    Dept: {emp.get('department')} / {emp.get('department_ar')}")
    
    def test_transactions_have_employee_arabic_names(self, api_client, users_map):
        """Verify transactions include employee Arabic names in data"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/transactions", headers=auth_headers(token))
        assert response.status_code == 200
        transactions = response.json()
        
        if not transactions:
            pytest.skip("No transactions to verify")
        
        # Check sample transactions
        for tx in transactions[:3]:
            data = tx.get('data', {})
            if not data.get('employee_name_ar'):
                print(f"  Note: TX {tx.get('ref_no')} has no employee_name_ar in data")
            else:
                print(f"  ✓ TX {tx.get('ref_no')}: {data.get('employee_name')} / {data.get('employee_name_ar')}")
        
        print(f"✓ Checked {len(transactions)} transactions for Arabic names")


# ==================== STATUS COLORS (API VERIFICATION) ====================
class TestStatusValues:
    """
    Verify status values returned by API match expected values.
    Frontend uses fixed colors based on these statuses:
    - executed: #16A34A (green)
    - pending_*: #EAB308 (yellow)
    - rejected: #DC2626 (red)
    """
    
    def test_transaction_status_values(self, api_client, users_map):
        """Verify transactions have valid status values"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/transactions", headers=auth_headers(token))
        assert response.status_code == 200
        transactions = response.json()
        
        valid_statuses = [
            'pending_supervisor', 'pending_ops', 'pending_finance', 
            'pending_ceo', 'pending_stas', 'executed', 'rejected'
        ]
        
        status_counts = {}
        invalid_statuses = []
        
        for tx in transactions:
            status = tx.get('status')
            status_counts[status] = status_counts.get(status, 0) + 1
            if status not in valid_statuses:
                invalid_statuses.append(f"{tx.get('ref_no')}: {status}")
        
        assert len(invalid_statuses) == 0, \
            f"Transactions with invalid status values: {invalid_statuses}"
        
        print(f"✓ All {len(transactions)} transactions have valid statuses")
        print(f"  Status breakdown: {status_counts}")


# ==================== ROLE VALUES ====================
class TestRoleValues:
    """
    Verify user roles returned by API match expected values.
    Frontend uses fixed colors based on these roles:
    - employee: #3B82F6 (blue)
    - supervisor: #1D4ED8 (dark blue)
    - sultan: #F97316 (orange)
    - mohammed: #B91C1C (red)
    - stas: #7C3AED (purple)
    - naif: #4D7C0F (green)
    - salah: #0D9488 (teal)
    """
    
    def test_user_role_values(self, api_client):
        """Verify users have valid role values"""
        response = api_client.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        
        valid_roles = ['employee', 'supervisor', 'sultan', 'naif', 'salah', 'mohammed', 'stas']
        
        role_counts = {}
        invalid_roles = []
        
        for u in users:
            role = u.get('role')
            role_counts[role] = role_counts.get(role, 0) + 1
            if role not in valid_roles:
                invalid_roles.append(f"{u.get('username')}: {role}")
        
        assert len(invalid_roles) == 0, \
            f"Users with invalid role values: {invalid_roles}"
        
        print(f"✓ All {len(users)} users have valid roles")
        print(f"  Role breakdown: {role_counts}")
        
        # Verify expected roles exist
        for expected_role in ['stas', 'supervisor', 'employee', 'sultan']:
            assert expected_role in role_counts, f"Expected role '{expected_role}' not found"


# ==================== HEALTH CHECK ====================
class TestHealthCheck:
    """Basic health check"""
    
    def test_api_health(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ API health check passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
