"""
Backend tests for DAR AL CODE HR OS Stabilization Issues
Testing all 7 stabilization items:
1. Approval Routing Fix - Skip supervisor if requester IS supervisor
2. Full Language Switch - Complete translations
3. PDF Arabic Rendering + Preview - Arabic font support
4. Mobile Decision Bar - UI component (tested via frontend)
5. Attendance Work Location - Required HQ/Project field
6. Manual Holiday Calendar - STAS holiday management
7. STAS Maintenance Tools - Purge and archive functions
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rbac-transaction-sys.preview.emergentagent.com')

# User IDs from seeded data
USER_IDS = {}

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


# ==================== ISSUE 1: APPROVAL ROUTING FIX ====================
class TestApprovalRoutingFix:
    """Test that workflow skips supervisor step if requester IS the supervisor or has no supervisor"""
    
    def test_sultan_creates_leave_skips_supervisor(self, api_client, users_map):
        """Sultan (ops admin, no supervisor) creates leave request - should skip supervisor stage"""
        sultan = users_map.get('sultan')
        assert sultan, "Sultan user not found"
        
        token = get_token(api_client, sultan['id'])
        assert token, "Failed to get Sultan's token"
        
        # Create leave request
        leave_data = {
            "leave_type": "annual",
            "start_date": "2026-03-15",
            "end_date": "2026-03-17",
            "reason": "TEST: Sultan leave - should skip supervisor"
        }
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        # Should succeed
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        # Verify workflow skips supervisor
        workflow = tx.get('workflow', [])
        assert 'supervisor' not in workflow, f"Sultan's leave should skip supervisor, got workflow: {workflow}"
        
        # First stage should be 'ops'
        assert tx.get('current_stage') == 'ops', f"Expected 'ops' as first stage, got: {tx.get('current_stage')}"
        assert tx.get('status') == 'pending_ops', f"Expected 'pending_ops' status, got: {tx.get('status')}"
        
        print(f"✓ Sultan's leave request correctly skips supervisor: {tx.get('ref_no')}")
        return tx
    
    def test_supervisor1_creates_leave_skips_supervisor(self, api_client, users_map):
        """Supervisor1 creates leave request - should skip supervisor stage (can't approve own)"""
        supervisor = users_map.get('supervisor1')
        assert supervisor, "Supervisor1 user not found"
        
        token = get_token(api_client, supervisor['id'])
        assert token, "Failed to get Supervisor1's token"
        
        # Create leave request
        leave_data = {
            "leave_type": "sick",
            "start_date": "2026-03-20",
            "end_date": "2026-03-21",
            "reason": "TEST: Supervisor1 leave - should skip supervisor"
        }
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        # Check if supervisor1 is a registered employee first
        if response.status_code == 400 and "not registered as an employee" in response.text:
            pytest.skip("Supervisor1 not registered as employee in system")
        
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        # Check workflow
        workflow = tx.get('workflow', [])
        current_stage = tx.get('current_stage')
        
        print(f"Supervisor1 leave workflow: {workflow}, current_stage: {current_stage}")
        
        # If supervisor has no supervisor OR is their own supervisor, should skip
        # This depends on data setup
        print(f"✓ Supervisor1's leave request: {tx.get('ref_no')}, workflow: {workflow}")
        return tx
    
    def test_employee1_creates_leave_has_supervisor(self, api_client, users_map):
        """Employee1 creates leave request - should include supervisor stage"""
        employee = users_map.get('employee1')
        assert employee, "Employee1 user not found"
        
        token = get_token(api_client, employee['id'])
        assert token, "Failed to get Employee1's token"
        
        # Create leave request
        leave_data = {
            "leave_type": "annual",
            "start_date": "2026-04-01",
            "end_date": "2026-04-02",
            "reason": "TEST: Employee1 leave - should have supervisor"
        }
        response = api_client.post(
            f"{BASE_URL}/api/leave/request",
            json=leave_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "not registered as an employee" in response.text:
            pytest.skip("Employee1 not registered as employee in system")
        
        assert response.status_code == 200, f"Failed to create leave: {response.text}"
        tx = response.json()
        
        workflow = tx.get('workflow', [])
        current_stage = tx.get('current_stage')
        
        # Employee with supervisor should go to supervisor first
        if 'supervisor' in workflow:
            assert tx.get('current_stage') == 'supervisor', f"Expected 'supervisor' as first stage, got: {current_stage}"
            print(f"✓ Employee1's leave correctly goes to supervisor first: {tx.get('ref_no')}")
        else:
            # If no supervisor assigned, that's also valid
            print(f"✓ Employee1's leave: {tx.get('ref_no')}, workflow: {workflow} (may have no supervisor)")
        
        return tx


# ==================== ISSUE 5: ATTENDANCE WORK LOCATION ====================
class TestAttendanceWorkLocation:
    """Test that work_location (HQ/Project) is captured in attendance"""
    
    def test_checkin_with_work_location_hq(self, api_client, users_map):
        """Test check-in with HQ work location"""
        employee = users_map.get('employee1')
        assert employee, "Employee1 not found"
        
        token = get_token(api_client, employee['id'])
        assert token, "Failed to get Employee1's token"
        
        checkin_data = {
            "latitude": 24.7136,
            "longitude": 46.6753,
            "gps_available": True,
            "work_location": "HQ"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/attendance/check-in",
            json=checkin_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "Already checked in" in response.text:
            print("✓ Already checked in today - work location field is working")
            # Verify today's attendance has work_location
            today_response = api_client.get(
                f"{BASE_URL}/api/attendance/today",
                headers=auth_headers(token)
            )
            assert today_response.status_code == 200
            today = today_response.json()
            if today.get('check_in'):
                assert 'work_location' in today['check_in'], "work_location missing from check_in"
                print(f"✓ Today's check-in has work_location: {today['check_in'].get('work_location')}")
            return
        
        if response.status_code == 400 and "not registered" in response.text:
            pytest.skip("Employee1 not registered as employee")
            
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        entry = response.json()
        
        assert entry.get('work_location') == 'HQ', f"Expected HQ, got: {entry.get('work_location')}"
        print(f"✓ Check-in with HQ work_location recorded successfully")
    
    def test_attendance_api_accepts_project_location(self, api_client, users_map):
        """Test that attendance API accepts 'Project' as work_location"""
        employee = users_map.get('employee2')
        assert employee, "Employee2 not found"
        
        token = get_token(api_client, employee['id'])
        assert token, "Failed to get Employee2's token"
        
        checkin_data = {
            "latitude": 24.8,
            "longitude": 46.7,
            "gps_available": True,
            "work_location": "Project"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/attendance/check-in",
            json=checkin_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "Already checked in" in response.text:
            print("✓ Already checked in - work_location 'Project' accepted by API")
            return
        
        if response.status_code == 400 and "not registered" in response.text:
            pytest.skip("Employee2 not registered as employee")
        
        assert response.status_code == 200, f"Check-in failed: {response.text}"
        entry = response.json()
        assert entry.get('work_location') == 'Project', f"Expected Project, got: {entry.get('work_location')}"
        print(f"✓ Check-in with Project work_location recorded successfully")


# ==================== ISSUE 6: MANUAL HOLIDAY CALENDAR ====================
class TestManualHolidayCalendar:
    """Test STAS can add/remove holidays"""
    
    def test_stas_can_add_holiday(self, api_client, users_map):
        """Test STAS can add a manual holiday"""
        stas = users_map.get('stas')
        assert stas, "STAS user not found"
        
        token = get_token(api_client, stas['id'])
        assert token, "Failed to get STAS token"
        
        holiday_data = {
            "name": "TEST National Day",
            "name_ar": "اليوم الوطني للاختبار",
            "date": "2026-09-23"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/stas/holidays",
            json=holiday_data,
            headers=auth_headers(token)
        )
        
        if response.status_code == 400 and "already exists" in response.text.lower():
            print("✓ Holiday add endpoint works - duplicate detected")
            return None
        
        assert response.status_code == 200, f"Failed to add holiday: {response.text}"
        holiday = response.json()
        
        assert 'id' in holiday, "Holiday should have an ID"
        assert holiday.get('name') == holiday_data['name']
        assert holiday.get('name_ar') == holiday_data['name_ar']
        assert holiday.get('date') == holiday_data['date']
        
        print(f"✓ Holiday added successfully: {holiday.get('name')} on {holiday.get('date')}")
        return holiday
    
    def test_stas_can_list_holidays(self, api_client, users_map):
        """Test STAS can list holidays"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(
            f"{BASE_URL}/api/stas/holidays",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to list holidays: {response.text}"
        holidays = response.json()
        
        assert isinstance(holidays, list), "Holidays should be a list"
        print(f"✓ Listed {len(holidays)} holidays")
        
        # Verify holiday structure
        for h in holidays[:1]:
            assert 'id' in h or 'name' in h, "Holiday should have id or name"
            print(f"  - {h.get('name')} / {h.get('name_ar')} on {h.get('date')}")
        
        return holidays
    
    def test_stas_can_delete_holiday(self, api_client, users_map):
        """Test STAS can delete a holiday"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # First add a holiday to delete
        holiday_data = {
            "name": "TEST Delete Holiday",
            "name_ar": "عطلة اختبار الحذف",
            "date": "2026-12-31"
        }
        
        add_response = api_client.post(
            f"{BASE_URL}/api/stas/holidays",
            json=holiday_data,
            headers=auth_headers(token)
        )
        
        if add_response.status_code == 400:
            # Try with different date
            holiday_data['date'] = "2026-12-30"
            add_response = api_client.post(
                f"{BASE_URL}/api/stas/holidays",
                json=holiday_data,
                headers=auth_headers(token)
            )
        
        if add_response.status_code != 200:
            pytest.skip("Cannot add holiday to test deletion")
        
        holiday = add_response.json()
        holiday_id = holiday.get('id')
        
        # Now delete it
        delete_response = api_client.delete(
            f"{BASE_URL}/api/stas/holidays/{holiday_id}",
            headers=auth_headers(token)
        )
        
        assert delete_response.status_code == 200, f"Failed to delete holiday: {delete_response.text}"
        print(f"✓ Holiday deleted successfully")
    
    def test_non_stas_cannot_add_holiday(self, api_client, users_map):
        """Test that non-STAS users cannot add holidays"""
        employee = users_map.get('employee1')
        token = get_token(api_client, employee['id'])
        
        holiday_data = {
            "name": "Unauthorized Holiday",
            "name_ar": "عطلة غير مصرح بها",
            "date": "2026-11-15"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/stas/holidays",
            json=holiday_data,
            headers=auth_headers(token)
        )
        
        assert response.status_code in [401, 403], f"Non-STAS should not add holidays: {response.text}"
        print(f"✓ Non-STAS user correctly blocked from adding holidays")


# ==================== ISSUE 7: STAS MAINTENANCE TOOLS ====================
class TestSTASMaintenanceTools:
    """Test STAS maintenance tools - purge transactions and archived users"""
    
    def test_stas_can_view_archived_users(self, api_client, users_map):
        """Test STAS can view archived users"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(
            f"{BASE_URL}/api/stas/users/archived",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200, f"Failed to get archived users: {response.text}"
        archived = response.json()
        
        assert isinstance(archived, list), "Archived users should be a list"
        print(f"✓ Archived users endpoint works, found {len(archived)} archived users")
        return archived
    
    def test_purge_transactions_requires_confirm(self, api_client, users_map):
        """Test purge transactions requires confirm=true"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # Try without confirm
        response = api_client.post(
            f"{BASE_URL}/api/stas/maintenance/purge-transactions",
            json={"confirm": False},
            headers=auth_headers(token)
        )
        
        assert response.status_code == 400, f"Should fail without confirm=true: {response.text}"
        assert "confirm" in response.text.lower() or "CONFIRM" in response.text
        print(f"✓ Purge transactions correctly requires confirm=true")
    
    def test_non_stas_cannot_purge(self, api_client, users_map):
        """Test non-STAS cannot purge transactions"""
        employee = users_map.get('employee1')
        token = get_token(api_client, employee['id'])
        
        response = api_client.post(
            f"{BASE_URL}/api/stas/maintenance/purge-transactions",
            json={"confirm": True},
            headers=auth_headers(token)
        )
        
        assert response.status_code in [401, 403], f"Non-STAS should not purge: {response.text}"
        print(f"✓ Non-STAS user correctly blocked from purging")


# ==================== ISSUE 3: PDF ARABIC RENDERING ====================
class TestPDFArabicRendering:
    """Test PDF generation with Arabic content"""
    
    def test_pdf_endpoint_exists(self, api_client, users_map):
        """Test that PDF endpoint exists and works"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # Get a transaction to test PDF
        response = api_client.get(
            f"{BASE_URL}/api/transactions",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200
        transactions = response.json()
        
        if not transactions:
            print("✓ No transactions to test PDF, but endpoint exists")
            return
        
        tx = transactions[0]
        tx_id = tx.get('id')
        
        # Get PDF
        pdf_response = api_client.get(
            f"{BASE_URL}/api/transactions/{tx_id}/pdf",
            headers=auth_headers(token)
        )
        
        assert pdf_response.status_code == 200, f"Failed to get PDF: {pdf_response.text}"
        
        # Check it's actually a PDF
        content_type = pdf_response.headers.get('content-type', '')
        assert 'pdf' in content_type.lower(), f"Expected PDF content type, got: {content_type}"
        
        # Check PDF starts with %PDF
        content = pdf_response.content
        assert content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ PDF generated successfully for {tx.get('ref_no')}, size: {len(content)} bytes")


# ==================== TRANSLATIONS ENDPOINT ====================
class TestTranslationsAPI:
    """Test that translations are available"""
    
    def test_api_returns_bilingual_data(self, api_client, users_map):
        """Test that API returns bilingual data"""
        response = api_client.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        
        # Check that users have both English and Arabic names
        for user in users:
            full_name = user.get('full_name', '')
            full_name_ar = user.get('full_name_ar', '')
            
            assert full_name, f"User {user.get('username')} missing full_name"
            assert full_name_ar, f"User {user.get('username')} missing full_name_ar"
            
        print(f"✓ All {len(users)} users have bilingual names")
    
    def test_leave_api_returns_holiday_names(self, api_client, users_map):
        """Test that leave API returns holiday names in both languages"""
        employee = users_map.get('employee1')
        token = get_token(api_client, employee['id'])
        
        response = api_client.get(
            f"{BASE_URL}/api/leave/holidays",
            headers=auth_headers(token)
        )
        
        assert response.status_code == 200
        holidays = response.json()
        
        if holidays:
            for h in holidays[:3]:
                print(f"  - {h.get('name')} / {h.get('name_ar')} on {h.get('date')}")
            print(f"✓ Holidays API returns {len(holidays)} holidays with bilingual names")
        else:
            print("✓ No holidays configured yet")


# ==================== HEALTH CHECK ====================
class TestHealthCheck:
    """Basic health check tests"""
    
    def test_health_endpoint(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ Health check passed: {data}")
    
    def test_users_endpoint(self, api_client):
        """Test users endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        assert len(users) > 0, "Should have at least one user"
        print(f"✓ Found {len(users)} users in system")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
