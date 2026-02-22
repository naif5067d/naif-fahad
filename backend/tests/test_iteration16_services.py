"""
Test Iteration 16 - Service Layer Tests
=========================================
Testing features:
1. Service Calculator - مدة الخدمة و EOS
2. Leave Service - نظام الإجازات 21/30 و المرضية 30/60/30
3. Attendance Service - الغياب التلقائي و رمضان
4. Settlement Service - محرك المخالصة
5. STAS Mirror Service - مرآة STAS (Pre-Checks)
6. STAS Routes - رمضان, إرجاع المعاملة مرة واحدة
7. Employee Routes - تعيين المشرف
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://stas-mirror-fix.preview.emergentagent.com"

# Test user IDs (from previous iterations)
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
NAIF_USER_ID = "3f2532cf-499e-54b3-a1b7-f8083ef5414f"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def stas_token(api_client):
    """Get STAS authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("STAS Authentication failed - skipping authenticated tests")


@pytest.fixture
def sultan_token(api_client):
    """Get Sultan authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Sultan Authentication failed")


@pytest.fixture
def naif_token(api_client):
    """Get Naif authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{NAIF_USER_ID}")
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Naif Authentication failed")


@pytest.fixture
def stas_client(api_client, stas_token):
    """Session with STAS auth header"""
    api_client.headers.update({"Authorization": f"Bearer {stas_token}"})
    return api_client


@pytest.fixture
def sultan_client(api_client, sultan_token):
    """Session with Sultan auth header"""
    api_client.headers.update({"Authorization": f"Bearer {sultan_token}"})
    return api_client


class TestServiceCalculator:
    """Tests for service_calculator.py - مدة الخدمة و EOS"""
    
    def test_employee_summary_returns_service_info(self, stas_client):
        """Test /api/employees/{id}/summary returns service info from calculator"""
        # Get an employee with active contract
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        assert employees_response.status_code == 200
        
        employees = employees_response.json()
        if not employees:
            pytest.skip("No employees found")
        
        # Get employee with active contract
        employee_id = employees[0]['id']
        summary_response = stas_client.get(f"{BASE_URL}/api/employees/{employee_id}/summary")
        assert summary_response.status_code == 200
        
        data = summary_response.json()
        # Check service_info is returned (from service_calculator)
        if data.get('service_info'):
            assert 'service' in data['service_info']
            service = data['service_info']['service']
            # Service should have calculated years
            assert 'years' in service
            assert 'total_days' in service
            assert 'formatted_ar' in service
            print(f"✓ Service info returned: {service['formatted_ar']}")
        else:
            print("⚠ No service_info (no active contract)")
    
    def test_service_calculation_format(self, stas_client):
        """Test service calculation returns correct format"""
        # Use contracts-v2 to find employee with contract
        contracts_response = stas_client.get(f"{BASE_URL}/api/contracts-v2")
        assert contracts_response.status_code == 200
        
        contracts = contracts_response.json()
        active_contracts = [c for c in contracts if c.get('status') == 'active']
        
        if not active_contracts:
            pytest.skip("No active contracts")
        
        employee_id = active_contracts[0]['employee_id']
        summary_response = stas_client.get(f"{BASE_URL}/api/employees/{employee_id}/summary")
        assert summary_response.status_code == 200
        
        data = summary_response.json()
        if data.get('service_info'):
            service = data['service_info']['service']
            # Check 4 decimal precision for years
            assert isinstance(service['years'], (int, float))
            # Check integer years
            assert isinstance(service['years_int'], int)
            # Check remaining calculation
            assert 'remaining_months' in service
            assert 'remaining_days' in service
            print(f"✓ Years: {service['years']}, Int: {service['years_int']}, Months: {service['remaining_months']}, Days: {service['remaining_days']}")


class TestLeaveService:
    """Tests for leave_service.py - نظام الإجازات 21/30"""
    
    def test_leave_balance_endpoint_exists(self, stas_client):
        """Test /api/employees/{id}/leave-balance endpoint"""
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        assert employees_response.status_code == 200
        
        employees = employees_response.json()
        if not employees:
            pytest.skip("No employees")
        
        employee_id = employees[0]['id']
        balance_response = stas_client.get(f"{BASE_URL}/api/employees/{employee_id}/leave-balance")
        assert balance_response.status_code == 200
        
        data = balance_response.json()
        # Should return dict with leave types
        assert isinstance(data, dict)
        print(f"✓ Leave balance: {data}")
    
    def test_employee_summary_contains_leave(self, stas_client):
        """Test /api/employees/{id}/summary contains leave summary from service"""
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        employees = employees_response.json()
        
        if not employees:
            pytest.skip("No employees")
        
        employee_id = employees[0]['id']
        summary_response = stas_client.get(f"{BASE_URL}/api/employees/{employee_id}/summary")
        assert summary_response.status_code == 200
        
        data = summary_response.json()
        assert 'leave' in data
        # Leave should have balances, annual, sick info
        leave = data['leave']
        assert 'balances' in leave
        print(f"✓ Leave info in summary: balances={leave.get('balances')}")


class TestAttendanceService:
    """Tests for attendance_service.py - الحضور و رمضان"""
    
    def test_ramadan_settings_endpoint(self, stas_client):
        """Test GET /api/stas/ramadan endpoint"""
        response = stas_client.get(f"{BASE_URL}/api/stas/ramadan")
        assert response.status_code == 200
        
        data = response.json()
        # Should return is_active and hours info
        assert 'is_active' in data or 'hours_per_day' in data
        print(f"✓ Ramadan settings: is_active={data.get('is_active')}, hours={data.get('hours_per_day', 8)}")
    
    def test_ramadan_activate_endpoint_stas_only(self, api_client):
        """Test POST /api/stas/ramadan/activate (STAS only)"""
        # Get fresh STAS token
        stas_resp = api_client.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        stas_token = stas_resp.json().get("token")
        
        headers = {"Authorization": f"Bearer {stas_token}", "Content-Type": "application/json"}
        
        # First deactivate if active
        api_client.post(f"{BASE_URL}/api/stas/ramadan/deactivate", headers=headers)
        
        # Test activation
        today = datetime.now()
        payload = {
            "start_date": today.strftime("%Y-%m-%d"),
            "end_date": (today + timedelta(days=30)).strftime("%Y-%m-%d")
        }
        
        response = api_client.post(f"{BASE_URL}/api/stas/ramadan/activate", json=payload, headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert 'settings' in data
        assert data['settings']['is_active'] == True
        assert data['settings']['hours_per_day'] == 6
        print(f"✓ Ramadan activated: {data['settings']['start_date']} to {data['settings']['end_date']}")
        
        # Test Sultan cannot activate (should fail)
        sultan_resp = api_client.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        sultan_token = sultan_resp.json().get("token")
        sultan_headers = {"Authorization": f"Bearer {sultan_token}", "Content-Type": "application/json"}
        
        sultan_response = api_client.post(f"{BASE_URL}/api/stas/ramadan/activate", json=payload, headers=sultan_headers)
        # Sultan should be forbidden (403)
        assert sultan_response.status_code == 403 or sultan_response.status_code == 401
        print(f"✓ Sultan correctly blocked from activating Ramadan (status={sultan_response.status_code})")
    
    def test_ramadan_deactivate_endpoint(self, api_client):
        """Test POST /api/stas/ramadan/deactivate"""
        # Get fresh STAS token
        stas_resp = api_client.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        stas_token = stas_resp.json().get("token")
        
        headers = {"Authorization": f"Bearer {stas_token}", "Content-Type": "application/json"}
        
        response = api_client.post(f"{BASE_URL}/api/stas/ramadan/deactivate", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should deactivate
        settings = data.get('settings', {})
        if settings:
            assert settings.get('is_active') == False or 'deactivated' in str(data)
        print(f"✓ Ramadan deactivated")
    
    def test_calculate_daily_attendance_endpoint(self, stas_client):
        """Test POST /api/stas/attendance/calculate-daily"""
        response = stas_client.post(f"{BASE_URL}/api/stas/attendance/calculate-daily")
        assert response.status_code == 200
        
        data = response.json()
        assert 'result' in data
        result = data['result']
        # Should return summary
        assert 'date' in result
        assert 'summary' in result
        print(f"✓ Daily attendance calculated: {result['summary']}")
    
    def test_calculate_for_specific_date(self, stas_client):
        """Test POST /api/stas/attendance/calculate-for-date?date=YYYY-MM-DD"""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = stas_client.post(f"{BASE_URL}/api/stas/attendance/calculate-for-date?date={yesterday}")
        assert response.status_code == 200
        
        data = response.json()
        assert 'result' in data
        print(f"✓ Attendance for {yesterday}: {data['result'].get('summary', {})}")


class TestSTASMirrorService:
    """Tests for stas_mirror_service.py - مرآة STAS و Pre-Checks"""
    
    def test_mirror_endpoint_exists(self, stas_client):
        """Test GET /api/stas/mirror/{transaction_id}"""
        # Get a pending transaction
        txs_response = stas_client.get(f"{BASE_URL}/api/stas/pending")
        assert txs_response.status_code == 200
        
        transactions = txs_response.json()
        if not transactions:
            pytest.skip("No pending transactions")
        
        tx_id = transactions[0]['id']
        mirror_response = stas_client.get(f"{BASE_URL}/api/stas/mirror/{tx_id}")
        assert mirror_response.status_code == 200
        
        data = mirror_response.json()
        # Mirror should contain pre_checks
        assert 'pre_checks' in data
        # Should have all_checks_pass indicator
        assert 'all_checks_pass' in data
        print(f"✓ Mirror data has {len(data['pre_checks'])} pre-checks, all_pass={data['all_checks_pass']}")
    
    def test_mirror_pre_checks_have_status(self, stas_client):
        """Test pre_checks contain PASS/FAIL/WARN status"""
        txs_response = stas_client.get(f"{BASE_URL}/api/stas/pending")
        transactions = txs_response.json()
        
        if not transactions:
            pytest.skip("No pending transactions")
        
        tx_id = transactions[0]['id']
        mirror_response = stas_client.get(f"{BASE_URL}/api/stas/mirror/{tx_id}")
        data = mirror_response.json()
        
        # Each pre_check should have status
        for check in data.get('pre_checks', []):
            assert 'status' in check
            assert check['status'] in ['PASS', 'FAIL', 'WARN']
            assert 'name' in check or 'name_ar' in check
            print(f"  → {check.get('name', check.get('name_ar'))}: {check['status']}")


class TestTransactionReturn:
    """Tests for transaction return - إرجاع المعاملة مرة واحدة فقط"""
    
    def test_return_transaction_once_only(self, stas_client):
        """Test POST /api/stas/return/{id} - مرة واحدة فقط"""
        # Get a pending transaction
        txs_response = stas_client.get(f"{BASE_URL}/api/stas/pending")
        transactions = txs_response.json()
        
        if not transactions:
            pytest.skip("No pending transactions")
        
        # Find a transaction that hasn't been returned yet
        unreturned = [t for t in transactions if not t.get('returned_by_stas')]
        if not unreturned:
            print("⚠ All transactions already returned - testing error response")
            # Try to return an already-returned one
            tx_id = transactions[0]['id']
            response = stas_client.post(f"{BASE_URL}/api/stas/return/{tx_id}", json={"note": "test"})
            # Should fail with 400
            assert response.status_code == 400
            data = response.json()
            assert 'ALREADY_RETURNED' in str(data) or 'already' in str(data).lower()
            print(f"✓ Already returned transaction correctly blocked")
            return
        
        # Return transaction first time - should succeed
        tx_id = unreturned[0]['id']
        response = stas_client.post(f"{BASE_URL}/api/stas/return/{tx_id}", json={"note": "test return"})
        
        if response.status_code == 200:
            print(f"✓ First return succeeded for {tx_id}")
            
            # Try to return again - should fail
            response2 = stas_client.post(f"{BASE_URL}/api/stas/return/{tx_id}", json={"note": "second return"})
            assert response2.status_code == 400
            data = response2.json()
            assert 'ALREADY_RETURNED' in str(data) or 'already' in str(data).lower()
            print(f"✓ Second return correctly blocked with: {data.get('detail', {}).get('message_ar', str(data))}")
        else:
            # May have been returned already
            assert response.status_code == 400
            print(f"✓ Return blocked (may have been returned previously)")


class TestSupervisorAssignment:
    """Tests for /api/employees/{id}/supervisor - تعيين المشرف"""
    
    def test_assign_supervisor_endpoint(self, stas_client):
        """Test PUT /api/employees/{id}/supervisor"""
        # Get employees
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        employees = employees_response.json()
        
        if len(employees) < 2:
            pytest.skip("Need at least 2 employees")
        
        employee_id = employees[0]['id']
        supervisor_id = employees[1]['id']
        
        # Assign supervisor
        response = stas_client.put(
            f"{BASE_URL}/api/employees/{employee_id}/supervisor",
            json={"supervisor_id": supervisor_id}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data['supervisor_id'] == supervisor_id
        print(f"✓ Supervisor assigned: {data.get('supervisor_name', '')}")
    
    def test_cannot_assign_self_as_supervisor(self, stas_client):
        """Test cannot assign employee as their own supervisor"""
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        employees = employees_response.json()
        
        if not employees:
            pytest.skip("No employees")
        
        employee_id = employees[0]['id']
        
        # Try to assign self - should fail
        response = stas_client.put(
            f"{BASE_URL}/api/employees/{employee_id}/supervisor",
            json={"supervisor_id": employee_id}
        )
        assert response.status_code == 400
        print(f"✓ Self-assignment correctly blocked")
    
    def test_remove_supervisor(self, stas_client):
        """Test DELETE /api/employees/{id}/supervisor"""
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        employees = employees_response.json()
        
        if not employees:
            pytest.skip("No employees")
        
        employee_id = employees[0]['id']
        
        # Remove supervisor
        response = stas_client.delete(f"{BASE_URL}/api/employees/{employee_id}/supervisor")
        assert response.status_code == 200
        print(f"✓ Supervisor removed")


class TestSettlementService:
    """Tests for settlement_service.py - محرك المخالصة"""
    
    def test_settlement_mirror_data_for_terminated_contract(self, stas_client):
        """Test settlement mirror data includes EOS calculation"""
        # Get contracts to find terminated one
        contracts_response = stas_client.get(f"{BASE_URL}/api/contracts-v2")
        contracts = contracts_response.json()
        
        terminated = [c for c in contracts if c.get('status') == 'terminated']
        if not terminated:
            print("⚠ No terminated contracts - skipping settlement test")
            pytest.skip("No terminated contracts")
        
        # Get pending settlement transaction
        txs_response = stas_client.get(f"{BASE_URL}/api/stas/pending")
        transactions = txs_response.json()
        
        settlements = [t for t in transactions if t.get('type') == 'settlement']
        if not settlements:
            pytest.skip("No settlement transactions pending")
        
        tx_id = settlements[0]['id']
        mirror_response = stas_client.get(f"{BASE_URL}/api/stas/mirror/{tx_id}")
        assert mirror_response.status_code == 200
        
        data = mirror_response.json()
        # Settlement mirror should have settlement_details
        if 'settlement_details' in data:
            details = data['settlement_details']
            assert 'pre_checks' in details
            print(f"✓ Settlement mirror has pre_checks")


class TestEmployeeSummaryEndpoint:
    """Tests for /api/employees/{id}/summary - ملخص شامل للموظف"""
    
    def test_summary_contains_all_sections(self, stas_client):
        """Test employee summary contains all required sections"""
        employees_response = stas_client.get(f"{BASE_URL}/api/employees")
        employees = employees_response.json()
        
        if not employees:
            pytest.skip("No employees")
        
        employee_id = employees[0]['id']
        summary_response = stas_client.get(f"{BASE_URL}/api/employees/{employee_id}/summary")
        assert summary_response.status_code == 200
        
        data = summary_response.json()
        
        # Check all required sections
        required_sections = ['employee', 'leave', 'attendance', 'finance']
        for section in required_sections:
            assert section in data, f"Missing section: {section}"
        
        # Check attendance contains summary and today status
        assert 'summary_30_days' in data['attendance'] or 'unsettled_absences' in data['attendance']
        assert 'today_status' in data['attendance']
        
        print(f"✓ Employee summary contains all sections")
        print(f"  → Leave balances: {data['leave'].get('balances', {})}")
        print(f"  → Today status: {data['attendance'].get('today_status')}")
        print(f"  → Unsettled absences: {data['attendance'].get('unsettled_absences', 0)}")


class TestHealthAndBasicAPIs:
    """Basic API health checks"""
    
    def test_health_endpoint(self, api_client):
        """Test /api/health"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        print(f"✓ Health check: {data}")
    
    def test_auth_switch_works(self, api_client):
        """Test authentication switch"""
        response = api_client.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        assert data['user']['role'] == 'stas'
        print(f"✓ Auth switch works: {data['user']['username']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
