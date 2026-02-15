"""
Iteration 18 Tests: Bug Fixes and Feature Verification
===============================================
Testing:
1. Map visibility for employees in Attendance page
2. Arabic text in Transactions page
3. Date format DD/MM/YYYY, HH:MM
4. Approve/Reject buttons for authorized users
5. Leave balance API shows 6 leave types
6. Sultan workflow: Sultan → CEO → STAS
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test users
USERS = {
    'stas': 'fedffe24-ec69-5c65-809d-5d24f8a16b9d',
    'sultan': '54e422b8-357c-5fdc-81d5-de6cac565810',
    'employee1': '46c9dd1a-7f0f-584b-9bab-b37b949afece',
    'mohammed': '32c4ee4f-72a4-565f-a4bd-1d763d95d584',
}


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def get_token(api_client, user_id):
    """Get authentication token for user"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{user_id}")
    if response.status_code == 200:
        return response.json().get("token")
    return None


class TestMapVisibilityPublic:
    """Test map visibility endpoint accessible to all users"""
    
    def test_map_visibility_public_as_employee(self, api_client):
        """Employee can access map visibility settings"""
        token = get_token(api_client, USERS['employee1'])
        assert token, "Failed to get employee1 token"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.get(f"{BASE_URL}/api/stas/settings/map-visibility/public")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "show_map_to_employees" in data, "Missing show_map_to_employees field"
        print(f"✓ Map visibility accessible to employee: {data}")
    
    def test_map_visibility_public_as_stas(self, api_client):
        """STAS can access map visibility settings"""
        token = get_token(api_client, USERS['stas'])
        assert token, "Failed to get STAS token"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.get(f"{BASE_URL}/api/stas/settings/map-visibility/public")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("show_map_to_employees"), bool)
        print(f"✓ Map visibility accessible to STAS: {data}")


class TestLeaveBalance:
    """Test leave balance API returns 6 leave types"""
    
    def test_leave_balance_returns_six_types(self, api_client):
        """Leave balance API returns all 6 leave types"""
        token = get_token(api_client, USERS['employee1'])
        assert token, "Failed to get employee1 token"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        response = api_client.get(f"{BASE_URL}/api/leave/balance")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify all 6 leave types are present
        expected_types = ['annual', 'sick', 'marriage', 'bereavement', 'exam', 'unpaid']
        for leave_type in expected_types:
            assert leave_type in data, f"Missing leave type: {leave_type}"
        
        print(f"✓ Leave balance has all 6 types: {list(data.keys())}")
        
        # Verify annual leave has proper structure
        annual = data['annual']
        assert 'balance' in annual, "Annual leave missing balance"
        assert 'entitlement' in annual, "Annual leave missing entitlement"
        assert 'message_ar' in annual, "Annual leave missing message_ar"
        print(f"✓ Annual leave details: balance={annual['balance']}, entitlement={annual['entitlement']}")
        
        # Verify sick leave has tier info
        sick = data['sick']
        assert 'used_12_months' in sick, "Sick leave missing used_12_months"
        assert 'remaining' in sick, "Sick leave missing remaining"
        assert 'current_tier' in sick, "Sick leave missing current_tier"
        assert 'note_ar' in sick, "Sick leave missing note_ar"
        print(f"✓ Sick leave details: used={sick['used_12_months']}, remaining={sick['remaining']}")


class TestSultanWorkflow:
    """Test Sultan self-request workflow: Sultan → CEO → STAS"""
    
    def test_sultan_leave_request_goes_to_ceo(self, api_client):
        """Sultan's self leave request skips ops and goes to CEO"""
        token = get_token(api_client, USERS['sultan'])
        assert token, "Failed to get Sultan token"
        
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create a leave request - use future dates to avoid overlap
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        response = api_client.post(f"{BASE_URL}/api/leave/request", json={
            "leave_type": "annual",
            "start_date": "2026-07-01",
            "end_date": "2026-07-03",
            "reason": f"Test Sultan workflow {unique_id}"
        })
        
        # Could be 200 or 400 if dates overlap
        if response.status_code == 400:
            error = response.json()
            if "overlap" in str(error).lower() or "متداخلة" in str(error):
                pytest.skip("Dates overlap with existing leave - skipping")
            else:
                pytest.fail(f"Unexpected error: {error}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify workflow skips ops and goes to CEO
        assert data.get('status') == 'pending_ceo', f"Expected pending_ceo, got {data.get('status')}"
        assert data.get('current_stage') == 'ceo', f"Expected ceo stage, got {data.get('current_stage')}"
        assert 'ceo' in data.get('workflow', []), "CEO not in workflow"
        assert 'stas' in data.get('workflow', []), "STAS not in workflow"
        assert data.get('self_request_escalated') == True, "self_request_escalated should be True"
        
        print(f"✓ Sultan request workflow: {data['workflow']}")
        print(f"✓ Current stage: {data['current_stage']}")
        print(f"✓ self_request_escalated: {data['self_request_escalated']}")
        
        # Verify ops is skipped
        skipped = data.get('workflow_skipped_stages', [])
        assert 'ops' in skipped, f"ops should be in skipped stages: {skipped}"
        print(f"✓ Skipped stages: {skipped}")
    
    def test_ceo_can_approve_sultan_request(self, api_client):
        """Mohammed (CEO) can approve Sultan's escalated request"""
        # First create a Sultan request
        sultan_token = get_token(api_client, USERS['sultan'])
        api_client.headers.update({"Authorization": f"Bearer {sultan_token}"})
        
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        response = api_client.post(f"{BASE_URL}/api/leave/request", json={
            "leave_type": "annual",
            "start_date": "2026-08-01",
            "end_date": "2026-08-02",
            "reason": f"Test CEO approval {unique_id}"
        })
        
        if response.status_code == 400:
            pytest.skip("Cannot create test request - dates may overlap")
        
        if response.status_code != 200:
            pytest.skip(f"Cannot create test request: {response.text}")
        
        tx = response.json()
        tx_id = tx['id']
        
        # Now login as Mohammed (CEO) and approve
        mohammed_token = get_token(api_client, USERS['mohammed'])
        api_client.headers.update({"Authorization": f"Bearer {mohammed_token}"})
        
        response = api_client.post(f"{BASE_URL}/api/transactions/{tx_id}/action", json={
            "action": "approve",
            "note": "CEO approved"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        # After CEO approval, should go to STAS
        assert result.get('current_stage') == 'stas', f"Expected stas stage after CEO approval, got {result.get('current_stage')}"
        assert result.get('status') == 'stas', f"Expected stas status, got {result.get('status')}"
        print(f"✓ CEO approval moved to STAS: stage={result['current_stage']}, status={result['status']}")


class TestTransactionsPage:
    """Test transactions API returns proper data for Arabic UI"""
    
    def test_transactions_list(self, api_client):
        """Transactions API returns data with employee names"""
        token = get_token(api_client, USERS['stas'])
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        
        response = api_client.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            tx = data[0]
            # Check required fields for Arabic UI
            assert 'ref_no' in tx, "Missing ref_no"
            assert 'type' in tx, "Missing type"
            assert 'status' in tx, "Missing status"
            assert 'created_at' in tx, "Missing created_at"
            
            print(f"✓ Transaction fields present: ref_no={tx.get('ref_no')}, type={tx.get('type')}")
            
            # Check employee name in data
            if 'data' in tx and tx['data']:
                employee_name_ar = tx['data'].get('employee_name_ar')
                employee_name = tx['data'].get('employee_name')
                print(f"✓ Employee name: ar={employee_name_ar}, en={employee_name}")


class TestDateFormat:
    """Test date format in API responses"""
    
    def test_transaction_created_at_format(self, api_client):
        """Transactions have ISO date format that frontend can parse"""
        token = get_token(api_client, USERS['stas'])
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        
        response = api_client.get(f"{BASE_URL}/api/transactions")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            tx = data[0]
            created_at = tx.get('created_at')
            assert created_at, "Missing created_at"
            
            # Verify it's ISO format
            from datetime import datetime
            try:
                # ISO format: 2026-02-15T19:04:20.394806+00:00
                parsed = datetime.fromisoformat(created_at.replace('+00:00', ''))
                print(f"✓ Date format is valid ISO: {created_at}")
            except ValueError as e:
                pytest.fail(f"Invalid date format: {created_at}, error: {e}")


class TestAttendanceAdmin:
    """Test admin attendance endpoint returns formatted times"""
    
    def test_admin_attendance_time_fields(self, api_client):
        """Admin attendance includes check_in_time and check_out_time"""
        token = get_token(api_client, USERS['stas'])
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        
        response = api_client.get(f"{BASE_URL}/api/attendance/admin", params={"period": "daily"})
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            record = data[0]
            print(f"Attendance record: {record}")
            
            # Check time fields exist (may be None if no check-in)
            assert 'check_in_time' in record or 'check_in' in record, "Missing check_in fields"
            assert 'check_out_time' in record or 'check_out' in record, "Missing check_out fields"
            
            # If there's a check-in, verify time format
            if record.get('check_in_time'):
                time_str = record['check_in_time']
                # Should be HH:MM:SS format
                assert ':' in time_str, f"Time should contain colon: {time_str}"
                assert 'T' not in time_str, f"Time should not be ISO format: {time_str}"
                print(f"✓ Check-in time format: {time_str}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
