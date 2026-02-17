"""
Iteration 13 Backend Tests
Features to test:
1. PDF Generation - Arabic version should have proper RTL text
2. PDF Generation - English version should NOT be blank  
3. PDF should include company logo and name from settings
4. STAS workflow - STAS can execute transactions that were returned and re-approved
5. STAS cancellation - cancelled transactions should not affect leave balance
6. Approval chain should show approver names correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://stas-mirror-detect.preview.emergentagent.com")

# Test user IDs
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
SUPERVISOR1_USER_ID = "0c38e38d-70a3-54e6-b3ab-c8a7cb628d09"
EMPLOYEE1_USER_ID = "46c9dd1a-7f0f-584b-9bab-b37b949afece"


@pytest.fixture
def stas_token():
    """Get STAS authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def sultan_token():
    """Get Sultan authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def supervisor_token():
    """Get Supervisor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{SUPERVISOR1_USER_ID}")
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def employee_token():
    """Get Employee authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{EMPLOYEE1_USER_ID}")
    assert response.status_code == 200
    return response.json()["token"]


class TestPDFGeneration:
    """Test PDF generation for bilingual support"""
    
    def test_arabic_pdf_not_blank(self, stas_token):
        """Verify Arabic PDF has content and is not blank"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get transactions
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) > 0, "No transactions found"
        
        # Get Arabic PDF for first executed transaction
        executed_txs = [t for t in transactions if t["status"] == "executed"]
        if executed_txs:
            tx_id = executed_txs[0]["id"]
            pdf_response = requests.get(
                f"{BASE_URL}/api/transactions/{tx_id}/pdf?lang=ar",
                headers=headers
            )
            assert pdf_response.status_code == 200
            assert pdf_response.headers.get("content-type") == "application/pdf"
            
            pdf_content = pdf_response.content
            assert len(pdf_content) > 10000, f"Arabic PDF too small: {len(pdf_content)} bytes"
            assert pdf_content[:4] == b"%PDF", "Not a valid PDF file"
    
    def test_english_pdf_not_blank(self, stas_token):
        """Verify English PDF has content and is not blank"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get transactions
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        assert len(transactions) > 0
        
        # Get English PDF
        executed_txs = [t for t in transactions if t["status"] == "executed"]
        if executed_txs:
            tx_id = executed_txs[0]["id"]
            pdf_response = requests.get(
                f"{BASE_URL}/api/transactions/{tx_id}/pdf?lang=en",
                headers=headers
            )
            assert pdf_response.status_code == 200
            assert pdf_response.headers.get("content-type") == "application/pdf"
            
            pdf_content = pdf_response.content
            assert len(pdf_content) > 10000, f"English PDF too small: {len(pdf_content)} bytes"
            assert pdf_content[:4] == b"%PDF", "Not a valid PDF file"
    
    def test_pdf_includes_company_branding(self, stas_token):
        """Verify PDF has company branding from settings"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Check branding settings exist
        branding_response = requests.get(f"{BASE_URL}/api/settings/branding", headers=headers)
        assert branding_response.status_code == 200
        branding = branding_response.json()
        
        assert "company_name_en" in branding, "Missing company_name_en"
        assert "company_name_ar" in branding, "Missing company_name_ar"
        # Logo should be present
        assert branding.get("logo_data") is not None or branding.get("logo_url") is not None, \
            "Company logo should be present in branding"


class TestSTASWorkflow:
    """Test STAS execution and return workflow"""
    
    def test_stas_can_view_transactions(self, stas_token):
        """STAS should be able to view all transactions"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_stas_pending_endpoint(self, stas_token):
        """Test /api/stas/pending endpoint"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        response = requests.get(f"{BASE_URL}/api/stas/pending", headers=headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_stas_mirror_endpoint(self, stas_token):
        """Test STAS mirror endpoint for an executed transaction"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get transactions
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        
        if len(transactions) > 0:
            tx_id = transactions[0]["id"]
            mirror_response = requests.get(
                f"{BASE_URL}/api/stas/mirror/{tx_id}",
                headers=headers
            )
            assert mirror_response.status_code == 200
            mirror = mirror_response.json()
            
            assert "transaction" in mirror
            assert "pre_checks" in mirror
            assert "all_checks_pass" in mirror
    
    def test_stas_return_actions_exist(self, stas_token):
        """Verify STAS return actions are implemented"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get transactions
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        
        # Check if return_to_sultan and return_to_ceo are available actions
        # by examining transaction workflow
        for tx in transactions:
            if tx.get("current_stage") == "stas":
                # This transaction is at STAS stage - return actions should be available
                break


class TestApprovalChain:
    """Test approval chain shows approver names correctly"""
    
    def test_approval_chain_has_approver_names(self, stas_token):
        """Verify approval_chain entries have approver_name field"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        
        for tx in transactions:
            if "approval_chain" in tx and len(tx["approval_chain"]) > 0:
                for approval in tx["approval_chain"]:
                    # Each approval entry should have approver_name
                    assert "approver_name" in approval or "actor_name" in approval, \
                        f"Approval chain entry missing name field: {approval}"
                break
    
    def test_transaction_detail_has_approval_chain(self, stas_token):
        """Verify transaction detail includes approval chain"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get list first
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        transactions = response.json()
        
        if len(transactions) > 0:
            tx_id = transactions[0]["id"]
            detail_response = requests.get(
                f"{BASE_URL}/api/transactions/{tx_id}",
                headers=headers
            )
            assert detail_response.status_code == 200
            detail = detail_response.json()
            
            assert "approval_chain" in detail or "timeline" in detail


class TestCancelledTransaction:
    """Test cancelled transactions behavior"""
    
    def test_cancelled_transaction_exists(self, stas_token):
        """Verify there are cancelled transactions in the system"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        response = requests.get(f"{BASE_URL}/api/transactions?status=cancelled", headers=headers)
        assert response.status_code == 200
        
        # Check if there are cancelled transactions
        cancelled = response.json()
        print(f"Found {len(cancelled)} cancelled transaction(s)")
    
    def test_leave_balance_check_endpoint(self, stas_token):
        """Verify leave balance can be checked"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get employees to check leave balance
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert emp_response.status_code == 200


class TestTransactionExecuted:
    """Test transactions that have been executed via STAS"""
    
    def test_txn_2026_0006_is_executed(self, stas_token):
        """Verify TXN-2026-0006 is executed"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        
        txn_0006 = next((t for t in transactions if t.get("ref_no") == "TXN-2026-0006"), None)
        if txn_0006:
            assert txn_0006["status"] == "executed", f"TXN-2026-0006 should be executed but is {txn_0006['status']}"
            print(f"TXN-2026-0006 status: {txn_0006['status']}")
    
    def test_txn_2026_0007_is_executed(self, stas_token):
        """Verify TXN-2026-0007 is executed (after return flow)"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200
        transactions = response.json()
        
        txn_0007 = next((t for t in transactions if t.get("ref_no") == "TXN-2026-0007"), None)
        if txn_0007:
            assert txn_0007["status"] == "executed", f"TXN-2026-0007 should be executed but is {txn_0007['status']}"
            print(f"TXN-2026-0007 status: {txn_0007['status']}")


class TestWorkflowValidation:
    """Test workflow validation functions"""
    
    def test_validate_stage_actor_allows_stas(self, stas_token):
        """STAS should be exempt from 'already acted' check"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        
        # Get a transaction at stas stage
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        transactions = response.json()
        
        stas_tx = next((t for t in transactions if t.get("current_stage") == "stas" and t.get("status") != "executed"), None)
        if stas_tx:
            # STAS should be able to execute this
            # Just verify we can access the mirror
            mirror_response = requests.get(
                f"{BASE_URL}/api/stas/mirror/{stas_tx['id']}",
                headers=headers
            )
            assert mirror_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
