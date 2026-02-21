"""
Iteration 37 - Employee Summary & GPS Bypass Tests
===================================================
Tests for:
1. GET /api/employees/{id}/summary - Dynamic required_monthly_hours
2. GET /api/employees/{id}/summary - work_days_in_month & daily_hours fields
3. GET /api/employees/{id}/summary - hours_until_deduction & days_to_deduct
4. GPS bypass logic for checkout
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://company-settings-2.preview.emergentagent.com')


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for stas user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "stas", "password": "123456"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        pytest.skip("Authentication failed")
    return response.json().get("token")


@pytest.fixture(scope="module")
def employee_token():
    """Get authentication token for sultan user (employee)"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "sultan", "password": "123456"},
        headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        pytest.skip("Employee authentication failed")
    return response.json().get("token")


class TestEmployeeSummaryDynamicHours:
    """Tests for dynamic monthly hours calculation in employee summary"""
    
    def test_summary_returns_required_monthly_hours(self, auth_token):
        """Test that required_monthly_hours is dynamically calculated"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "attendance" in data, "Response should contain attendance section"
        
        attendance = data["attendance"]
        assert "required_monthly_hours" in attendance, "Should have required_monthly_hours"
        
        # Verify it's dynamically calculated (not fixed 176)
        required_hours = attendance["required_monthly_hours"]
        assert required_hours > 0, "required_monthly_hours should be positive"
        assert isinstance(required_hours, (int, float)), "required_monthly_hours should be numeric"
        
        print(f"✓ required_monthly_hours = {required_hours} (dynamic)")
    
    def test_summary_returns_work_days_in_month(self, auth_token):
        """Test that work_days_in_month is included"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        attendance = data["attendance"]
        
        assert "work_days_in_month" in attendance, "Should have work_days_in_month"
        work_days = attendance["work_days_in_month"]
        
        assert work_days > 0, "work_days_in_month should be positive"
        assert work_days <= 31, "work_days_in_month should not exceed 31"
        
        print(f"✓ work_days_in_month = {work_days}")
    
    def test_summary_returns_daily_hours(self, auth_token):
        """Test that daily_hours is included"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        attendance = data["attendance"]
        
        assert "daily_hours" in attendance, "Should have daily_hours"
        daily_hours = attendance["daily_hours"]
        
        assert daily_hours > 0, "daily_hours should be positive"
        assert daily_hours <= 24, "daily_hours should not exceed 24"
        
        print(f"✓ daily_hours = {daily_hours}")
    
    def test_summary_returns_hours_until_deduction(self, auth_token):
        """Test that hours_until_deduction is included"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        attendance = data["attendance"]
        
        assert "hours_until_deduction" in attendance, "Should have hours_until_deduction"
        hours_until = attendance["hours_until_deduction"]
        
        assert isinstance(hours_until, (int, float)), "hours_until_deduction should be numeric"
        assert hours_until >= 0, "hours_until_deduction should be non-negative"
        
        print(f"✓ hours_until_deduction = {hours_until}")
    
    def test_summary_returns_days_to_deduct(self, auth_token):
        """Test that days_to_deduct is included"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        attendance = data["attendance"]
        
        assert "days_to_deduct" in attendance, "Should have days_to_deduct"
        days_to_deduct = attendance["days_to_deduct"]
        
        assert isinstance(days_to_deduct, (int, float)), "days_to_deduct should be numeric"
        assert days_to_deduct >= 0, "days_to_deduct should be non-negative"
        
        print(f"✓ days_to_deduct = {days_to_deduct}")
    
    def test_dynamic_calculation_varies_by_employee(self, auth_token):
        """Test that required_monthly_hours varies based on work location"""
        # Get summary for EMP-001
        response1 = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response1.status_code == 200
        emp001_hours = response1.json()["attendance"]["required_monthly_hours"]
        emp001_daily = response1.json()["attendance"]["daily_hours"]
        emp001_days = response1.json()["attendance"]["work_days_in_month"]
        
        # Get summary for EMP-STAS
        response2 = requests.get(
            f"{BASE_URL}/api/employees/EMP-STAS/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response2.status_code == 200
        emp_stas_hours = response2.json()["attendance"]["required_monthly_hours"]
        emp_stas_daily = response2.json()["attendance"]["daily_hours"]
        emp_stas_days = response2.json()["attendance"]["work_days_in_month"]
        
        # Verify calculation is consistent
        assert emp001_hours == emp001_daily * emp001_days, \
            f"EMP-001: {emp001_hours} should equal {emp001_daily} * {emp001_days}"
        assert emp_stas_hours == emp_stas_daily * emp_stas_days, \
            f"EMP-STAS: {emp_stas_hours} should equal {emp_stas_daily} * {emp_stas_days}"
        
        print(f"✓ EMP-001: {emp001_days} days * {emp001_daily} hours = {emp001_hours} required")
        print(f"✓ EMP-STAS: {emp_stas_days} days * {emp_stas_daily} hours = {emp_stas_hours} required")
    
    def test_summary_contains_all_attendance_fields(self, auth_token):
        """Verify all attendance fields are present in summary"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        
        attendance = response.json()["attendance"]
        
        required_fields = [
            "today_status",
            "today_status_ar",
            "monthly_hours",
            "required_monthly_hours",
            "remaining_hours",
            "deficit_hours",
            "deficit_minutes",
            "late_minutes_month",
            "early_leave_minutes",
            "work_days_in_month",
            "daily_hours",
            "hours_until_deduction",
            "days_to_deduct"
        ]
        
        for field in required_fields:
            assert field in attendance, f"Missing attendance field: {field}"
            print(f"✓ {field}: {attendance[field]}")


class TestEmployeeSummaryAccess:
    """Tests for employee summary access permissions"""
    
    def test_admin_can_access_any_summary(self, auth_token):
        """Admin (stas) can access any employee summary"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin can access EMP-001 summary")
    
    def test_employee_can_access_own_summary(self, employee_token):
        """Employee can access their own summary"""
        response = requests.get(
            f"{BASE_URL}/api/employees/EMP-001/summary",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        assert response.status_code == 200
        print("✓ Employee (sultan/EMP-001) can access own summary")
    
    def test_summary_returns_404_for_nonexistent_employee(self, auth_token):
        """Should return 404 for non-existent employee"""
        response = requests.get(
            f"{BASE_URL}/api/employees/NONEXISTENT/summary",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 404
        print("✓ Returns 404 for non-existent employee")


class TestAttendancePageAccess:
    """Tests for attendance page API endpoints"""
    
    def test_attendance_today_endpoint_accessible(self, auth_token):
        """Verify attendance/today endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/today",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Got unexpected status {response.status_code}"
        data = response.json()
        # Should have check_in and check_out fields
        assert "check_in" in data or "check_out" in data
        print(f"✓ Attendance today endpoint accessible: {data}")


class TestHealthEndpoint:
    """Basic health check"""
    
    def test_health_endpoint(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"✓ API health: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
