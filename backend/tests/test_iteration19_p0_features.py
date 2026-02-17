"""
Iteration 19 - P0 Features Test
Testing 3 main tasks:
1. Barcode in PDF instead of QR for STAS signature
2. Prevent duplicate execution of STAS transactions
3. Read-only map for employees (red pin = assigned location, blue pins = other locations)

Additional endpoints tested:
- GET /api/stas/settings/map-visibility/public
- GET /api/work-locations
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leave-management-6.preview.emergentagent.com').rstrip('/')


class TestP0FeaturesIteration19:
    """Tests for the 3 P0 features implemented"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for STAS user"""
        # Get all users first
        users_resp = requests.get(f"{BASE_URL}/api/auth/users")
        assert users_resp.status_code == 200, f"Failed to get users: {users_resp.text}"
        users = users_resp.json()
        
        # Find STAS user
        stas_user = next((u for u in users if u.get('role') == 'stas'), None)
        assert stas_user is not None, "STAS user not found"
        
        # Switch to STAS user
        switch_resp = requests.post(f"{BASE_URL}/api/auth/switch/{stas_user['id']}")
        assert switch_resp.status_code == 200, f"Failed to switch to STAS: {switch_resp.text}"
        
        self.stas_token = switch_resp.json()['token']
        self.stas_headers = {"Authorization": f"Bearer {self.stas_token}"}
        
        # Find an employee user
        emp_user = next((u for u in users if u.get('role') == 'employee'), None)
        if emp_user:
            emp_switch = requests.post(f"{BASE_URL}/api/auth/switch/{emp_user['id']}")
            if emp_switch.status_code == 200:
                self.emp_token = emp_switch.json()['token']
                self.emp_headers = {"Authorization": f"Bearer {self.emp_token}"}
            else:
                self.emp_token = None
                self.emp_headers = None
        else:
            self.emp_token = None
            self.emp_headers = None
    
    # ================== Feature 1: Work Locations Endpoint ==================
    
    def test_work_locations_endpoint_returns_data(self):
        """GET /api/work-locations should return all work locations"""
        resp = requests.get(f"{BASE_URL}/api/work-locations", headers=self.stas_headers)
        assert resp.status_code == 200, f"Work locations endpoint failed: {resp.text}"
        
        locations = resp.json()
        assert isinstance(locations, list), "Response should be a list"
        print(f"✓ Work locations endpoint returned {len(locations)} locations")
        
        if len(locations) > 0:
            # Check structure of first location
            loc = locations[0]
            assert 'id' in loc, "Location should have id"
            assert 'name' in loc or 'name_ar' in loc, "Location should have name"
            assert 'latitude' in loc, "Location should have latitude"
            assert 'longitude' in loc, "Location should have longitude"
            print(f"✓ Location structure validated: {loc.get('name', loc.get('name_ar'))}")
    
    # ================== Feature 2: Map Visibility Public Endpoint ==================
    
    def test_map_visibility_public_endpoint_works(self):
        """GET /api/stas/settings/map-visibility/public should be accessible"""
        resp = requests.get(f"{BASE_URL}/api/stas/settings/map-visibility/public", headers=self.stas_headers)
        assert resp.status_code == 200, f"Map visibility public endpoint failed: {resp.text}"
        
        data = resp.json()
        assert 'show_map_to_employees' in data, "Response should have show_map_to_employees field"
        print(f"✓ Map visibility public endpoint works. show_map_to_employees={data['show_map_to_employees']}")
    
    def test_map_visibility_accessible_by_employee(self):
        """Employee should be able to access map visibility endpoint"""
        if not self.emp_headers:
            pytest.skip("No employee user available")
        
        resp = requests.get(f"{BASE_URL}/api/stas/settings/map-visibility/public", headers=self.emp_headers)
        assert resp.status_code == 200, f"Map visibility should be accessible by employee: {resp.text}"
        print(f"✓ Employee can access map visibility endpoint")
    
    # ================== Feature 3: Prevent Duplicate Execution ==================
    
    def test_prevent_duplicate_execution_returns_400(self):
        """
        POST /api/stas/execute/{id} should return 400 if transaction already executed
        """
        # First, get all transactions to find an executed one
        txs_resp = requests.get(f"{BASE_URL}/api/transactions?limit=50", headers=self.stas_headers)
        assert txs_resp.status_code == 200, f"Failed to get transactions: {txs_resp.text}"
        
        transactions = txs_resp.json()
        executed_tx = next((t for t in transactions if t.get('status') == 'executed'), None)
        
        if not executed_tx:
            # Try to find any transaction and execute it first, then test duplicate
            pytest.skip("No executed transaction found to test duplicate execution prevention")
        
        # Try to execute an already executed transaction
        exec_resp = requests.post(f"{BASE_URL}/api/stas/execute/{executed_tx['id']}", headers=self.stas_headers)
        
        assert exec_resp.status_code == 400, f"Expected 400 for duplicate execution, got {exec_resp.status_code}: {exec_resp.text}"
        
        error_data = exec_resp.json().get('detail', {})
        if isinstance(error_data, dict):
            assert error_data.get('error') == 'ALREADY_EXECUTED', f"Expected ALREADY_EXECUTED error, got: {error_data}"
            print(f"✓ Duplicate execution prevented with correct error: {error_data.get('message_ar')}")
        else:
            print(f"✓ Duplicate execution prevented with error: {error_data}")
    
    # ================== Feature 4: PDF Generation with Barcode ==================
    
    def test_pdf_generation_endpoint_works(self):
        """
        GET /api/transactions/{id}/pdf should generate PDF
        Note: We cannot verify barcode vs QR from API response, but we verify endpoint works
        """
        # Get an executed transaction for PDF
        txs_resp = requests.get(f"{BASE_URL}/api/transactions?limit=50", headers=self.stas_headers)
        assert txs_resp.status_code == 200, f"Failed to get transactions: {txs_resp.text}"
        
        transactions = txs_resp.json()
        executed_tx = next((t for t in transactions if t.get('status') == 'executed'), None)
        
        if not executed_tx:
            # Try pending transactions
            pending_tx = next((t for t in transactions), None)
            if not pending_tx:
                pytest.skip("No transaction found to test PDF generation")
            test_tx = pending_tx
        else:
            test_tx = executed_tx
        
        # Generate PDF
        pdf_resp = requests.get(f"{BASE_URL}/api/transactions/{test_tx['id']}/pdf", headers=self.stas_headers)
        assert pdf_resp.status_code == 200, f"PDF generation failed: {pdf_resp.text}"
        
        # Check content type
        content_type = pdf_resp.headers.get('content-type', '')
        assert 'pdf' in content_type.lower(), f"Expected PDF content type, got: {content_type}"
        
        # Check PDF has content
        assert len(pdf_resp.content) > 1000, "PDF content should be substantial"
        print(f"✓ PDF generated successfully for {test_tx['ref_no']}, size: {len(pdf_resp.content)} bytes")
    
    # ================== Feature 5: STAS Mirror Data ==================
    
    def test_stas_pending_endpoint(self):
        """GET /api/stas/pending should return pending transactions for STAS"""
        resp = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.stas_headers)
        assert resp.status_code == 200, f"STAS pending endpoint failed: {resp.text}"
        
        pending = resp.json()
        assert isinstance(pending, list), "Response should be a list"
        print(f"✓ STAS pending endpoint returned {len(pending)} transactions")
    
    def test_stas_mirror_endpoint(self):
        """GET /api/stas/mirror/{id} should return mirror data"""
        # Get pending transactions
        pending_resp = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.stas_headers)
        assert pending_resp.status_code == 200
        
        pending = pending_resp.json()
        if len(pending) == 0:
            # Try to get any transaction
            txs_resp = requests.get(f"{BASE_URL}/api/transactions?limit=10", headers=self.stas_headers)
            txs = txs_resp.json()
            if len(txs) == 0:
                pytest.skip("No transactions available to test mirror")
            test_tx = txs[0]
        else:
            test_tx = pending[0]
        
        # Get mirror data
        mirror_resp = requests.get(f"{BASE_URL}/api/stas/mirror/{test_tx['id']}", headers=self.stas_headers)
        assert mirror_resp.status_code == 200, f"Mirror endpoint failed: {mirror_resp.text}"
        
        mirror = mirror_resp.json()
        assert 'transaction' in mirror, "Mirror should have transaction data"
        assert 'pre_checks' in mirror, "Mirror should have pre_checks"
        print(f"✓ STAS mirror endpoint works for {test_tx['ref_no']}")
    
    # ================== Integration Test: Full Execution Flow ==================
    
    def test_execution_flow_and_duplicate_prevention(self):
        """
        Integration test: Create transaction, execute it, verify duplicate is blocked
        """
        # Get pending transactions
        pending_resp = requests.get(f"{BASE_URL}/api/stas/pending", headers=self.stas_headers)
        assert pending_resp.status_code == 200
        
        pending = pending_resp.json()
        
        # Find a transaction ready for execution (stas stage, not executed)
        executable_tx = next((t for t in pending if t.get('current_stage') == 'stas' and t.get('status') != 'executed'), None)
        
        if not executable_tx:
            print("⚠ No executable transaction found for full flow test")
            pytest.skip("No executable transaction available")
            return
        
        # Execute the transaction
        exec_resp = requests.post(f"{BASE_URL}/api/stas/execute/{executable_tx['id']}", headers=self.stas_headers)
        
        if exec_resp.status_code == 400:
            # Check if it's because of failed pre-checks
            error = exec_resp.json().get('detail', {})
            if isinstance(error, dict) and error.get('error') == 'EXECUTION_BLOCKED':
                print(f"⚠ Execution blocked due to failed pre-checks: {error.get('failed_checks')}")
                pytest.skip("Transaction blocked by pre-checks")
                return
        
        assert exec_resp.status_code == 200, f"Initial execution failed: {exec_resp.text}"
        exec_data = exec_resp.json()
        print(f"✓ Transaction {exec_data.get('ref_no')} executed successfully")
        
        # Now try to execute again - should fail with 400
        duplicate_resp = requests.post(f"{BASE_URL}/api/stas/execute/{executable_tx['id']}", headers=self.stas_headers)
        assert duplicate_resp.status_code == 400, f"Duplicate execution should return 400, got: {duplicate_resp.status_code}"
        
        error_data = duplicate_resp.json().get('detail', {})
        if isinstance(error_data, dict):
            assert error_data.get('error') == 'ALREADY_EXECUTED', f"Expected ALREADY_EXECUTED error"
            print(f"✓ Duplicate execution correctly prevented: {error_data.get('message_ar')}")
        else:
            print(f"✓ Duplicate execution prevented")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
