"""
Iteration 51 - System Nuclear Delete Feature Tests
Tests the new system-wide nuclear delete functionality that:
1. Only allows stas and sultan users to perform nuclear delete
2. Deletes all transactional data (login_sessions, attendance, transactions, etc.)
3. Preserves contracts, users, employees, and settings
4. Returns collections statistics before deletion
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCollectionsStatsAPI:
    """Test GET /api/system/collections-stats endpoint"""
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        """Get auth token for stas user (stas506)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas506", "password": "654321"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as stas506")
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        """Get auth token for sultan user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as sultan")
    
    @pytest.fixture(scope="class")
    def naif_token(self):
        """Get auth token for naif user (should NOT have nuclear access)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "naif", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as naif")
    
    def test_stas_can_get_collections_stats(self, stas_token):
        """Test that stas user can access collections-stats"""
        response = requests.get(
            f"{BASE_URL}/api/system/collections-stats",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "collections" in data
        assert "total_documents" in data
        assert "preserved" in data
        
        # Verify collections include transactional data types
        assert "login_sessions" in data["collections"]
        assert "attendance" in data["collections"]
        assert "transactions" in data["collections"]
        
        # Verify preserved collections are listed
        assert "contracts" in data["preserved"]
        assert "users" in data["preserved"]
        
        print(f"✓ stas can access collections-stats: {data['total_documents']} total documents")
    
    def test_sultan_can_get_collections_stats(self, sultan_token):
        """Test that sultan user can access collections-stats"""
        response = requests.get(
            f"{BASE_URL}/api/system/collections-stats",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "collections" in data
        assert "total_documents" in data
        print(f"✓ sultan can access collections-stats: {data['total_documents']} total documents")
    
    def test_naif_cannot_get_collections_stats(self, naif_token):
        """Test that naif user CANNOT access collections-stats - should return 403"""
        response = requests.get(
            f"{BASE_URL}/api/system/collections-stats",
            headers={"Authorization": f"Bearer {naif_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for naif, got {response.status_code}"
        print("✓ naif correctly denied access to collections-stats (403)")
    
    def test_unauthenticated_cannot_get_collections_stats(self):
        """Test that unauthenticated requests are rejected"""
        response = requests.get(f"{BASE_URL}/api/system/collections-stats")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestNuclearDeletePermissions:
    """Test POST /api/system/nuclear-delete permission controls"""
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas506", "password": "654321"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as stas506")
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as sultan")
    
    @pytest.fixture(scope="class")
    def naif_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "naif", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as naif")
    
    def test_naif_cannot_nuclear_delete(self, naif_token):
        """Test that naif user CANNOT perform nuclear delete - should return 403"""
        response = requests.post(
            f"{BASE_URL}/api/system/nuclear-delete",
            headers={"Authorization": f"Bearer {naif_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for naif, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ naif correctly denied nuclear delete (403): {data['detail']}")
    
    def test_unauthenticated_cannot_nuclear_delete(self):
        """Test that unauthenticated requests are rejected"""
        response = requests.post(f"{BASE_URL}/api/system/nuclear-delete")
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
        print("✓ Unauthenticated nuclear delete request correctly rejected")
    
    # NOTE: We DO NOT test actual nuclear delete execution to preserve test data
    # The frontend test will verify the button and dialog work without executing


class TestAuthenticationEndpoints:
    """Test login endpoints for all users in the test scenario"""
    
    def test_stas506_login(self):
        """Test stas506 (sysadmin) login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas506", "password": "654321"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "stas"
        print("✓ stas506 login successful")
    
    def test_sultan_login(self):
        """Test sultan (admin) login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "sultan"
        print("✓ sultan login successful")
    
    def test_naif_login(self):
        """Test naif (regular user) login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "naif", "password": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "naif"
        print("✓ naif login successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
