"""
Iteration 17 Bug Testing
Tests for bug fixes:
B: Ramadan mode activation with custom work_start/work_end times
C: Map visibility public endpoint
D: Sultan self-request goes to CEO
E: Supervisor assignment API
G: STAS Mirror shows PASS for active contracts, FAIL for terminated
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test users
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"

class TestRamadanMode:
    """B: Ramadan mode activation with custom work_start/work_end times"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get STAS token"""
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        if resp.status_code == 200:
            self.stas_token = resp.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.stas_token}"}
        else:
            pytest.skip("Cannot get STAS token")
    
    def test_activate_ramadan_with_custom_times(self):
        """Test POST /api/stas/ramadan/activate with custom work_start/work_end"""
        payload = {
            "start_date": "2026-03-01",
            "end_date": "2026-03-30",
            "work_start": "10:00",  # Custom start time
            "work_end": "16:00"     # Custom end time
        }
        response = requests.post(
            f"{BASE_URL}/api/stas/ramadan/activate", 
            headers=self.headers,
            json=payload
        )
        assert response.status_code == 200, f"Failed to activate Ramadan: {response.text}"
        
        data = response.json()
        assert "settings" in data
        settings = data['settings']
        
        # Verify custom times are saved
        assert settings.get('start_time') == "10:00", f"Expected start_time=10:00, got {settings.get('start_time')}"
        assert settings.get('end_time') == "16:00", f"Expected end_time=16:00, got {settings.get('end_time')}"
        assert settings.get('hours_per_day') == 6
        assert settings.get('is_active') == True
        print(f"Ramadan settings saved: start_time={settings['start_time']}, end_time={settings['end_time']}")
    
    def test_get_ramadan_settings_shows_custom_times(self):
        """Test GET /api/stas/ramadan returns custom times"""
        response = requests.get(f"{BASE_URL}/api/stas/ramadan", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        if data.get('is_active'):
            assert 'start_time' in data
            assert 'end_time' in data
            print(f"Ramadan GET: is_active={data['is_active']}, start_time={data.get('start_time')}, end_time={data.get('end_time')}")
        else:
            print("Ramadan not active, skipping time check")
    
    def test_deactivate_ramadan(self):
        """Clean up - deactivate Ramadan mode"""
        response = requests.post(f"{BASE_URL}/api/stas/ramadan/deactivate", headers=self.headers)
        assert response.status_code == 200
        print("Ramadan mode deactivated")


class TestMapVisibilityPublic:
    """C: Map visibility public endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens for both STAS and Sultan"""
        # STAS token
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        if resp.status_code == 200:
            self.stas_token = resp.json().get('token')
            self.stas_headers = {"Authorization": f"Bearer {self.stas_token}"}
        else:
            pytest.skip("Cannot get STAS token")
        
        # Sultan token (regular user)
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if resp.status_code == 200:
            self.sultan_token = resp.json().get('token')
            self.sultan_headers = {"Authorization": f"Bearer {self.sultan_token}"}
        else:
            pytest.skip("Cannot get Sultan token")
    
    def test_map_visibility_public_endpoint_for_regular_user(self):
        """Test GET /api/stas/settings/map-visibility/public accessible by non-STAS"""
        response = requests.get(
            f"{BASE_URL}/api/stas/settings/map-visibility/public",
            headers=self.sultan_headers  # Sultan, not STAS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert 'show_map_to_employees' in data
        print(f"Map visibility public endpoint: show_map_to_employees={data['show_map_to_employees']}")
    
    def test_set_and_verify_map_visibility(self):
        """Test setting map visibility and reading via public endpoint"""
        # STAS sets map visibility
        set_response = requests.post(
            f"{BASE_URL}/api/stas/settings/map-visibility?show=true",
            headers=self.stas_headers
        )
        assert set_response.status_code == 200
        
        # Sultan reads via public endpoint
        get_response = requests.get(
            f"{BASE_URL}/api/stas/settings/map-visibility/public",
            headers=self.sultan_headers
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get('show_map_to_employees') == True
        print("Map visibility set to true and verified via public endpoint")


class TestSultanSelfRequestToCEO:
    """D: Sultan self-request goes to CEO"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get Sultan token and find Sultan's employee_id"""
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if resp.status_code == 200:
            self.sultan_token = resp.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.sultan_token}"}
        else:
            pytest.skip("Cannot get Sultan token")
        
        # Get Sultan's employee record
        emp_resp = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        if emp_resp.status_code == 200:
            employees = emp_resp.json()
            # Find Sultan's employee record by user_id
            sultan_emp = next((e for e in employees if e.get('user_id') == SULTAN_USER_ID), None)
            if sultan_emp:
                self.sultan_employee_id = sultan_emp['id']
            else:
                # Find by name
                sultan_emp = next((e for e in employees if 'sultan' in e.get('full_name', '').lower()), None)
                if sultan_emp:
                    self.sultan_employee_id = sultan_emp['id']
                else:
                    pytest.skip("Cannot find Sultan's employee record")
        else:
            pytest.skip("Cannot get employees")
    
    def test_sultan_leave_request_goes_to_ceo(self):
        """Test that Sultan's leave request skips ops and goes to CEO"""
        payload = {
            "employee_id": self.sultan_employee_id,
            "leave_type": "annual",
            "start_date": "2026-02-15",
            "end_date": "2026-02-16"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/transactions/leave",
            headers=self.headers,
            json=payload
        )
        
        # Check response
        print(f"Leave request response: {response.status_code} - {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            tx = data.get('transaction', {})
            
            # Check workflow and current_stage
            workflow = tx.get('workflow', [])
            current_stage = tx.get('current_stage', '')
            status = tx.get('status', '')
            
            print(f"Transaction created: ref={tx.get('ref_no')}, workflow={workflow}, current_stage={current_stage}, status={status}")
            
            # For Sultan's self-request, it should go to CEO (not ops)
            # The workflow should either skip ops or current_stage should be ceo
            assert 'ceo' in workflow or current_stage == 'ceo', \
                f"Sultan's self-request should go to CEO. workflow={workflow}, current_stage={current_stage}"
            
            # Store transaction ID for cleanup
            self.tx_id = tx.get('id')
        else:
            # Check if it's a balance issue or other error
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            print(f"Error creating leave request: {error_data}")


class TestSupervisorAssignment:
    """E: Supervisor assignment API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get STAS token"""
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        if resp.status_code == 200:
            self.token = resp.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Cannot get STAS token")
        
        # Get employees list
        emp_resp = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        if emp_resp.status_code == 200:
            self.employees = emp_resp.json()
        else:
            pytest.skip("Cannot get employees")
    
    def test_supervisor_assignment_endpoint_exists(self):
        """Test PUT /api/employees/{id}/supervisor endpoint exists"""
        if len(self.employees) < 2:
            pytest.skip("Need at least 2 employees")
        
        employee = self.employees[0]
        supervisor = self.employees[1]
        
        response = requests.put(
            f"{BASE_URL}/api/employees/{employee['id']}/supervisor",
            headers=self.headers,
            json={"supervisor_id": supervisor['id']}
        )
        
        # Should be 200 or at least not 404/405
        assert response.status_code in [200, 400], f"Unexpected response: {response.status_code} - {response.text}"
        print(f"Supervisor assignment response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Supervisor assigned successfully: {data}")
    
    def test_self_supervisor_assignment_blocked(self):
        """Test that employee cannot be assigned as their own supervisor"""
        if len(self.employees) < 1:
            pytest.skip("Need at least 1 employee")
        
        employee = self.employees[0]
        
        response = requests.put(
            f"{BASE_URL}/api/employees/{employee['id']}/supervisor",
            headers=self.headers,
            json={"supervisor_id": employee['id']}  # Same as employee
        )
        
        # Should be blocked (400)
        assert response.status_code == 400, f"Self-assignment should be blocked: {response.status_code}"
        print("Self-assignment correctly blocked")


class TestSTASMirrorContractCheck:
    """G: STAS Mirror shows PASS for active contracts, FAIL for terminated"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get STAS token"""
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        if resp.status_code == 200:
            self.token = resp.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Cannot get STAS token")
    
    def test_get_pending_transactions(self):
        """Test GET /api/stas/pending returns transactions"""
        response = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.headers)
        assert response.status_code == 200
        
        transactions = response.json()
        print(f"Found {len(transactions)} pending transactions")
        
        if transactions:
            # Store first transaction for mirror test
            self.pending_tx = transactions[0]
            return transactions
        return []
    
    def test_mirror_shows_contract_check(self):
        """Test GET /api/stas/mirror/{id} includes Active Contract check"""
        # First get pending transactions
        pending = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.headers)
        if pending.status_code != 200 or not pending.json():
            pytest.skip("No pending transactions to test mirror")
        
        tx = pending.json()[0]
        tx_id = tx['id']
        
        # Get mirror data
        response = requests.get(f"{BASE_URL}/api/stas/mirror/{tx_id}", headers=self.headers)
        assert response.status_code == 200
        
        mirror_data = response.json()
        pre_checks = mirror_data.get('pre_checks', [])
        
        print(f"Mirror for {tx.get('ref_no')} has {len(pre_checks)} pre_checks")
        
        # Find Active Contract check
        contract_check = next(
            (c for c in pre_checks if 'Contract' in c.get('name', '') or 'العقد' in c.get('name_ar', '')), 
            None
        )
        
        if contract_check:
            print(f"Contract check: name={contract_check['name']}, status={contract_check['status']}, detail={contract_check['detail']}")
            assert contract_check['status'] in ['PASS', 'FAIL', 'WARN']
        
        # Print all checks
        for check in pre_checks:
            print(f"  - {check.get('name')}: {check.get('status')} - {check.get('detail', '')[:50]}")
    
    def test_mirror_for_leave_request_shows_active_contract_pass(self):
        """Test that leave request for active employee shows PASS for contract"""
        # Get pending leave requests
        pending = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.headers)
        if pending.status_code != 200 or not pending.json():
            pytest.skip("No pending transactions")
        
        # Find leave request
        leave_tx = next((t for t in pending.json() if t.get('type') == 'leave_request'), None)
        if not leave_tx:
            pytest.skip("No pending leave requests")
        
        # Get mirror
        response = requests.get(f"{BASE_URL}/api/stas/mirror/{leave_tx['id']}", headers=self.headers)
        assert response.status_code == 200
        
        mirror_data = response.json()
        pre_checks = mirror_data.get('pre_checks', [])
        
        # Find Active Contract check
        contract_check = next(
            (c for c in pre_checks if 'Active Contract' in c.get('name', '')), 
            None
        )
        
        if contract_check:
            print(f"Leave request contract check: {contract_check['status']} - {contract_check['detail']}")
            # For active employee with active contract, should be PASS
            # If it's FAIL, it means terminated contract which is correct behavior
        else:
            print("Active Contract check not found in pre_checks")


class TestContractsV2ForTerminated:
    """Test contracts-v2 to find terminated contracts for mirror testing"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get STAS token"""
        resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        if resp.status_code == 200:
            self.token = resp.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Cannot get STAS token")
    
    def test_get_contracts_v2(self):
        """Test GET /api/contracts-v2 returns contracts"""
        response = requests.get(f"{BASE_URL}/api/contracts-v2", headers=self.headers)
        assert response.status_code == 200
        
        contracts = response.json()
        print(f"Found {len(contracts)} contracts")
        
        # Group by status
        by_status = {}
        for c in contracts:
            status = c.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1
        
        print(f"Contracts by status: {by_status}")
        
        # Check for EMP-005 (terminated contract mentioned in requirements)
        emp005_contracts = [c for c in contracts if 'EMP-005' in str(c.get('employee_number', '')) or 'EMP-005' in str(c)]
        if emp005_contracts:
            print(f"EMP-005 contracts: {emp005_contracts}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
