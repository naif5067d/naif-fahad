"""
Test Admin Custody (Financial Custody) System - Iteration 35
Tests: /api/admin-custody endpoints for the new custody management system
Users: sultan, salah (accountant), stas
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLogin:
    """Test login for all custody users"""
    
    def test_sultan_login(self):
        """Sultan can login with password 123456"""
        response = requests.post(f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": "123456"})
        assert response.status_code == 200, f"Sultan login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "sultan"
        print("✓ Sultan login successful")
    
    def test_salah_login(self):
        """Salah (accountant) can login with password 123456"""
        response = requests.post(f"{BASE_URL}/api/auth/login",
            json={"username": "salah", "password": "123456"})
        assert response.status_code == 200, f"Salah login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "salah"
        print("✓ Salah login successful")
    
    def test_stas_login(self):
        """STAS can login with password 123456"""
        response = requests.post(f"{BASE_URL}/api/auth/login",
            json={"username": "stas", "password": "123456"})
        assert response.status_code == 200, f"STAS login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "stas"
        print("✓ STAS login successful")


@pytest.fixture(scope="module")
def sultan_token():
    """Get Sultan auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login",
        json={"username": "sultan", "password": "123456"})
    assert resp.status_code == 200, "Sultan login failed"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def salah_token():
    """Get Salah auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login",
        json={"username": "salah", "password": "123456"})
    assert resp.status_code == 200, "Salah login failed"
    return resp.json()["token"]


@pytest.fixture(scope="module")
def stas_token():
    """Get STAS auth token"""
    resp = requests.post(f"{BASE_URL}/api/auth/login",
        json={"username": "stas", "password": "123456"})
    assert resp.status_code == 200, "STAS login failed"
    return resp.json()["token"]


class TestExpenseCodes:
    """Test expense codes API (60 codes)"""
    
    def test_get_all_codes(self, sultan_token):
        """GET /api/admin-custody/codes - Get all 60 codes"""
        response = requests.get(f"{BASE_URL}/api/admin-custody/codes",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "codes" in data
        assert data["total"] >= 60
        # Check code 5 exists
        code5 = next((c for c in data["codes"] if c["code"] == 5), None)
        assert code5 is not None
        assert code5["name_ar"] == "انتقالات"
        print(f"✓ Retrieved {data['total']} expense codes")
    
    def test_get_specific_code(self, sultan_token):
        """GET /api/admin-custody/codes/{code} - Get specific code"""
        response = requests.get(f"{BASE_URL}/api/admin-custody/codes/5",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["found"] == True
        assert data["code"]["name_ar"] == "انتقالات"
        assert data["code"]["name_en"] == "Transportation"
        print("✓ Code 5 lookup: انتقالات (Transportation)")
    
    def test_get_nonexistent_code(self, sultan_token):
        """GET /api/admin-custody/codes/{code} - Non-existent code returns is_new"""
        response = requests.get(f"{BASE_URL}/api/admin-custody/codes/999",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == False
        assert data["code"]["is_new"] == True
        print("✓ Non-existent code 999 marked as new")


class TestCustodyCreation:
    """Test custody creation"""
    
    def test_sultan_create_custody(self, sultan_token):
        """POST /api/admin-custody/create - Sultan creates custody"""
        response = requests.post(f"{BASE_URL}/api/admin-custody/create",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"amount": 2000, "notes": "TEST_pytest_custody"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["custody"]["total_amount"] == 2000
        assert data["custody"]["budget"] == 2000  # No surplus added
        assert data["custody"]["remaining"] == 2000
        assert data["custody"]["status"] == "open"
        print(f"✓ Created custody #{data['custody']['custody_number']}")
        return data["custody"]["id"]
    
    def test_salah_cannot_create_custody(self, salah_token):
        """Salah (accountant) cannot create custody - only audit"""
        response = requests.post(f"{BASE_URL}/api/admin-custody/create",
            headers={"Authorization": f"Bearer {salah_token}"},
            json={"amount": 1000, "notes": "TEST_salah_attempt"})
        assert response.status_code == 403, f"Salah should be denied: {response.text}"
        print("✓ Salah correctly denied from creating custody")


class TestCustodySummary:
    """Test summary endpoint"""
    
    def test_get_summary(self, sultan_token):
        """GET /api/admin-custody/summary - Get statistics"""
        response = requests.get(f"{BASE_URL}/api/admin-custody/summary",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total_custodies" in data
        assert "open" in data
        assert "pending_audit" in data
        assert "approved" in data
        assert "executed" in data
        assert "closed" in data
        assert "total_budget" in data
        assert "total_spent" in data
        assert "total_remaining" in data
        print(f"✓ Summary: {data['total_custodies']} custodies, "
              f"budget={data['total_budget']}, spent={data['total_spent']}")


class TestFullWorkflow:
    """Test complete custody workflow"""
    
    @pytest.fixture(scope="class")
    def workflow_custody(self, sultan_token):
        """Create custody for workflow test"""
        resp = requests.post(f"{BASE_URL}/api/admin-custody/create",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"amount": 5000, "notes": "TEST_workflow_custody"})
        assert resp.status_code == 200
        return resp.json()["custody"]
    
    def test_01_add_expense(self, sultan_token, workflow_custody):
        """POST /api/admin-custody/{id}/expense - Add expense"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/expense",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"code": 5, "description": "TEST_transportation", "amount": 500})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["expense"]["code"] == 5
        assert data["expense"]["code_name_ar"] == "انتقالات"
        assert data["custody_update"]["spent"] == 500
        assert data["custody_update"]["remaining"] == 4500
        print("✓ Added expense: 500 SAR for code 5 (انتقالات)")
    
    def test_02_add_second_expense(self, sultan_token, workflow_custody):
        """Add second expense"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/expense",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"code": 15, "description": "TEST_fuel", "amount": 300})
        assert response.status_code == 200
        data = response.json()
        assert data["custody_update"]["spent"] == 800  # 500 + 300
        assert data["custody_update"]["remaining"] == 4200
        print("✓ Added second expense: 300 SAR for code 15 (محروقات)")
    
    def test_03_submit_for_audit(self, sultan_token, workflow_custody):
        """POST /api/admin-custody/{id}/submit-audit - Submit for audit"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/submit-audit",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "pending_audit"
        print("✓ Submitted for audit - status: pending_audit")
    
    def test_04_salah_audits(self, salah_token, workflow_custody):
        """POST /api/admin-custody/{id}/audit - Salah approves"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/audit",
            headers={"Authorization": f"Bearer {salah_token}"},
            json={"action": "approve", "comment": "TEST_approved by Salah"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "approved"
        print("✓ Salah approved audit - status: approved")
    
    def test_05_stas_executes(self, stas_token, workflow_custody):
        """POST /api/admin-custody/{id}/execute - STAS executes"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/execute",
            headers={"Authorization": f"Bearer {stas_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "executed"
        assert data["remaining"] == 4200
        print(f"✓ STAS executed - remaining: {data['remaining']} SAR")
    
    def test_06_close_custody(self, stas_token, workflow_custody):
        """POST /api/admin-custody/{id}/close - Close custody"""
        custody_id = workflow_custody["id"]
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/close",
            headers={"Authorization": f"Bearer {stas_token}"})
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert data["status"] == "closed"
        assert data["surplus"] == 4200
        print(f"✓ Custody closed - surplus: {data['surplus']} SAR will be carried forward")


class TestDeleteExpense:
    """Test expense deletion"""
    
    def test_delete_expense(self, sultan_token):
        """DELETE /api/admin-custody/{id}/expense/{exp_id} - Cancel expense"""
        # Create new custody
        create_resp = requests.post(f"{BASE_URL}/api/admin-custody/create",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"amount": 1000, "notes": "TEST_delete_expense"})
        custody_id = create_resp.json()["custody"]["id"]
        
        # Add expense
        exp_resp = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/expense",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"code": 1, "description": "TEST_to_delete", "amount": 200})
        expense_id = exp_resp.json()["expense"]["id"]
        
        # Delete expense
        del_resp = requests.delete(
            f"{BASE_URL}/api/admin-custody/{custody_id}/expense/{expense_id}",
            headers={"Authorization": f"Bearer {sultan_token}"})
        assert del_resp.status_code == 200, f"Failed: {del_resp.text}"
        data = del_resp.json()
        assert data["success"] == True
        assert data["custody_update"]["spent"] == 0  # Back to 0
        print("✓ Expense deleted successfully")


class TestAuditReject:
    """Test audit rejection flow"""
    
    def test_salah_can_reject_audit(self, sultan_token, salah_token):
        """Salah can reject audit - returns custody to open"""
        # Create custody with expense
        create_resp = requests.post(f"{BASE_URL}/api/admin-custody/create",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"amount": 1000, "notes": "TEST_rejection"})
        custody_id = create_resp.json()["custody"]["id"]
        
        requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/expense",
            headers={"Authorization": f"Bearer {sultan_token}"},
            json={"code": 1, "description": "TEST", "amount": 100})
        
        requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/submit-audit",
            headers={"Authorization": f"Bearer {sultan_token}"})
        
        # Salah rejects
        response = requests.post(f"{BASE_URL}/api/admin-custody/{custody_id}/audit",
            headers={"Authorization": f"Bearer {salah_token}"},
            json={"action": "reject", "comment": "Needs corrections"})
        assert response.status_code == 200
        assert response.json()["status"] == "open"  # Returns to open
        print("✓ Salah rejected audit - custody returned to open status")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
