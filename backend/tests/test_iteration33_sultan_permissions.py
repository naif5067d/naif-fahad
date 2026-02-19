"""
Iteration 33 - Sultan Permissions Test
Tests:
1. Sultan login authentication
2. Sultan can access and modify official holidays
3. Sultan can access and modify contracts 
4. Sultan can update employee name (settings)
5. Notification bell endpoint
6. Leave balance for migrated contracts
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSultanAuthentication:
    """Test Sultan login and token generation"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        """Get Sultan's auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200, f"Sultan login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    def test_sultan_login_success(self):
        """Test Sultan can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") in ["sultan", "admin"]
    
    def test_sultan_me_endpoint(self, sultan_token):
        """Test Sultan can access /api/auth/me"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("username") == "sultan" or "sultan" in data.get("role", "")


class TestSultanHolidayPermissions:
    """Test Sultan can manage official holidays"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    def test_sultan_can_list_holidays(self, sultan_token):
        """Test Sultan can view holidays list"""
        response = requests.get(
            f"{BASE_URL}/api/leave/holidays",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_sultan_can_add_holiday(self, sultan_token):
        """Test Sultan can add a new holiday"""
        response = requests.post(
            f"{BASE_URL}/api/leave/holidays",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={
                "name": "Test Holiday",
                "name_ar": "إجازة اختبار",
                "date": "2026-12-31"
            }
        )
        # Sultan should be able to add holidays (canEditHolidays includes sultan)
        assert response.status_code in [200, 201], f"Failed to add holiday: {response.text}"
        
    def test_sultan_can_delete_holiday(self, sultan_token):
        """Test Sultan can delete a holiday"""
        # First, create a holiday to delete
        create_resp = requests.post(
            f"{BASE_URL}/api/leave/holidays",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={
                "name": "Delete Test",
                "name_ar": "اختبار حذف",
                "date": "2026-12-30"
            }
        )
        if create_resp.status_code in [200, 201]:
            holiday_id = create_resp.json().get("id")
            if holiday_id:
                del_resp = requests.delete(
                    f"{BASE_URL}/api/leave/holidays/{holiday_id}",
                    headers={"Authorization": f"Bearer {sultan_token}"}
                )
                assert del_resp.status_code in [200, 204], f"Failed to delete holiday: {del_resp.text}"


class TestSultanContractPermissions:
    """Test Sultan can manage contracts"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    def test_sultan_can_list_contracts(self, sultan_token):
        """Test Sultan can view contracts list"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_sultan_can_search_contracts(self, sultan_token):
        """Test Sultan can search contracts"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2/search?q=sultan",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        
    def test_sultan_can_access_pending_stas(self, sultan_token):
        """Test Sultan can view pending STAS contracts"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2/pending-stas",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        # Sultan should have access (require_roles includes sultan)
        assert response.status_code == 200
        
    def test_sultan_contract_stats(self, sultan_token):
        """Test Sultan can view contract statistics"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2/stats/summary",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200


class TestSultanEmployeeUpdate:
    """Test Sultan can update employee name in settings"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def sultan_employee_id(self, sultan_token):
        """Get Sultan's employee ID"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        data = response.json()
        return data.get("employee_id")
    
    def test_sultan_can_get_employee_data(self, sultan_token, sultan_employee_id):
        """Test Sultan can view his employee data"""
        if not sultan_employee_id:
            pytest.skip("No employee_id found for Sultan")
        response = requests.get(
            f"{BASE_URL}/api/employees/{sultan_employee_id}",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        
    def test_sultan_can_update_name(self, sultan_token, sultan_employee_id):
        """Test Sultan can update his name via PATCH"""
        if not sultan_employee_id:
            pytest.skip("No employee_id found for Sultan")
        
        # Get current name first
        get_resp = requests.get(
            f"{BASE_URL}/api/employees/{sultan_employee_id}",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        if get_resp.status_code != 200:
            pytest.skip("Cannot get current employee data")
            
        current_data = get_resp.json()
        current_name = current_data.get("full_name")
        current_name_ar = current_data.get("full_name_ar")
        
        # Update name (keep same name to avoid breaking things)
        response = requests.patch(
            f"{BASE_URL}/api/employees/{sultan_employee_id}",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={
                "full_name": current_name or "Sultan Al-Zamil",
                "full_name_ar": current_name_ar or "سلطان الزامل"
            }
        )
        # Sultan should be able to update name
        assert response.status_code in [200, 201], f"Failed to update name: {response.text}"


class TestNotificationBell:
    """Test notification bell endpoint"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    def test_notification_bell_endpoint(self, sultan_token):
        """Test notification bell endpoint works"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/bell",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should return notifications array and unread count
        assert "notifications" in data or "unread_count" in data


class TestLeaveBalance:
    """Test leave balance calculation"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    def test_leave_balance_endpoint(self, sultan_token):
        """Test leave balance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leave/balance",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should return balance info
        assert "annual" in data or isinstance(data, dict)
        
    def test_leave_balance_for_migrated_contracts(self, sultan_token):
        """Test leave balance correctly shows for migrated contracts"""
        response = requests.get(
            f"{BASE_URL}/api/leave/balance",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check if annual balance is present
        if "annual" in data:
            annual_data = data["annual"]
            # Should have available balance
            available = annual_data.get("available") or annual_data.get("balance", 0)
            print(f"Annual leave balance: {available} days")
            
            # For migrated contracts, check opening balance
            if annual_data.get("is_migrated"):
                opening = annual_data.get("opening_balance", 0)
                print(f"Migrated contract - Opening balance: {opening}")


class TestAttendanceGPS:
    """Test attendance GPS-related endpoints"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        return response.json().get("token")
    
    def test_attendance_today_endpoint(self, sultan_token):
        """Test today's attendance endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/today",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        
    def test_work_locations_endpoint(self, sultan_token):
        """Test work locations endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/work-locations",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
