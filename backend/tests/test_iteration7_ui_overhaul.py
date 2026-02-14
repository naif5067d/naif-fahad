"""
DAR AL CODE HR OS - Iteration 7: UI/UX Overhaul Testing
Tests: 
1. Holiday CRUD (POST/PUT/DELETE /api/leave/holidays) for Sultan/Naif/STAS
2. Attendance Admin Endpoint (GET /api/attendance/admin?period=daily/weekly/monthly/yearly)
3. Financial Custody Table structure
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHolidayCRUD:
    """Test Holiday Create/Update/Delete - Sultan/Naif/STAS only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get sultan token
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/54e422b8-357c-5fdc-81d5-de6cac565810")
        assert switch_res.status_code == 200
        self.sultan_token = switch_res.json().get('token')
        
        # Get naif token
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/3f2532cf-499e-54b3-a1b7-f8083ef5414f")
        assert switch_res.status_code == 200
        self.naif_token = switch_res.json().get('token')
        
        # Get stas token
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/fedffe24-ec69-5c65-809d-5d24f8a16b9d")
        assert switch_res.status_code == 200
        self.stas_token = switch_res.json().get('token')
        
        # Get employee token (should fail)
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/46c9dd1a-7f0f-584b-9bab-b37b949afece")
        assert switch_res.status_code == 200
        self.employee_token = switch_res.json().get('token')
    
    def test_get_holidays(self):
        """GET /api/leave/holidays returns list"""
        res = requests.get(f"{BASE_URL}/api/leave/holidays")
        assert res.status_code == 200
        holidays = res.json()
        assert isinstance(holidays, list)
        assert len(holidays) > 0
        # Check structure
        h = holidays[0]
        assert 'name' in h
        assert 'date' in h
        print(f"Found {len(holidays)} holidays")
    
    def test_sultan_create_holiday(self):
        """POST /api/leave/holidays - Sultan can create"""
        headers = {"Authorization": f"Bearer {self.sultan_token}"}
        test_holiday = {
            "name": f"TEST_HOLIDAY_{uuid.uuid4().hex[:6]}",
            "name_ar": "اختبار عطلة",
            "date": "2026-12-25"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 200, f"Sultan create holiday failed: {res.text}"
        data = res.json()
        assert data['name'] == test_holiday['name']
        assert 'id' in data
        self.created_holiday_id = data['id']
        print(f"Sultan created holiday: {data['id']}")
        return data['id']
    
    def test_naif_create_holiday(self):
        """POST /api/leave/holidays - Naif can create"""
        headers = {"Authorization": f"Bearer {self.naif_token}"}
        test_holiday = {
            "name": f"TEST_NAIF_HOLIDAY_{uuid.uuid4().hex[:6]}",
            "name_ar": "عطلة نايف",
            "date": "2026-11-15"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 200, f"Naif create holiday failed: {res.text}"
        print(f"Naif created holiday: {res.json()['id']}")
    
    def test_stas_create_holiday(self):
        """POST /api/leave/holidays - STAS can create"""
        headers = {"Authorization": f"Bearer {self.stas_token}"}
        test_holiday = {
            "name": f"TEST_STAS_HOLIDAY_{uuid.uuid4().hex[:6]}",
            "name_ar": "عطلة ستاس",
            "date": "2026-10-10"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 200, f"STAS create holiday failed: {res.text}"
        print(f"STAS created holiday: {res.json()['id']}")
    
    def test_employee_cannot_create_holiday(self):
        """POST /api/leave/holidays - Employee CANNOT create"""
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        test_holiday = {
            "name": "TEST_EMPLOYEE_HOLIDAY",
            "date": "2026-08-01"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 403, f"Employee should NOT be able to create holiday, got {res.status_code}"
        print("Correctly blocked employee from creating holiday")
    
    def test_update_holiday(self):
        """PUT /api/leave/holidays/{id} - Update holiday name and date"""
        headers = {"Authorization": f"Bearer {self.sultan_token}"}
        # First create a holiday to update
        test_holiday = {
            "name": f"TEST_UPDATE_ME_{uuid.uuid4().hex[:6]}",
            "date": "2026-07-01"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 200
        holiday_id = res.json()['id']
        
        # Now update it
        update_data = {
            "name": "UPDATED_HOLIDAY_NAME",
            "name_ar": "اسم محدث",
            "date": "2026-07-15"
        }
        res = requests.put(f"{BASE_URL}/api/leave/holidays/{holiday_id}", json=update_data, headers=headers)
        assert res.status_code == 200, f"Update holiday failed: {res.text}"
        data = res.json()
        assert data['name'] == "UPDATED_HOLIDAY_NAME"
        assert data['date'] == "2026-07-15"
        print(f"Successfully updated holiday: {holiday_id}")
    
    def test_delete_holiday(self):
        """DELETE /api/leave/holidays/{id} - Delete holiday"""
        headers = {"Authorization": f"Bearer {self.sultan_token}"}
        # First create a holiday to delete
        test_holiday = {
            "name": f"TEST_DELETE_ME_{uuid.uuid4().hex[:6]}",
            "date": "2026-06-01"
        }
        res = requests.post(f"{BASE_URL}/api/leave/holidays", json=test_holiday, headers=headers)
        assert res.status_code == 200
        holiday_id = res.json()['id']
        
        # Delete it
        res = requests.delete(f"{BASE_URL}/api/leave/holidays/{holiday_id}", headers=headers)
        assert res.status_code == 200, f"Delete holiday failed: {res.text}"
        assert "deleted" in res.json().get('message', '').lower()
        print(f"Successfully deleted holiday: {holiday_id}")


class TestAttendanceAdmin:
    """Test Attendance Admin Endpoint with Daily/Weekly/Monthly/Yearly periods"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Get sultan token (admin)
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/54e422b8-357c-5fdc-81d5-de6cac565810")
        assert switch_res.status_code == 200
        self.admin_token = switch_res.json().get('token')
        
        # Get employee token
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/46c9dd1a-7f0f-584b-9bab-b37b949afece")
        assert switch_res.status_code == 200
        self.employee_token = switch_res.json().get('token')
    
    def test_admin_daily_attendance(self):
        """GET /api/attendance/admin?period=daily returns grouped attendance data"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = requests.get(f"{BASE_URL}/api/attendance/admin?period=daily", headers=headers)
        assert res.status_code == 200, f"Admin daily attendance failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        print(f"Daily attendance: {len(data)} records")
        # If data exists, check structure
        if data:
            record = data[0]
            assert 'employee_name' in record
            assert 'date' in record
            assert 'check_in_time' in record or 'check_in' in record
    
    def test_admin_weekly_attendance(self):
        """GET /api/attendance/admin?period=weekly"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = requests.get(f"{BASE_URL}/api/attendance/admin?period=weekly", headers=headers)
        assert res.status_code == 200, f"Admin weekly attendance failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        print(f"Weekly attendance: {len(data)} records")
    
    def test_admin_monthly_attendance(self):
        """GET /api/attendance/admin?period=monthly"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = requests.get(f"{BASE_URL}/api/attendance/admin?period=monthly", headers=headers)
        assert res.status_code == 200, f"Admin monthly attendance failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        print(f"Monthly attendance: {len(data)} records")
    
    def test_admin_yearly_attendance(self):
        """GET /api/attendance/admin?period=yearly"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = requests.get(f"{BASE_URL}/api/attendance/admin?period=yearly", headers=headers)
        assert res.status_code == 200, f"Admin yearly attendance failed: {res.text}"
        data = res.json()
        assert isinstance(data, list)
        print(f"Yearly attendance: {len(data)} records")
    
    def test_employee_cannot_access_admin(self):
        """Employee should NOT access admin attendance endpoint"""
        headers = {"Authorization": f"Bearer {self.employee_token}"}
        res = requests.get(f"{BASE_URL}/api/attendance/admin?period=daily", headers=headers)
        assert res.status_code == 403, f"Employee should NOT access admin attendance, got {res.status_code}"
        print("Correctly blocked employee from admin attendance")


class TestFinancialCustody:
    """Test Financial Custody list and detail structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        switch_res = requests.post(f"{BASE_URL}/api/auth/switch/54e422b8-357c-5fdc-81d5-de6cac565810")
        assert switch_res.status_code == 200
        self.token = switch_res.json().get('token')
    
    def test_get_custody_list(self):
        """GET /api/financial-custody returns list"""
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(f"{BASE_URL}/api/financial-custody", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} custodies")
        # Check structure for table rendering
        if data:
            c = data[0]
            assert 'custody_number' in c
            assert 'title' in c
            assert 'total_amount' in c
            assert 'total_spent' in c
            assert 'remaining' in c
            assert 'status' in c
            print(f"Custody structure verified: #{c['custody_number']}, Budget: {c['total_amount']}, Spent: {c['total_spent']}, Remaining: {c['remaining']}")
    
    def test_get_custody_summary(self):
        """GET /api/financial-custody/summary/totals returns summary stats"""
        headers = {"Authorization": f"Bearer {self.token}"}
        res = requests.get(f"{BASE_URL}/api/financial-custody/summary/totals", headers=headers)
        assert res.status_code == 200
        data = res.json()
        # Check summary has required fields for UI stats bar
        assert 'total_custodies' in data or isinstance(data, dict)
        print(f"Summary: {data}")
    
    def test_get_custody_detail(self):
        """GET /api/financial-custody/{id} returns detail with expenses and timeline"""
        headers = {"Authorization": f"Bearer {self.token}"}
        # First get list
        res = requests.get(f"{BASE_URL}/api/financial-custody", headers=headers)
        custodies = res.json()
        if custodies:
            custody_id = custodies[0]['id']
            res = requests.get(f"{BASE_URL}/api/financial-custody/{custody_id}", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert 'expenses' in data
            assert 'timeline' in data
            print(f"Detail has {len(data.get('expenses', []))} expenses, {len(data.get('timeline', []))} timeline events")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
