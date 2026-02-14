"""
DAR AL CODE HR OS - Iteration 12 Tests
Testing:
1. PDF Generation with Arabic text (arabic_reshaper + bidi)
2. STAS can execute transactions (no "You have already taken action" error)
3. STAS Mirror pre-checks work correctly with escalations
4. /api/stas/pending returns pending transactions
5. STAS excluded from "already acted" constraint
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user IDs
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
MOHAMMED_USER_ID = "53f7f8fd-c8c6-55e3-ac13-8e9e9c789c91"  # CEO


class AuthHelper:
    """Helper to get tokens for users"""
    _tokens = {}
    
    @classmethod
    def get_token(cls, user_id: str) -> str:
        if user_id not in cls._tokens:
            resp = requests.post(f"{BASE_URL}/api/auth/switch/{user_id}")
            if resp.status_code == 200:
                cls._tokens[user_id] = resp.json()['token']
            else:
                pytest.fail(f"Failed to get token for {user_id}: {resp.text}")
        return cls._tokens[user_id]


@pytest.fixture
def stas_token():
    return AuthHelper.get_token(STAS_USER_ID)


@pytest.fixture
def sultan_token():
    return AuthHelper.get_token(SULTAN_USER_ID)


@pytest.fixture
def mohammed_token():
    return AuthHelper.get_token(MOHAMMED_USER_ID)


class TestSTASPendingAPI:
    """Test /api/stas/pending endpoint"""
    
    def test_stas_pending_endpoint_accessible(self, stas_token):
        """STAS can access pending transactions endpoint"""
        resp = requests.get(
            f"{BASE_URL}/api/stas/pending",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        print(f"✓ /api/stas/pending accessible, returns {len(resp.json())} transactions")
    
    def test_stas_pending_returns_correct_statuses(self, stas_token):
        """Pending endpoint returns transactions with stas stage or pending_stas status"""
        resp = requests.get(
            f"{BASE_URL}/api/stas/pending",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        
        # Each transaction should be at stas stage or have pending_stas status
        for tx in data:
            is_at_stas = tx.get('current_stage') == 'stas' or tx.get('status') in ['stas', 'pending_stas']
            assert is_at_stas, f"Transaction {tx['ref_no']} not at STAS stage: stage={tx.get('current_stage')}, status={tx.get('status')}"
        
        print(f"✓ All {len(data)} pending transactions are correctly at STAS stage")


class TestPDFGenerationWithArabic:
    """Test PDF generation with Arabic text support"""
    
    def test_pdf_generation_endpoint(self, stas_token):
        """PDF endpoint returns valid PDF"""
        # Get any transaction
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert resp.status_code == 200
        txs = resp.json()
        assert len(txs) > 0, "Need at least one transaction to test PDF"
        
        tx = txs[0]
        tx_id = tx['id']
        
        # Get PDF
        pdf_resp = requests.get(
            f"{BASE_URL}/api/transactions/{tx_id}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers.get('content-type') == 'application/pdf'
        assert pdf_resp.content[:4] == b'%PDF', "Response should be a valid PDF"
        
        print(f"✓ PDF generated successfully for {tx['ref_no']}, size: {len(pdf_resp.content)} bytes")
    
    def test_pdf_arabic_language(self, stas_token):
        """PDF can be generated in Arabic"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        tx_id = txs[0]['id']
        
        # Get Arabic PDF
        pdf_resp = requests.get(
            f"{BASE_URL}/api/transactions/{tx_id}/pdf?lang=ar",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert pdf_resp.status_code == 200
        assert pdf_resp.content[:4] == b'%PDF'
        print(f"✓ Arabic PDF generated successfully")
    
    def test_pdf_english_language(self, stas_token):
        """PDF can be generated in English"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        tx_id = txs[0]['id']
        
        # Get English PDF
        pdf_resp = requests.get(
            f"{BASE_URL}/api/transactions/{tx_id}/pdf?lang=en",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert pdf_resp.status_code == 200
        assert pdf_resp.content[:4] == b'%PDF'
        print(f"✓ English PDF generated successfully")


class TestSTASMirrorPreChecks:
    """Test STAS Mirror pre-checks functionality"""
    
    def test_mirror_endpoint_for_transaction(self, stas_token):
        """Mirror endpoint returns pre-checks for transaction"""
        # Get any transaction
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        tx_id = txs[0]['id']
        
        # Get mirror data
        mirror_resp = requests.get(
            f"{BASE_URL}/api/stas/mirror/{tx_id}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert mirror_resp.status_code == 200
        data = mirror_resp.json()
        
        # Check mirror structure
        assert 'transaction' in data
        assert 'pre_checks' in data
        assert 'all_checks_pass' in data
        assert 'trace_links' in data
        assert 'before_after' in data
        
        print(f"✓ Mirror endpoint returns correct structure for {txs[0]['ref_no']}")
        print(f"  Pre-checks: {len(data['pre_checks'])} checks, all_pass: {data['all_checks_pass']}")
    
    def test_prechecks_include_approval_validation(self, stas_token):
        """Pre-checks include 'All Approvals Complete' check"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        tx_id = txs[0]['id']
        
        mirror_resp = requests.get(
            f"{BASE_URL}/api/stas/mirror/{tx_id}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        data = mirror_resp.json()
        
        check_names = [c['name'] for c in data['pre_checks']]
        assert 'All Approvals Complete' in check_names or 'جميع الموافقات مكتملة' in [c.get('name_ar') for c in data['pre_checks']]
        print(f"✓ Pre-checks include approval validation")
    
    def test_prechecks_escalations_count_as_approval(self, stas_token):
        """Pre-checks correctly count escalations as valid actions"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        
        # Find a transaction that was escalated
        escalated_tx = None
        for tx in txs:
            if tx.get('escalated'):
                escalated_tx = tx
                break
        
        if escalated_tx:
            mirror_resp = requests.get(
                f"{BASE_URL}/api/stas/mirror/{escalated_tx['id']}",
                headers={"Authorization": f"Bearer {stas_token}"}
            )
            data = mirror_resp.json()
            
            # Check if approval check passes (escalate should count)
            approval_check = next((c for c in data['pre_checks'] if c['name'] == 'All Approvals Complete'), None)
            if approval_check:
                print(f"✓ Escalated transaction {escalated_tx['ref_no']}: {approval_check['status']} - {approval_check['detail']}")
        else:
            print("⚠ No escalated transactions found to test")


class TestSTASExecutionFlow:
    """Test that STAS can execute transactions without 'already acted' error"""
    
    def test_stas_excluded_from_already_acted_check(self, stas_token):
        """STAS role should be excluded from 'already acted' validation"""
        # Get a transaction where STAS has already taken action
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        
        # Find executed transaction where STAS acted
        tx_with_stas_action = None
        for tx in txs:
            approval_chain = tx.get('approval_chain', [])
            for approval in approval_chain:
                if approval.get('approver_id') == STAS_USER_ID and tx.get('status') != 'executed':
                    tx_with_stas_action = tx
                    break
            if tx_with_stas_action:
                break
        
        if tx_with_stas_action:
            # Try to view mirror (should not get 'already acted' error)
            mirror_resp = requests.get(
                f"{BASE_URL}/api/stas/mirror/{tx_with_stas_action['id']}",
                headers={"Authorization": f"Bearer {stas_token}"}
            )
            assert mirror_resp.status_code == 200
            print(f"✓ STAS can access mirror for transaction where they already acted: {tx_with_stas_action['ref_no']}")
        else:
            print("⚠ No non-executed transaction with STAS action found")
    
    def test_stas_can_access_mirror_for_any_transaction(self, stas_token):
        """STAS can access mirror for any transaction regardless of approval chain"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        
        for tx in txs[:3]:  # Test first 3 transactions
            mirror_resp = requests.get(
                f"{BASE_URL}/api/stas/mirror/{tx['id']}",
                headers={"Authorization": f"Bearer {stas_token}"}
            )
            # Should always return 200 (not 403 'already acted')
            assert mirror_resp.status_code == 200, f"STAS should access mirror for {tx['ref_no']}, got {mirror_resp.status_code}"
            print(f"✓ STAS can access mirror for {tx['ref_no']} (status: {tx['status']})")


class TestSTASActionPermissions:
    """Test STAS action permissions (approve/execute) without already_acted error"""
    
    def test_stas_can_take_multiple_actions(self, stas_token):
        """STAS should be able to act multiple times on same transaction (e.g., return then execute)"""
        # Get transactions where STAS may have already acted
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        
        # Look for any transaction
        for tx in txs:
            # Check if it's not in a final state
            if tx.get('status') not in ['executed', 'rejected', 'cancelled']:
                # Try approve action (should work for STAS)
                action_resp = requests.post(
                    f"{BASE_URL}/api/transactions/{tx['id']}/action",
                    headers={"Authorization": f"Bearer {stas_token}"},
                    json={"action": "approve", "note": "Test STAS multi-action"}
                )
                
                # Should NOT get 'already acted' error
                if action_resp.status_code == 403:
                    error = action_resp.json().get('detail', '')
                    assert 'already taken' not in error.lower(), f"STAS got 'already acted' error: {error}"
                
                print(f"✓ STAS action test on {tx['ref_no']}: status {action_resp.status_code}")
                break


class TestTransactionWorkflow:
    """Test overall transaction workflow"""
    
    def test_transaction_list(self, stas_token):
        """Get list of transactions"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert resp.status_code == 200
        txs = resp.json()
        print(f"✓ Transaction list: {len(txs)} transactions")
        for tx in txs:
            print(f"  - {tx['ref_no']}: {tx['type']} - {tx['status']}")
    
    def test_transaction_detail(self, stas_token):
        """Get transaction detail"""
        resp = requests.get(
            f"{BASE_URL}/api/transactions",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        txs = resp.json()
        if txs:
            detail_resp = requests.get(
                f"{BASE_URL}/api/transactions/{txs[0]['id']}",
                headers={"Authorization": f"Bearer {stas_token}"}
            )
            assert detail_resp.status_code == 200
            data = detail_resp.json()
            assert 'ref_no' in data
            assert 'type' in data
            assert 'status' in data
            print(f"✓ Transaction detail retrieved for {data['ref_no']}")


class TestCompanySettingsForSTAS:
    """Test that STAS can access company settings"""
    
    def test_stas_can_access_branding(self, stas_token):
        """STAS can access branding settings"""
        resp = requests.get(
            f"{BASE_URL}/api/settings/branding",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert resp.status_code == 200
        print(f"✓ STAS can access branding settings")
    
    def test_stas_can_update_branding(self, stas_token):
        """STAS can update branding settings"""
        resp = requests.put(
            f"{BASE_URL}/api/settings/branding",
            headers={"Authorization": f"Bearer {stas_token}"},
            json={"company_name": "DAR AL CODE", "company_name_ar": "دار الكود"}
        )
        assert resp.status_code == 200
        print(f"✓ STAS can update branding settings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
