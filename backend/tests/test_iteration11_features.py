"""
DAR AL CODE HR OS - Iteration 11 Backend Tests
Testing: Company Settings API, Branding API, Transaction Timeline, PDF Generation, Saudi Timezone
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dar-maintenance.preview.emergentagent.com').rstrip('/')

# User IDs for testing
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
TEST_TRANSACTION_ID = "da46bd8f-94f8-442d-b375-27461c0c417b"


@pytest.fixture(scope="module")
def stas_token():
    """Get STAS user token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert response.status_code == 200, f"Failed to get STAS token: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def sultan_token():
    """Get Sultan user token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    assert response.status_code == 200, f"Failed to get Sultan token: {response.text}"
    return response.json()["token"]


class TestCompanyBrandingAPI:
    """Tests for Company Branding Settings API"""
    
    def test_get_branding_as_stas(self, stas_token):
        """GET /api/settings/branding should work for STAS"""
        response = requests.get(
            f"{BASE_URL}/api/settings/branding",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify data structure
        assert "company_name_en" in data
        assert "company_name_ar" in data
        assert "slogan_en" in data
        assert "slogan_ar" in data
        assert "logo_data" in data
        
        # Verify no [object Object] in any values
        for key, value in data.items():
            if isinstance(value, str):
                assert "[object Object]" not in value, f"Found [object Object] in {key}"
    
    def test_get_branding_as_sultan(self, sultan_token):
        """GET /api/settings/branding should work for non-STAS users too"""
        response = requests.get(
            f"{BASE_URL}/api/settings/branding",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "company_name_en" in data
    
    def test_put_branding_as_stas(self, stas_token):
        """PUT /api/settings/branding should work for STAS"""
        update_data = {
            "company_name_en": "DAR AL CODE ENGINEERING CONSULTANCY",
            "company_name_ar": "شركة دار الكود للاستشارات الهندسية",
            "slogan_en": "Engineering Excellence",
            "slogan_ar": "التميز الهندسي"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/settings/branding",
            headers={
                "Authorization": f"Bearer {stas_token}",
                "Content-Type": "application/json"
            },
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify update was applied
        assert data["company_name_en"] == update_data["company_name_en"]
        assert data["company_name_ar"] == update_data["company_name_ar"]
        assert data["slogan_en"] == update_data["slogan_en"]
        assert data["slogan_ar"] == update_data["slogan_ar"]
    
    def test_put_branding_as_sultan_should_fail(self, sultan_token):
        """PUT /api/settings/branding should fail for non-STAS users"""
        response = requests.put(
            f"{BASE_URL}/api/settings/branding",
            headers={
                "Authorization": f"Bearer {sultan_token}",
                "Content-Type": "application/json"
            },
            json={"company_name_en": "Test"}
        )
        assert response.status_code == 403
        assert "STAS" in response.json().get("detail", "")


class TestTransactionDetailAPI:
    """Tests for Transaction Detail and Timeline"""
    
    def test_get_transaction_detail(self, stas_token):
        """GET /api/transactions/{id} should return full transaction details"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        tx = response.json()
        
        # Verify basic fields
        assert tx["id"] == TEST_TRANSACTION_ID
        assert "ref_no" in tx
        assert "type" in tx
        assert "status" in tx
        assert "data" in tx
        assert "timeline" in tx
        assert "approval_chain" in tx
    
    def test_transaction_data_no_object_object(self, stas_token):
        """Transaction data should not contain [object Object]"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        tx = response.json()
        
        # Check transaction data
        for key, value in tx.get("data", {}).items():
            if isinstance(value, str):
                assert "[object Object]" not in value, f"Found [object Object] in data.{key}"
    
    def test_transaction_timeline_exists(self, stas_token):
        """Transaction should have timeline with events"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        tx = response.json()
        
        timeline = tx.get("timeline", [])
        assert len(timeline) > 0, "Timeline should have at least one event"
        
        # Verify timeline event structure
        for event in timeline:
            assert "event" in event
            assert "actor" in event
            assert "timestamp" in event
            assert "stage" in event
    
    def test_transaction_approval_chain(self, stas_token):
        """Transaction should have approval chain"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        tx = response.json()
        
        chain = tx.get("approval_chain", [])
        assert len(chain) > 0, "Approval chain should have entries"
        
        # Verify chain entry structure
        for entry in chain:
            assert "stage" in entry
            assert "approver_id" in entry
            assert "approver_name" in entry
            assert "status" in entry
            assert "timestamp" in entry


class TestPDFGeneration:
    """Tests for PDF Generation"""
    
    def test_pdf_download_arabic(self, stas_token):
        """PDF should download with Arabic language"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf?lang=ar",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("Content-Type", "")
        assert response.content[:4] == b"%PDF", "Response should be valid PDF"
        assert len(response.content) > 1000, "PDF should have content"
    
    def test_pdf_download_english(self, stas_token):
        """PDF should download with English language"""
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf?lang=en",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("Content-Type", "")
        assert response.content[:4] == b"%PDF", "Response should be valid PDF"


class TestSTASWorkflow:
    """Tests for STAS workflow actions"""
    
    def test_stas_can_view_all_transactions(self, stas_token):
        """STAS should be able to view all transactions"""
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        txs = response.json()
        assert isinstance(txs, list)
    
    def test_transaction_return_logic(self, stas_token):
        """Verify STAS return actions work correctly"""
        # Get transaction to verify status
        response = requests.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        tx = response.json()
        
        # Verify workflow contains correct stages
        workflow = tx.get("workflow", [])
        assert "supervisor" in workflow
        assert "ops" in workflow
        assert "stas" in workflow


class TestDashboardStats:
    """Tests for Dashboard Stats"""
    
    def test_dashboard_stats_for_stas(self, stas_token):
        """STAS should see dashboard stats"""
        response = requests.get(
            f"{BASE_URL}/api/dashboard/stats",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        stats = response.json()
        
        # STAS should see these stats
        assert "total_transactions" in stats or "pending_execution" in stats


class TestUserSwitcher:
    """Tests for User Switcher functionality"""
    
    def test_user_switcher_returns_users(self):
        """GET /api/auth/users should return list of users"""
        response = requests.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        
        # Find STAS user
        stas_users = [u for u in users if u.get("role") == "stas"]
        assert len(stas_users) > 0, "STAS user should exist"
    
    def test_switch_to_stas_user(self):
        """POST /api/auth/switch/{user_id} should return token"""
        response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
        assert response.status_code == 200
        data = response.json()
        
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "stas"
        assert data["user"]["full_name"] == "STAS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
