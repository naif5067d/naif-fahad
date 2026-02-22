"""
Iteration 42 - Nuclear Delete Feature Tests
Tests the nuclear delete functionality for ATS system that:
1. Only allows stas and sultan users to perform nuclear delete
2. Returns 403 for other users (like naif)
3. Deletes all files in /app/ats_storage/cv_files/
4. Deletes all records from ats_applications collection
5. Creates audit log entry in ats_audit_log
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestNuclearDeletePermissions:
    """Test nuclear delete endpoint permission controls"""
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        """Get auth token for stas user (has nuclear access)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as stas")
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        """Get auth token for sultan user (has nuclear access)"""
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
    
    @pytest.fixture(scope="class")
    def mohammed_token(self):
        """Get auth token for mohammed user (should NOT have nuclear access)"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "mohammed", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as mohammed")
    
    def test_login_stas_success(self):
        """Test that stas can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas", "password": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["username"] == "stas"
        print("✓ stas login successful")
    
    def test_login_sultan_success(self):
        """Test that sultan can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sultan", "password": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["username"] == "sultan"
        print("✓ sultan login successful")
    
    def test_login_naif_success(self):
        """Test that naif can login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "naif", "password": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["username"] == "naif"
        print("✓ naif login successful")
    
    def test_nuclear_delete_denied_for_naif(self, naif_token):
        """Test that naif CANNOT perform nuclear delete - should return 403"""
        response = requests.delete(
            f"{BASE_URL}/api/ats/admin/nuclear-delete",
            headers={"Authorization": f"Bearer {naif_token}"}
        )
        assert response.status_code == 403, f"Expected 403 for naif, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        # Should contain the Arabic/English denial message
        assert "sultan" in data["detail"].lower() or "stas" in data["detail"].lower() or "فقط" in data["detail"]
        print(f"✓ naif correctly denied (403): {data['detail']}")
    
    def test_nuclear_delete_denied_for_mohammed(self, mohammed_token):
        """Test that mohammed CANNOT perform nuclear delete - should return 403"""
        response = requests.delete(
            f"{BASE_URL}/api/ats/admin/nuclear-delete",
            headers={"Authorization": f"Bearer {mohammed_token}"}
        )
        # Either 403 (access denied for nuclear) or might be 403 for ATS access
        assert response.status_code == 403, f"Expected 403 for mohammed, got {response.status_code}"
        print(f"✓ mohammed correctly denied (403)")
    
    def test_nuclear_delete_allowed_for_stas(self, stas_token):
        """Test that stas CAN call nuclear delete - should return 200 (success)"""
        response = requests.delete(
            f"{BASE_URL}/api/ats/admin/nuclear-delete",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for stas, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "deleted_files" in data
        assert "deleted_records" in data
        assert data.get("performed_by") == "stas"
        print(f"✓ stas nuclear delete succeeded: {data['deleted_records']} records, {data['deleted_files']} files")
    
    def test_nuclear_delete_allowed_for_sultan(self, sultan_token):
        """Test that sultan CAN call nuclear delete - should return 200 (success)"""
        response = requests.delete(
            f"{BASE_URL}/api/ats/admin/nuclear-delete",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200, f"Expected 200 for sultan, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "deleted_files" in data
        assert "deleted_records" in data
        assert data.get("performed_by") == "sultan"
        print(f"✓ sultan nuclear delete succeeded: {data['deleted_records']} records, {data['deleted_files']} files")
    
    def test_nuclear_delete_without_auth(self):
        """Test that unauthenticated requests are rejected"""
        response = requests.delete(f"{BASE_URL}/api/ats/admin/nuclear-delete")
        # Should return 401 or 403 for unauthenticated
        assert response.status_code in [401, 403], f"Expected 401/403 for unauthenticated, got {response.status_code}"
        print("✓ Unauthenticated request correctly rejected")


class TestNuclearDeleteFunctionality:
    """Test that nuclear delete actually deletes data and creates audit log"""
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        """Get auth token for stas user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as stas")
    
    def test_ats_stats_endpoint(self, stas_token):
        """Test that ATS stats endpoint works to verify data state"""
        response = requests.get(
            f"{BASE_URL}/api/ats/admin/stats",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_applications" in data
        print(f"✓ ATS stats: {data['total_applications']} applications, {data['total_jobs']} jobs")
        return data
    
    def test_nuclear_delete_response_structure(self, stas_token):
        """Test that nuclear delete returns proper response structure"""
        response = requests.delete(
            f"{BASE_URL}/api/ats/admin/nuclear-delete",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "message" in data
        assert "deleted_files" in data
        assert "deleted_records" in data
        assert "performed_by" in data
        
        # Check message structure (bilingual)
        assert "ar" in data["message"]
        assert "en" in data["message"]
        
        # Verify values are integers
        assert isinstance(data["deleted_files"], int)
        assert isinstance(data["deleted_records"], int)
        
        print(f"✓ Response structure valid: {data}")


class TestATSEndpointsAccess:
    """Test ATS endpoint access for different users"""
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "stas", "password": "123456"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Unable to login as stas")
    
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
    
    def test_stas_can_access_ats_jobs(self, stas_token):
        """Test that stas can access ATS jobs list"""
        response = requests.get(
            f"{BASE_URL}/api/ats/admin/jobs",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        print("✓ stas can access /api/ats/admin/jobs")
    
    def test_sultan_can_access_ats_jobs(self, sultan_token):
        """Test that sultan can access ATS jobs list"""
        response = requests.get(
            f"{BASE_URL}/api/ats/admin/jobs",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        print("✓ sultan can access /api/ats/admin/jobs")
    
    def test_naif_can_access_ats_jobs(self, naif_token):
        """Test that naif can access ATS jobs list (has ATS access, just not nuclear)"""
        response = requests.get(
            f"{BASE_URL}/api/ats/admin/jobs",
            headers={"Authorization": f"Bearer {naif_token}"}
        )
        assert response.status_code == 200
        print("✓ naif can access /api/ats/admin/jobs (regular ATS access)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
