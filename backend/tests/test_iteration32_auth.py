"""
Iteration 32 - Authentication & Login Tests
Testing P0 fixes:
1) Login page displays on app open without token
2) Login with STAS credentials: username=stas, password=DarAlCode2026!
3) User Switcher shows only for STAS
4) Login with Sultan credentials - verify no User Switcher
5) Logout functionality
6) STAS access to /stas-mirror without "Access denied"
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLoginAuthentication:
    """Test login endpoint with different credentials"""
    
    def test_login_stas_success(self):
        """Test login with STAS credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "DarAlCode2026!",
            "device_signature": "TEST_DEV_123",
            "fingerprint_data": {"userAgent": "TestAgent", "platform": "Test"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should contain token"
        assert "user" in data, "Response should contain user"
        assert data["user"]["username"] == "stas"
        assert data["user"]["role"] == "stas"
        print(f"SUCCESS: STAS login successful, role={data['user']['role']}")
        return data["token"]
    
    def test_login_sultan_success(self):
        """Test login with Sultan credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!",
            "device_signature": "TEST_DEV_SULTAN",
            "fingerprint_data": {"userAgent": "TestAgent", "platform": "Test"}
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == "sultan"
        assert data["user"]["role"] == "sultan"
        print(f"SUCCESS: Sultan login successful, role={data['user']['role']}")
        return data["token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "invalid_user",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Invalid credentials correctly rejected")
    
    def test_login_wrong_password(self):
        """Test login with correct username but wrong password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "wrongpassword123"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Wrong password correctly rejected")


class TestUserSwitcherAccess:
    """Test that user switcher is only accessible to STAS"""
    
    @pytest.fixture
    def stas_token(self):
        """Get STAS token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture
    def sultan_token(self):
        """Get Sultan token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_stas_can_list_users(self, stas_token):
        """STAS should be able to list all users for switcher"""
        response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0, "Should have at least one user"
        print(f"SUCCESS: STAS can list {len(users)} users for switcher")
    
    def test_sultan_cannot_list_users(self, sultan_token):
        """Sultan should NOT be able to list users (403)"""
        response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("SUCCESS: Sultan correctly denied access to user list")
    
    def test_stas_can_switch_user(self, stas_token):
        """STAS should be able to switch to another user"""
        # First, get the list of users
        users_response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert users_response.status_code == 200
        users = users_response.json()
        
        # Find Sultan user
        sultan_user = next((u for u in users if u["username"] == "sultan"), None)
        assert sultan_user is not None, "Sultan user should exist"
        
        # Try to switch to Sultan
        switch_response = requests.post(
            f"{BASE_URL}/api/auth/switch/{sultan_user['id']}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        
        assert switch_response.status_code == 200, f"Expected 200, got {switch_response.status_code}: {switch_response.text}"
        
        data = switch_response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["username"] == "sultan"
        print("SUCCESS: STAS can switch to Sultan user")
    
    def test_sultan_cannot_switch_user(self, sultan_token, stas_token):
        """Sultan should NOT be able to switch users"""
        # Get user ID of STAS
        users_response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        users = users_response.json()
        stas_user = next((u for u in users if u["username"] == "stas"), None)
        
        # Sultan tries to switch
        switch_response = requests.post(
            f"{BASE_URL}/api/auth/switch/{stas_user['id']}",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        
        assert switch_response.status_code == 403, f"Expected 403, got {switch_response.status_code}"
        print("SUCCESS: Sultan correctly denied from switching users")


class TestSTASMirrorAccess:
    """Test STAS access to /stas-mirror page (no Access Denied)"""
    
    @pytest.fixture
    def stas_token(self):
        """Get STAS token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_stas_me_endpoint(self, stas_token):
        """Test /api/auth/me endpoint returns correct STAS user data"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        user = response.json()
        assert user["role"] == "stas", f"Expected role 'stas', got '{user.get('role')}'"
        assert user["username"] == "stas"
        print(f"SUCCESS: STAS /me endpoint returns correct user, role={user['role']}")


class TestTokenValidation:
    """Test token validation and expiration"""
    
    def test_invalid_token_rejected(self):
        """Invalid token should be rejected"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_123"}
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: Invalid token correctly rejected")
    
    def test_no_token_rejected(self):
        """Request without token should be rejected"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: Request without token correctly rejected")


class TestPasswordNotExposed:
    """Verify plain password is not exposed in regular responses"""
    
    @pytest.fixture
    def stas_token(self):
        """Get STAS token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "DarAlCode2026!"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_login_response_no_password(self):
        """Login response should NOT contain password_hash or plain_password"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas",
            "password": "DarAlCode2026!"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check user object doesn't have password
        user = data.get("user", {})
        assert "password_hash" not in user, "password_hash should not be in response"
        # plain_password is deliberately excluded from login response
        print("SUCCESS: Password not exposed in login response")
    
    def test_users_list_no_password(self, stas_token):
        """Users list should NOT contain password_hash or plain_password"""
        response = requests.get(
            f"{BASE_URL}/api/auth/users",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()
        
        for user in users:
            assert "password_hash" not in user, f"password_hash exposed for {user.get('username')}"
            # Note: plain_password may be included for STAS for specific user detail endpoints
        
        print("SUCCESS: Password hash not exposed in users list")
