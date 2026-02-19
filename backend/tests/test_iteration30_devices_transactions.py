"""
Iteration 30 - Device Management & Transaction Delete Testing
============================================================

Tests:
1. DELETE /api/transactions/{id} - STAS can only delete own transactions
2. Device APIs: /api/devices/all, /api/devices/pending
3. Device actions: /api/devices/{id}/approve, /api/devices/{id}/block
4. Account block/unblock: /api/devices/account/{employee_id}/block, /api/devices/account/{employee_id}/unblock
5. Security logs: /api/devices/security-logs
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test user IDs
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
EMPLOYEE_ID_001 = "EMP-001"  # Sultan's employee record
EMPLOYEE_ID_002 = "EMP-002"  # Ahmad's employee record


@pytest.fixture(scope="module")
def stas_token():
    """Get STAS user token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert response.status_code == 200, f"Failed to switch to STAS: {response.text}"
    data = response.json()
    return data.get('token')


@pytest.fixture(scope="module")
def sultan_token():
    """Get Sultan user token (non-STAS user)"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    assert response.status_code == 200, f"Failed to switch to Sultan: {response.text}"
    data = response.json()
    return data.get('token')


@pytest.fixture(scope="module")
def stas_headers(stas_token):
    """Headers with STAS auth token"""
    return {
        "Authorization": f"Bearer {stas_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def sultan_headers(sultan_token):
    """Headers with Sultan auth token"""
    return {
        "Authorization": f"Bearer {sultan_token}",
        "Content-Type": "application/json"
    }


class TestDeviceAPIs:
    """Test device management APIs - requires STAS role"""
    
    def test_get_all_devices(self, stas_headers):
        """GET /api/devices/all - Should return list of all devices"""
        response = requests.get(f"{BASE_URL}/api/devices/all", headers=stas_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        # May be empty if no devices registered
        print(f"Total devices: {len(data)}")
    
    def test_get_pending_devices(self, stas_headers):
        """GET /api/devices/pending - Should return pending devices only"""
        response = requests.get(f"{BASE_URL}/api/devices/pending", headers=stas_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        # All returned devices should have status 'pending'
        for device in data:
            assert device.get('status') == 'pending', f"Device {device.get('id')} should be pending"
        print(f"Pending devices: {len(data)}")
    
    def test_get_devices_requires_stas_role(self, sultan_headers):
        """GET /api/devices/all - Should reject non-STAS users"""
        response = requests.get(f"{BASE_URL}/api/devices/all", headers=sultan_headers)
        assert response.status_code == 403, "Should reject non-STAS users"


class TestAccountBlockAPIs:
    """Test account block/unblock APIs"""
    
    def test_get_account_status(self, stas_headers):
        """GET /api/devices/account/{employee_id}/status - Check account status"""
        response = requests.get(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/status",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert 'is_blocked' in data, "Should return is_blocked field"
    
    def test_block_account(self, stas_headers):
        """POST /api/devices/account/{employee_id}/block - Block an account"""
        response = requests.post(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/block",
            headers=stas_headers,
            json={"reason": "Test block for iteration 30"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        assert 'message_ar' in data
        
        # Verify account is blocked
        status_response = requests.get(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/status",
            headers=stas_headers
        )
        status_data = status_response.json()
        assert status_data.get('is_blocked') == True, "Account should be blocked"
        assert status_data.get('reason') == "Test block for iteration 30"
    
    def test_unblock_account(self, stas_headers):
        """POST /api/devices/account/{employee_id}/unblock - Unblock an account"""
        response = requests.post(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/unblock",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == True
        
        # Verify account is unblocked
        status_response = requests.get(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/status",
            headers=stas_headers
        )
        status_data = status_response.json()
        assert status_data.get('is_blocked') == False, "Account should be unblocked"
    
    def test_cannot_block_admin_account(self, stas_headers):
        """POST /api/devices/account/EMP-STAS/block - Cannot block STAS account"""
        response = requests.post(
            f"{BASE_URL}/api/devices/account/EMP-STAS/block",
            headers=stas_headers,
            json={"reason": "Test"}
        )
        assert response.status_code == 403, "Should not allow blocking admin accounts"
    
    def test_block_requires_stas_role(self, sultan_headers):
        """POST /api/devices/account/{employee_id}/block - Non-STAS cannot block"""
        response = requests.post(
            f"{BASE_URL}/api/devices/account/{EMPLOYEE_ID_002}/block",
            headers=sultan_headers,
            json={"reason": "Test"}
        )
        assert response.status_code == 403, "Only STAS can block accounts"


class TestSecurityLogsAPI:
    """Test security audit logs API"""
    
    def test_get_security_logs(self, stas_headers):
        """GET /api/devices/security-logs - Get security audit logs"""
        response = requests.get(
            f"{BASE_URL}/api/devices/security-logs",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        
        # Verify log structure if any logs exist
        if len(data) > 0:
            log = data[0]
            assert 'id' in log
            assert 'employee_id' in log
            assert 'action' in log
            assert 'performed_by' in log
            assert 'timestamp' in log
        print(f"Security logs count: {len(data)}")
    
    def test_get_security_logs_with_employee_filter(self, stas_headers):
        """GET /api/devices/security-logs?employee_id={id} - Filter by employee"""
        response = requests.get(
            f"{BASE_URL}/api/devices/security-logs?employee_id={EMPLOYEE_ID_002}",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned logs should be for the specified employee
        for log in data:
            assert log.get('employee_id') == EMPLOYEE_ID_002
    
    def test_security_logs_requires_stas_role(self, sultan_headers):
        """GET /api/devices/security-logs - Non-STAS cannot access"""
        response = requests.get(
            f"{BASE_URL}/api/devices/security-logs",
            headers=sultan_headers
        )
        assert response.status_code == 403


class TestTransactionDeleteAPI:
    """Test DELETE /api/transactions/{id} - STAS can delete own transactions"""
    
    def test_non_stas_cannot_delete(self, sultan_headers):
        """DELETE /api/transactions/{id} - Non-STAS users cannot delete"""
        # Try to delete with a fake ID - should fail on role check first
        response = requests.delete(
            f"{BASE_URL}/api/transactions/fake-id-123",
            headers=sultan_headers
        )
        assert response.status_code == 403, "Non-STAS should be rejected"
        data = response.json()
        detail = data.get('detail', {})
        if isinstance(detail, dict):
            assert detail.get('error') == 'NOT_AUTHORIZED'
    
    def test_delete_nonexistent_transaction(self, stas_headers):
        """DELETE /api/transactions/{id} - Returns 404 for non-existent"""
        response = requests.delete(
            f"{BASE_URL}/api/transactions/nonexistent-tx-id",
            headers=stas_headers
        )
        assert response.status_code == 404, "Should return 404 for non-existent transaction"
    
    def test_get_transactions_for_stas(self, stas_headers):
        """GET /api/transactions - STAS sees all transactions"""
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"STAS visible transactions: {len(data)}")


class TestMyTransactionsIntegration:
    """Test My Transactions tab functionality (API integration)"""
    
    def test_transactions_list_returns_correct_structure(self, stas_headers):
        """GET /api/transactions - Returns correct transaction structure"""
        response = requests.get(
            f"{BASE_URL}/api/transactions",
            headers=stas_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure if transactions exist
        if len(data) > 0:
            tx = data[0]
            expected_fields = ['id', 'ref_no', 'type', 'status', 'employee_id']
            for field in expected_fields:
                assert field in tx, f"Transaction should have {field} field"


class TestDeviceValidationAPI:
    """Test device fingerprint validation API (public endpoint)"""
    
    def test_device_signature_generation(self, stas_headers):
        """POST /api/devices/signature - Generate device signature"""
        fingerprint_data = {
            "userAgent": "Mozilla/5.0 (Test) Chrome/120.0",
            "platform": "Win32",
            "screenResolution": "1920x1080",
            "timezone": "Asia/Riyadh",
            "language": "en-US",
            "webglVendor": "Test Vendor",
            "webglRenderer": "Test Renderer",
            "canvasFingerprint": "test-canvas-hash",
            "deviceMemory": "8",
            "hardwareConcurrency": "8",
            "touchSupport": "false",
            "cookiesEnabled": "true",
            "localStorageEnabled": "true"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/devices/signature",
            headers=stas_headers,
            json=fingerprint_data
        )
        assert response.status_code == 200
        data = response.json()
        assert 'signature' in data
        assert len(data['signature']) == 64, "SHA256 hash should be 64 chars"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
