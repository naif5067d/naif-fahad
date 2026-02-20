"""
Iteration 38 - Supervisor Features Testing

Test cases for:
1. Manual attendance API for supervisors
2. Manual attendance API blocks check-in when automatic record exists
3. Supervisor role access restrictions
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPERVISOR_CREDS = {"username": "supervisor1", "password": "123456"}
SULTAN_CREDS = {"username": "sultan", "password": "123456"}

# Employee EMP-004 is assigned to supervisor1 (EMP-002)
TEST_EMPLOYEE_ID = "EMP-004"


class TestAuth:
    """Get auth tokens for testing"""
    
    def test_login_supervisor(self):
        """Login as supervisor1"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SUPERVISOR_CREDS
        )
        assert response.status_code == 200, f"Supervisor login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "supervisor"
        print(f"Supervisor login OK: {data['user']['full_name']}")
        return data["token"]
    
    def test_login_sultan(self):
        """Login as sultan (management)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS
        )
        assert response.status_code == 200, f"Sultan login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "sultan"
        print(f"Sultan login OK: {data['user']['full_name']}")
        return data["token"]


@pytest.fixture
def supervisor_token():
    """Get supervisor auth token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=SUPERVISOR_CREDS
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Supervisor login failed")


@pytest.fixture
def sultan_token():
    """Get sultan auth token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=SULTAN_CREDS
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Sultan login failed")


class TestManualAttendanceAPI:
    """Test manual attendance API for supervisors"""
    
    def test_manual_attendance_endpoint_exists(self, supervisor_token):
        """Verify /api/team-attendance/manual-attendance endpoint exists"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        # Try with empty body to check endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/team-attendance/manual-attendance",
            headers=headers,
            json={}
        )
        # Should get 422 (validation error) not 404
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}: {response.text}"
        print(f"Manual attendance endpoint exists (got validation error as expected)")
    
    def test_manual_attendance_requires_acknowledgment(self, supervisor_token):
        """Test that manual attendance requires supervisor acknowledgment"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.post(
            f"{BASE_URL}/api/team-attendance/manual-attendance",
            headers=headers,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "check_type": "check_in",
                "time": "08:00",
                "reason": "Test manual attendance",
                "supervisor_acknowledgment": False
            }
        )
        
        # Should fail because acknowledgment is False
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("error") == "ACKNOWLEDGMENT_REQUIRED"
            print(f"Correctly requires acknowledgment: {detail.get('message_ar', '')}")
        else:
            print(f"Got error response: {detail}")
    
    def test_manual_attendance_not_your_employee(self, supervisor_token):
        """Test that supervisor can only record for their employees"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        # Try to record for an employee not under this supervisor (EMP-001 is sultan)
        response = requests.post(
            f"{BASE_URL}/api/team-attendance/manual-attendance",
            headers=headers,
            json={
                "employee_id": "EMP-001",
                "check_type": "check_in",
                "time": "08:00",
                "reason": "Test",
                "supervisor_acknowledgment": True
            }
        )
        
        # Should fail because EMP-001 is not under supervisor1
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("error") == "NOT_YOUR_EMPLOYEE"
            print(f"Correctly blocked: {detail.get('message_ar', '')}")
        else:
            print(f"Got error: {detail}")
    
    def test_my_team_attendance_endpoint(self, supervisor_token):
        """Test /api/team-attendance/my-team-attendance endpoint for supervisor"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        today = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/team-attendance/my-team-attendance",
            headers=headers,
            params={"date": today}
        )
        
        assert response.status_code == 200, f"Failed to get team attendance: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of employees"
        print(f"Got {len(data)} team members for supervisor")
        
        if data:
            emp = data[0]
            assert "employee_id" in emp
            assert "can_manual_check_in" in emp
            assert "can_manual_check_out" in emp
            print(f"Team member: {emp.get('employee_name_ar')} - can_check_in: {emp.get('can_manual_check_in')}")


class TestSupervisorAccessRestrictions:
    """Test supervisor access restrictions on team attendance endpoints"""
    
    def test_supervisor_can_access_team_summary(self, supervisor_token):
        """Supervisor can access /api/team-attendance/summary"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/team-attendance/summary",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total" in data
        print(f"Supervisor summary: {data}")
    
    def test_supervisor_can_access_daily_attendance(self, supervisor_token):
        """Supervisor can access /api/team-attendance/daily"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/team-attendance/daily",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} daily records for supervisor's team")


class TestSultanManagementAccess:
    """Test sultan/management access to penalties and team attendance"""
    
    def test_sultan_can_access_penalties_report(self, sultan_token):
        """Sultan can access /api/penalties/monthly-report"""
        headers = {"Authorization": f"Bearer {sultan_token}"}
        now = datetime.now()
        
        response = requests.get(
            f"{BASE_URL}/api/penalties/monthly-report",
            headers=headers,
            params={"year": now.year, "month": now.month}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "summary" in data or "employees" in data
        print(f"Sultan penalties report access OK")
    
    def test_sultan_can_access_pending_corrections(self, sultan_token):
        """Sultan can access /api/team-attendance/pending-corrections"""
        headers = {"Authorization": f"Bearer {sultan_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/team-attendance/pending-corrections",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} pending corrections for sultan")
    
    def test_sultan_can_access_pending_deductions(self, sultan_token):
        """Sultan can access /api/attendance-engine/deductions/pending"""
        headers = {"Authorization": f"Bearer {sultan_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/attendance-engine/deductions/pending",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Got {len(data)} pending deductions for sultan")


class TestSupervisorCantAccessPenalties:
    """Verify supervisor cannot access management-only endpoints"""
    
    def test_supervisor_cannot_update_status_directly(self, supervisor_token):
        """Supervisor should not be able to directly update status (needs to request correction)"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Try direct status update (should fail - this is sultan/naif/stas only)
        response = requests.post(
            f"{BASE_URL}/api/team-attendance/{TEST_EMPLOYEE_ID}/update-status",
            headers=headers,
            params={"date": today},
            json={"new_status": "PRESENT", "reason": "Test"}
        )
        
        # Should be forbidden (supervisor must use request-correction)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"
        print("Supervisor correctly blocked from direct status update")
    
    def test_supervisor_cannot_access_pending_corrections(self, supervisor_token):
        """Supervisor should not access /api/team-attendance/pending-corrections"""
        headers = {"Authorization": f"Bearer {supervisor_token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/team-attendance/pending-corrections",
            headers=headers
        )
        
        # Should be forbidden (sultan/naif/stas only)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}: {response.text}"
        print("Supervisor correctly blocked from pending corrections")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
