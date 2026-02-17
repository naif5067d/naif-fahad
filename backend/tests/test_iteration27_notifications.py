"""
Iteration 27 Tests - Notifications & Employee Card Features
Tests for:
1. GET /api/notifications/expiring-contracts - Contract expiry alerts
2. GET /api/notifications/header-alerts - Header bell notifications 
3. POST /api/notifications/leave-carryover - Leave carryover
4. GET /api/employees/{id}/summary - Employee card summary
5. GET /api/employees/{id} - Employee profile
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAuth:
    """Authentication helper"""
    
    @staticmethod
    def get_auth_header(role='stas'):
        """Get auth header for specified role"""
        # Login as stas (admin)
        login_data = {
            "username": "stas",
            "password": "DarAlCode2026!"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            # Token can be in 'token' or 'access_token' field
            token = response.json().get('token') or response.json().get('access_token')
            return {"Authorization": f"Bearer {token}"}
        return {}


class TestExpiringContracts:
    """Tests for expiring contracts notification API"""
    
    def test_expiring_contracts_endpoint_exists(self):
        """Verify endpoint exists and returns proper structure"""
        headers = TestAuth.get_auth_header()
        response = requests.get(
            f"{BASE_URL}/api/notifications/expiring-contracts?days_ahead=90",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "employees" in data, "Response should have 'employees' key"
        assert "summary" in data, "Response should have 'summary' key"
        assert isinstance(data["employees"], list), "Employees should be a list"
        
        # Check summary structure
        summary = data["summary"]
        assert "total" in summary
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        print(f"Expiring contracts summary: {summary}")
    
    def test_expiring_contracts_employee_structure(self):
        """Verify employee data structure in expiring contracts"""
        headers = TestAuth.get_auth_header()
        response = requests.get(
            f"{BASE_URL}/api/notifications/expiring-contracts?days_ahead=365",  # Use longer range
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["employees"]) > 0:
            emp = data["employees"][0]
            # Check expected fields
            expected_fields = [
                "employee_id", "employee_name", "end_date", 
                "days_remaining", "leave_balance", "urgency"
            ]
            for field in expected_fields:
                assert field in emp, f"Employee should have '{field}' field"
            
            print(f"Sample expiring employee: {emp.get('employee_name')}, days_remaining: {emp.get('days_remaining')}")
        else:
            print("No expiring contracts found (expected - may not have test data)")
    
    def test_expiring_contracts_requires_auth(self):
        """Verify endpoint requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/expiring-contracts"
        )
        assert response.status_code == 401 or response.status_code == 403


class TestHeaderAlerts:
    """Tests for header alerts API (bell notifications)"""
    
    def test_header_alerts_endpoint_exists(self):
        """Verify header alerts endpoint exists"""
        headers = TestAuth.get_auth_header()
        response = requests.get(
            f"{BASE_URL}/api/notifications/header-alerts",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check response structure
        assert "alerts" in data, "Response should have 'alerts' key"
        assert "count" in data, "Response should have 'count' key"
        assert isinstance(data["alerts"], list), "Alerts should be a list"
        
        print(f"Header alerts count: {data['count']}")
    
    def test_header_alerts_structure(self):
        """Verify alert data structure"""
        headers = TestAuth.get_auth_header()
        response = requests.get(
            f"{BASE_URL}/api/notifications/header-alerts",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            # Check expected fields
            expected_fields = ["id", "type", "employee_name", "days_remaining", "message_en", "message_ar"]
            for field in expected_fields:
                assert field in alert, f"Alert should have '{field}' field"
            print(f"Sample alert: {alert.get('message_en')}")
        else:
            print("No header alerts found (no expiring contracts)")


class TestLeaveCarryover:
    """Tests for leave carryover API"""
    
    def test_leave_carryover_endpoint_exists(self):
        """Verify carryover endpoint exists"""
        headers = TestAuth.get_auth_header()
        
        # First get an employee
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        if len(employees) == 0:
            pytest.skip("No employees found for testing")
        
        # Test with invalid days (should fail gracefully)
        employee_id = employees[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/notifications/leave-carryover",
            headers=headers,
            json={
                "employee_id": employee_id,
                "days_to_carryover": 0,  # Invalid - should be positive
                "note": "Test carryover"
            }
        )
        
        # Should return 400 for invalid days
        assert response.status_code == 400, f"Expected 400 for invalid days, got {response.status_code}"
        print("Leave carryover validation working correctly")
    
    def test_leave_carryover_requires_auth(self):
        """Verify carryover requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/leave-carryover",
            json={"employee_id": "test", "days_to_carryover": 5}
        )
        assert response.status_code == 401 or response.status_code == 403


class TestEmployeeCard:
    """Tests for Employee Card / Profile features"""
    
    def test_employee_summary_endpoint(self):
        """Verify employee summary endpoint exists"""
        headers = TestAuth.get_auth_header()
        
        # Get employee list first
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["id"]
        
        # Get summary
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/summary",
            headers=headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check expected fields in summary
        expected_keys = ["contract", "leave_details", "service_info"]
        for key in expected_keys:
            assert key in data, f"Summary should have '{key}'"
        
        print(f"Employee summary loaded - leave balance: {data.get('leave_details', {}).get('balance', 'N/A')}")
    
    def test_employee_profile_endpoint(self):
        """Verify individual employee endpoint works"""
        headers = TestAuth.get_auth_header()
        
        # Get employee list
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["id"]
        
        # Get individual employee
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify employee data
        assert "id" in data
        assert "full_name" in data
        assert "employee_number" in data
        
        print(f"Employee profile loaded: {data.get('full_name')} ({data.get('employee_number')})")
    
    def test_employees_list_with_expiry_data(self):
        """Verify employees list works (for expiry badge display)"""
        headers = TestAuth.get_auth_header()
        
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        
        employees = response.json()
        assert isinstance(employees, list)
        
        print(f"Total employees: {len(employees)}")
        
        if len(employees) > 0:
            emp = employees[0]
            assert "id" in emp
            assert "full_name" in emp
            assert "is_active" in emp


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_full_notification_flow(self):
        """Test complete notification flow - login, check alerts, view expiring"""
        headers = TestAuth.get_auth_header()
        
        # 1. Get header alerts
        alerts_response = requests.get(
            f"{BASE_URL}/api/notifications/header-alerts",
            headers=headers
        )
        assert alerts_response.status_code == 200
        alerts = alerts_response.json()
        
        # 2. Get expiring contracts detail
        expiring_response = requests.get(
            f"{BASE_URL}/api/notifications/expiring-contracts?days_ahead=90",
            headers=headers
        )
        assert expiring_response.status_code == 200
        expiring = expiring_response.json()
        
        # 3. Counts should match (alerts = expiring contracts)
        assert alerts["count"] == expiring["summary"]["total"], \
            f"Alert count ({alerts['count']}) should match expiring total ({expiring['summary']['total']})"
        
        print(f"Integration test passed - {alerts['count']} expiring contracts")
    
    def test_employee_card_preview_data(self):
        """Test data needed for employee card preview"""
        headers = TestAuth.get_auth_header()
        
        # Get employees
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200
        employees = emp_response.json()
        
        if len(employees) == 0:
            pytest.skip("No employees")
        
        employee = employees[0]
        employee_id = employee["id"]
        
        # Get summary for preview card
        summary_response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/summary",
            headers=headers
        )
        assert summary_response.status_code == 200
        summary = summary_response.json()
        
        # Verify card preview data available
        leave_details = summary.get("leave_details", {})
        service_info = summary.get("service_info", {})
        
        # These should be present for the card preview
        assert "balance" in leave_details or leave_details == {}
        
        print(f"Card preview data: Leave={leave_details.get('balance', 0)}, Service={service_info.get('years_display', '0')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
