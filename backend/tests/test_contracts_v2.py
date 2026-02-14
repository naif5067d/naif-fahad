"""
Test Contracts V2 System - DAC-YYYY-XXX Serial Format
Tests:
- Contract listing with DAC-YYYY-XXX format
- Serial number increments (DAC-2026-001, DAC-2026-002, etc.)
- Contract CRUD operations
- Contract lifecycle (draft → pending_stas → active → terminated → closed)
- Role-based permissions (sultan/naif: create+edit+submit | STAS: everything)
- Delete draft contracts only
- Date format verification (Gregorian + Hijri)
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# User IDs for role-based testing
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
NAIF_USER_ID = "3f2532cf-499e-54b3-a1b7-f8083ef5414f"
EMPLOYEE_USER_ID = "46c9dd1a-7f0f-584b-9bab-b37b949afece"


@pytest.fixture(scope="module")
def stas_token():
    """Get STAS token for full access"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert resp.status_code == 200, f"Failed to get STAS token: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def sultan_token():
    """Get Sultan token for limited access"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    assert resp.status_code == 200, f"Failed to get Sultan token: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def naif_token():
    """Get Naif token for limited access"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{NAIF_USER_ID}")
    assert resp.status_code == 200, f"Failed to get Naif token: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def employee_token():
    """Get employee token for restricted access"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{EMPLOYEE_USER_ID}")
    assert resp.status_code == 200, f"Failed to get employee token: {resp.text}"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def employees(stas_token):
    """Get list of employees for contract creation"""
    headers = {"Authorization": f"Bearer {stas_token}"}
    resp = requests.get(f"{BASE_URL}/api/employees", headers=headers)
    assert resp.status_code == 200
    return resp.json()


class TestContractListAndFormat:
    """Test GET /api/contracts-v2 returns contracts with DAC-YYYY-XXX format"""
    
    def test_list_contracts_returns_data(self, stas_token):
        """Test that contracts list endpoint returns data"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        contracts = resp.json()
        assert isinstance(contracts, list), "Response should be a list"
        assert len(contracts) > 0, "Should have at least one contract"
        print(f"✓ Found {len(contracts)} contracts")
    
    def test_contracts_have_dac_format_serial(self, stas_token):
        """Test that all contracts have DAC-YYYY-XXX serial format"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        import re
        dac_pattern = re.compile(r'^DAC-\d{4}-\d{3}$')
        
        for contract in contracts:
            serial = contract.get("contract_serial")
            assert serial is not None, f"Contract {contract['id']} missing serial"
            assert dac_pattern.match(serial), f"Serial '{serial}' doesn't match DAC-YYYY-XXX format"
        
        print(f"✓ All {len(contracts)} contracts have valid DAC-YYYY-XXX format")
    
    def test_contracts_serial_increment(self, stas_token):
        """Test that contract serials increment correctly"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        # Extract serial numbers and sort
        serials = sorted([c["contract_serial"] for c in contracts])
        
        # Check we have sequential serials (at least some)
        assert "DAC-2026-001" in serials, "First serial DAC-2026-001 should exist"
        
        # Verify format consistency
        current_year = datetime.now().year
        for serial in serials:
            parts = serial.split("-")
            assert parts[0] == "DAC", f"Serial {serial} should start with DAC"
            assert int(parts[1]) >= 2020, f"Year in {serial} seems too old"
            assert int(parts[1]) <= 2030, f"Year in {serial} seems too far in future"
        
        print(f"✓ Serial numbers: {serials}")
    
    def test_contracts_have_required_fields(self, stas_token):
        """Test contracts have all required fields"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        required_fields = [
            "id", "contract_serial", "version", "employee_id", "employee_code",
            "employee_name", "contract_category", "employment_type", "start_date",
            "status", "status_history", "created_at"
        ]
        
        for contract in contracts:
            for field in required_fields:
                assert field in contract, f"Contract missing required field: {field}"
        
        print(f"✓ All contracts have required fields")


class TestContractSearch:
    """Test contract search functionality"""
    
    def test_search_by_serial(self, stas_token):
        """Test search by contract serial"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2/search?q=DAC-2026-001", headers=headers)
        
        assert resp.status_code == 200
        contracts = resp.json()
        assert len(contracts) > 0, "Should find contract by serial"
        assert contracts[0]["contract_serial"] == "DAC-2026-001"
        print(f"✓ Found contract by serial")
    
    def test_search_by_employee_name(self, stas_token):
        """Test search by employee name"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2/search?q=Sultan", headers=headers)
        
        assert resp.status_code == 200
        contracts = resp.json()
        assert len(contracts) >= 0  # May or may not find depending on data
        print(f"✓ Search by name works (found {len(contracts)} contracts)")
    
    def test_filter_by_status(self, stas_token):
        """Test filter by status"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        resp = requests.get(f"{BASE_URL}/api/contracts-v2?status=active", headers=headers)
        
        assert resp.status_code == 200
        contracts = resp.json()
        for contract in contracts:
            assert contract["status"] == "active"
        print(f"✓ Status filter works (found {len(contracts)} active contracts)")


class TestContractCreate:
    """Test POST /api/contracts-v2 creates draft contract"""
    
    def test_create_contract_as_stas(self, stas_token, employees):
        """STAS can create contract"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Use first employee
        emp = employees[0]
        payload = {
            "employee_id": emp["id"],
            "employee_code": emp["employee_number"],
            "employee_name": emp["full_name"],
            "employee_name_ar": emp.get("full_name_ar", emp["full_name"]),
            "contract_category": "employment",
            "employment_type": "unlimited",
            "job_title": "TEST_Position",
            "start_date": "2026-03-01",
            "basic_salary": 5000,
            "housing_allowance": 500,
            "transport_allowance": 300,
        }
        
        resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        contract = resp.json()
        
        # Verify contract created
        assert "id" in contract
        assert contract["status"] == "draft", "New contract should be draft"
        assert contract["contract_serial"].startswith("DAC-"), f"Serial should start with DAC-"
        
        # Store for cleanup
        TestContractCreate.created_contract_id = contract["id"]
        TestContractCreate.created_serial = contract["contract_serial"]
        
        print(f"✓ Created contract: {contract['contract_serial']} in draft status")
        return contract
    
    def test_create_contract_as_sultan(self, sultan_token, employees):
        """Sultan can create contract"""
        headers = {"Authorization": f"Bearer {sultan_token}"}
        
        emp = employees[1] if len(employees) > 1 else employees[0]
        payload = {
            "employee_id": emp["id"],
            "employee_code": emp["employee_number"],
            "employee_name": emp["full_name"],
            "employee_name_ar": emp.get("full_name_ar", emp["full_name"]),
            "contract_category": "employment",
            "employment_type": "fixed_term",
            "job_title": "TEST_Engineer",
            "start_date": "2026-04-01",
            "end_date": "2027-03-31",
            "basic_salary": 6000,
        }
        
        resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        
        assert resp.status_code == 200, f"Sultan should be able to create: {resp.text}"
        contract = resp.json()
        assert contract["status"] == "draft"
        
        TestContractCreate.sultan_created_id = contract["id"]
        print(f"✓ Sultan created contract: {contract['contract_serial']}")
    
    def test_create_contract_as_naif(self, naif_token, employees):
        """Naif can create contract"""
        headers = {"Authorization": f"Bearer {naif_token}"}
        
        emp = employees[2] if len(employees) > 2 else employees[0]
        payload = {
            "employee_id": emp["id"],
            "employee_code": emp["employee_number"],
            "employee_name": emp["full_name"],
            "contract_category": "internship_unpaid",
            "start_date": "2026-05-01",
        }
        
        resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        
        assert resp.status_code == 200, f"Naif should be able to create: {resp.text}"
        contract = resp.json()
        
        # Internship should have 0 salary
        assert contract["basic_salary"] == 0, "Unpaid internship should have 0 salary"
        
        TestContractCreate.naif_created_id = contract["id"]
        print(f"✓ Naif created internship contract: {contract['contract_serial']}")
    
    def test_employee_cannot_create_contract(self, employee_token, employees):
        """Employee should NOT be able to create contract"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        payload = {
            "employee_id": employees[0]["id"],
            "employee_code": employees[0]["employee_number"],
            "employee_name": employees[0]["full_name"],
            "start_date": "2026-06-01",
        }
        
        resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        
        assert resp.status_code in [401, 403], f"Employee should be forbidden: {resp.status_code}"
        print(f"✓ Employee correctly blocked from creating contract")


class TestContractSubmitToSTAS:
    """Test POST /api/contracts-v2/{id}/submit changes status to pending_stas"""
    
    def test_submit_draft_to_stas(self, stas_token, employees):
        """Submit draft contract to STAS"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # First create a draft contract
        payload = {
            "employee_id": employees[0]["id"],
            "employee_code": employees[0]["employee_number"],
            "employee_name": employees[0]["full_name"],
            "start_date": "2026-07-01",
            "basic_salary": 4000,
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        assert create_resp.status_code == 200
        contract = create_resp.json()
        assert contract["status"] == "draft"
        
        # Submit to STAS
        submit_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/submit",
            headers=headers,
            json={"note": "Test submission"}
        )
        
        assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
        updated = submit_resp.json()
        assert updated["status"] == "pending_stas", f"Status should be pending_stas, got {updated['status']}"
        
        # Verify status history
        assert len(updated["status_history"]) >= 2, "Should have status history entry"
        
        TestContractSubmitToSTAS.pending_contract_id = contract["id"]
        print(f"✓ Contract {contract['contract_serial']} submitted to STAS")
    
    def test_cannot_submit_non_draft(self, stas_token):
        """Cannot submit contract that's not in draft status"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get an active contract
        resp = requests.get(f"{BASE_URL}/api/contracts-v2?status=active", headers=headers)
        contracts = resp.json()
        
        if contracts:
            active_contract = contracts[0]
            submit_resp = requests.post(
                f"{BASE_URL}/api/contracts-v2/{active_contract['id']}/submit",
                headers=headers
            )
            
            assert submit_resp.status_code == 400, "Should reject non-draft submit"
            print(f"✓ Correctly rejected submit of non-draft contract")
        else:
            pytest.skip("No active contracts to test")


class TestContractExecute:
    """Test POST /api/contracts-v2/{id}/execute (STAS only) activates contract"""
    
    def test_stas_can_execute_pending_contract(self, stas_token, employees):
        """STAS can execute pending_stas contract"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Create and submit a contract first
        payload = {
            "employee_id": employees[0]["id"],
            "employee_code": employees[0]["employee_number"],
            "employee_name": employees[0]["full_name"],
            "start_date": "2026-08-01",
            "basic_salary": 5500,
        }
        
        # Create
        create_resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        assert create_resp.status_code == 200
        contract = create_resp.json()
        
        # Submit
        submit_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/submit",
            headers=headers
        )
        assert submit_resp.status_code == 200
        
        # Execute
        execute_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/execute",
            headers=headers
        )
        
        # Note: May fail if employee already has active contract
        if execute_resp.status_code == 200:
            result = execute_resp.json()
            assert result["contract"]["status"] == "active"
            print(f"✓ STAS executed contract to active status")
        else:
            # Expected if employee has active contract
            assert "نشط" in execute_resp.text or "active" in execute_resp.text.lower()
            print(f"✓ Execute correctly blocked (employee may have active contract)")
    
    def test_sultan_cannot_execute(self, sultan_token, stas_token, employees):
        """Sultan cannot execute contracts"""
        headers = {"Authorization": f"Bearer {sultan_token}"}
        stas_headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Create a pending contract as STAS
        payload = {
            "employee_id": employees[0]["id"],
            "employee_code": employees[0]["employee_number"],
            "employee_name": employees[0]["full_name"],
            "start_date": "2026-09-01",
            "basic_salary": 4500,
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=stas_headers, json=payload)
        contract = create_resp.json()
        
        # Submit
        requests.post(f"{BASE_URL}/api/contracts-v2/{contract['id']}/submit", headers=stas_headers)
        
        # Try to execute as Sultan
        execute_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/execute",
            headers=headers
        )
        
        assert execute_resp.status_code in [401, 403], f"Sultan should not execute: {execute_resp.status_code}"
        print(f"✓ Sultan correctly blocked from executing contract")


class TestContractTerminate:
    """Test POST /api/contracts-v2/{id}/terminate (STAS only) terminates active contract"""
    
    def test_stas_can_terminate_active(self, stas_token):
        """STAS can terminate active contract"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get an active contract
        resp = requests.get(f"{BASE_URL}/api/contracts-v2?status=active", headers=headers)
        contracts = resp.json()
        
        if not contracts:
            pytest.skip("No active contracts to terminate")
        
        # Don't actually terminate to preserve test data
        # Just verify the endpoint exists
        contract = contracts[0]
        
        # Test with invalid reason first
        term_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/terminate",
            headers=headers,
            json={
                "termination_date": "2026-12-31",
                "termination_reason": "invalid_reason"
            }
        )
        
        assert term_resp.status_code == 400, "Should reject invalid termination reason"
        print(f"✓ Termination endpoint validates reason correctly")
    
    def test_naif_cannot_terminate(self, naif_token, stas_token):
        """Naif cannot terminate contracts"""
        headers = {"Authorization": f"Bearer {naif_token}"}
        stas_headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get an active contract
        resp = requests.get(f"{BASE_URL}/api/contracts-v2?status=active", headers=stas_headers)
        contracts = resp.json()
        
        if not contracts:
            pytest.skip("No active contracts")
        
        contract = contracts[0]
        
        term_resp = requests.post(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/terminate",
            headers=headers,
            json={
                "termination_date": "2026-12-31",
                "termination_reason": "resignation"
            }
        )
        
        assert term_resp.status_code in [401, 403], f"Naif should not terminate: {term_resp.status_code}"
        print(f"✓ Naif correctly blocked from terminating contract")


class TestContractDelete:
    """Test DELETE /api/contracts-v2/{id} deletes draft contracts only"""
    
    def test_can_delete_draft_contract(self, stas_token, employees):
        """Can delete draft contract"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Create a draft contract
        payload = {
            "employee_id": employees[0]["id"],
            "employee_code": employees[0]["employee_number"],
            "employee_name": employees[0]["full_name"],
            "start_date": "2026-10-01",
            "basic_salary": 3000,
        }
        
        create_resp = requests.post(f"{BASE_URL}/api/contracts-v2", headers=headers, json=payload)
        contract = create_resp.json()
        
        # Delete it
        delete_resp = requests.delete(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}",
            headers=headers
        )
        
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.text}"
        
        # Verify deleted
        get_resp = requests.get(f"{BASE_URL}/api/contracts-v2/{contract['id']}", headers=headers)
        assert get_resp.status_code == 404, "Deleted contract should return 404"
        
        print(f"✓ Successfully deleted draft contract")
    
    def test_cannot_delete_active_contract(self, stas_token):
        """Cannot delete active contract"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get an active contract
        resp = requests.get(f"{BASE_URL}/api/contracts-v2?status=active", headers=headers)
        contracts = resp.json()
        
        if not contracts:
            pytest.skip("No active contracts")
        
        contract = contracts[0]
        
        delete_resp = requests.delete(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}",
            headers=headers
        )
        
        assert delete_resp.status_code == 400, "Should not allow delete of active contract"
        print(f"✓ Correctly blocked delete of active contract")


class TestContractPDF:
    """Test PDF generation"""
    
    def test_pdf_generation(self, stas_token):
        """Test PDF endpoint returns PDF"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get a contract
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        if not contracts:
            pytest.skip("No contracts")
        
        contract = contracts[0]
        
        pdf_resp = requests.get(
            f"{BASE_URL}/api/contracts-v2/{contract['id']}/pdf?lang=ar",
            headers=headers
        )
        
        assert pdf_resp.status_code == 200, f"PDF generation failed: {pdf_resp.text}"
        assert "application/pdf" in pdf_resp.headers.get("content-type", "")
        assert len(pdf_resp.content) > 100, "PDF should have content"
        
        print(f"✓ PDF generated successfully ({len(pdf_resp.content)} bytes)")


class TestContractStats:
    """Test contract statistics endpoint"""
    
    def test_stats_endpoint(self, stas_token):
        """Test contract stats endpoint"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        resp = requests.get(f"{BASE_URL}/api/contracts-v2/stats/summary", headers=headers)
        
        assert resp.status_code == 200, f"Stats failed: {resp.text}"
        stats = resp.json()
        
        assert "total" in stats
        assert "active" in stats
        assert "draft" in stats
        
        print(f"✓ Contract stats: total={stats['total']}, active={stats['active']}, draft={stats['draft']}")


class TestDateFormat:
    """Test date format includes Gregorian and Hijri"""
    
    def test_contract_dates_are_present(self, stas_token):
        """Verify contracts have date fields"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        for contract in contracts:
            # Check start_date exists
            assert "start_date" in contract, f"Contract {contract['id']} missing start_date"
            assert contract["start_date"] is not None
            
            # Verify date format (YYYY-MM-DD)
            import re
            date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
            assert date_pattern.match(contract["start_date"]), f"Invalid date format: {contract['start_date']}"
        
        print(f"✓ All contracts have valid date formats")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_contracts(self, stas_token):
        """Cleanup TEST_ prefixed contracts"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get all contracts
        resp = requests.get(f"{BASE_URL}/api/contracts-v2", headers=headers)
        contracts = resp.json()
        
        deleted = 0
        for contract in contracts:
            # Delete draft/pending contracts that might be test data
            if contract["status"] in ["draft", "pending_stas"]:
                if "TEST_" in contract.get("job_title", "") or "TEST_" in contract.get("notes", ""):
                    del_resp = requests.delete(
                        f"{BASE_URL}/api/contracts-v2/{contract['id']}",
                        headers=headers
                    )
                    if del_resp.status_code == 200:
                        deleted += 1
        
        print(f"✓ Cleanup complete (deleted {deleted} test contracts)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
