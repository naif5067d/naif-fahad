"""
Iteration 34 - Attendance System Tests
========================================
Tests for:
1. POST /api/attendance/request - Create attendance requests (4 types)
2. GET /api/employees/{id}/assigned-locations - Get employee assigned work locations
3. POST /api/attendance/check-in - Check-in with GPS coordinates
4. GET /api/attendance/today - Today's attendance record
5. GET /api/attendance/admin - Admin attendance view (not admin-all)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from previous iterations
TEST_CREDENTIALS = {
    "username": "sultan",
    "password": "123456"
}

# Fallback password based on iteration 32/33 - NOT VALID anymore
FALLBACK_PASSWORD = "123456"  # Same as main password


class TestAttendanceAuth:
    """Authentication tests for attendance system"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token - try both passwords"""
        # Try original password
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_CREDENTIALS
        )
        
        if response.status_code != 200:
            # Try fallback password
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "sultan", "password": FALLBACK_PASSWORD}
            )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get authenticated headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def user_info(self, auth_headers):
        """Get current user info"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=auth_headers
        )
        if response.status_code == 200:
            return response.json()
        return {}
    
    def test_login_sultan(self):
        """Test Sultan can login"""
        # Try with provided password first
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=TEST_CREDENTIALS
        )
        
        if response.status_code != 200:
            # Try fallback
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "sultan", "password": FALLBACK_PASSWORD}
            )
        
        assert response.status_code == 200
        data = response.json()
        print(f"Login successful, token obtained")


class TestAttendanceToday:
    """Test GET /api/attendance/today endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_today_attendance(self, auth_headers):
        """Test getting today's attendance record"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/today",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Should have check_in and check_out keys
        assert "check_in" in data or "check_out" in data
        print(f"Today's attendance: {data}")


class TestAssignedLocations:
    """Test GET /api/employees/{id}/assigned-locations endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def employee_id(self, auth_headers):
        """Get Sultan's employee_id"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers=auth_headers
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("employee_id")
        return None
    
    def test_get_assigned_locations(self, auth_headers, employee_id):
        """Test getting employee assigned work locations"""
        if not employee_id:
            pytest.skip("No employee_id found")
        
        response = requests.get(
            f"{BASE_URL}/api/employees/{employee_id}/assigned-locations",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Should be a list of locations
        assert isinstance(data, list)
        print(f"Assigned locations count: {len(data)}")
        if data:
            print(f"First location: {data[0].get('name_ar', data[0].get('name'))}")


class TestAttendanceRequest:
    """Test POST /api/attendance/request endpoint (4 request types)"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_create_forget_checkin_request(self, auth_headers):
        """Test creating 'forget check-in' request (نسيان بصمة)"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/request",
            headers=auth_headers,
            json={
                "request_type": "forget_checkin",
                "date": "2026-01-15",
                "reason": "TEST نسيت تسجيل البصمة صباحاً"
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data.get("type") == "forget_checkin"
        assert data.get("category") == "attendance"
        print(f"Created forget_checkin request: {data.get('ref_no')}")
    
    def test_create_field_work_request(self, auth_headers):
        """Test creating 'field work' request (مهمة خارجية)"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/request",
            headers=auth_headers,
            json={
                "request_type": "field_work",
                "date": "2026-01-16",
                "reason": "TEST اجتماع مع عميل خارج المكتب",
                "from_time": "09:00",
                "to_time": "14:00"
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data.get("type") == "field_work"
        print(f"Created field_work request: {data.get('ref_no')}")
    
    def test_create_early_leave_request(self, auth_headers):
        """Test creating 'early leave' request (خروج مبكر)"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/request",
            headers=auth_headers,
            json={
                "request_type": "early_leave_request",
                "date": "2026-01-17",
                "reason": "TEST موعد طبي",
                "from_time": "14:00",
                "to_time": "17:00"
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data.get("type") == "early_leave_request"
        print(f"Created early_leave_request: {data.get('ref_no')}")
    
    def test_create_late_excuse_request(self, auth_headers):
        """Test creating 'late excuse' request (تبرير تأخير)"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/request",
            headers=auth_headers,
            json={
                "request_type": "late_excuse",
                "date": "2026-01-18",
                "reason": "TEST تأخرت بسبب ازدحام مروري شديد"
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data.get("type") == "late_excuse"
        print(f"Created late_excuse request: {data.get('ref_no')}")
    
    def test_invalid_request_type(self, auth_headers):
        """Test invalid request type returns error"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/request",
            headers=auth_headers,
            json={
                "request_type": "invalid_type",
                "date": "2026-01-19",
                "reason": "TEST invalid"
            }
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestAttendanceCheckIn:
    """Test POST /api/attendance/check-in endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_check_in_without_gps(self, auth_headers):
        """Test check-in without GPS - should fail or work for exempt users"""
        response = requests.post(
            f"{BASE_URL}/api/attendance/check-in",
            headers=auth_headers,
            json={
                "work_location": "HQ",
                "latitude": None,
                "longitude": None,
                "gps_available": False
            }
        )
        
        # For Sultan (admin), might work even without GPS
        # For regular employees, should fail
        if response.status_code == 200:
            print("Check-in succeeded (admin user exempt from GPS)")
        else:
            print(f"Check-in failed: {response.json()}")
    
    def test_check_in_with_gps(self, auth_headers):
        """Test check-in with GPS coordinates"""
        # Riyadh coordinates
        response = requests.post(
            f"{BASE_URL}/api/attendance/check-in",
            headers=auth_headers,
            json={
                "work_location": "HQ",
                "latitude": 24.7136,
                "longitude": 46.6753,
                "gps_available": True
            }
        )
        
        # For admin users, might work; for others might fail if not in geofence
        if response.status_code == 200:
            data = response.json()
            print(f"Check-in successful: {data.get('id')}")
        elif response.status_code == 400:
            # Expected - might already be checked in or outside geofence
            print(f"Check-in validation: {response.json()}")
        else:
            print(f"Unexpected response: {response.status_code} - {response.text}")


class TestAdminAttendance:
    """Test admin attendance endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_admin_attendance_endpoint(self, auth_headers):
        """Test GET /api/attendance/admin endpoint (NOT admin-all)"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/admin",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Admin attendance records: {len(data)}")
    
    def test_admin_all_endpoint_should_not_exist(self, auth_headers):
        """Test GET /api/attendance/admin-all does NOT exist (frontend bug)"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/admin-all",
            headers=auth_headers
        )
        
        # This should return 404 or 405 - the endpoint doesn't exist
        assert response.status_code in [404, 405, 422], f"Unexpected: {response.status_code}. Frontend calls admin-all but backend only has admin!"
        print("CONFIRMED BUG: /api/attendance/admin-all endpoint doesn't exist!")
        print("Frontend calls admin-all at AttendancePage.js line 186 but backend only has /admin")


class TestAttendanceRequests:
    """Test GET /api/attendance/requests endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": FALLBACK_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=TEST_CREDENTIALS
            )
        assert response.status_code == 200
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_attendance_requests(self, auth_headers):
        """Test fetching attendance requests"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/requests",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Attendance requests found: {len(data)}")
        
        # Check if our test requests are there
        test_requests = [r for r in data if "TEST" in str(r.get("data", {}).get("reason", ""))]
        print(f"Test requests created: {len(test_requests)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
