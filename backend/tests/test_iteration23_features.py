"""
Iteration 23 - Testing New Features:
1. Work Locations Page - Map rendering fix (no overlapping maps)
2. Employees Page - Delete employee functionality
3. Employees Page - Credentials management (username/password)
4. API: /api/users endpoints
5. API: DELETE /api/employees/{id}
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def stas_token():
    """Get STAS authentication token"""
    # Get users list
    users_res = requests.get(f"{BASE_URL}/api/auth/users")
    assert users_res.status_code == 200
    users = users_res.json()
    
    # Find STAS user
    stas_user = next((u for u in users if u['role'] == 'stas'), None)
    assert stas_user is not None, "STAS user not found"
    
    # Get token
    token_res = requests.post(f"{BASE_URL}/api/auth/switch/{stas_user['id']}")
    assert token_res.status_code == 200
    return token_res.json()['token']


@pytest.fixture(scope="module")
def auth_headers(stas_token):
    """Get authorization headers with STAS token"""
    return {"Authorization": f"Bearer {stas_token}"}


@pytest.fixture(scope="module")
def employees_list(auth_headers):
    """Get list of all employees"""
    res = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
    assert res.status_code == 200
    return res.json()


class TestUsersAPI:
    """Test /api/users endpoints for credential management"""
    
    def test_list_users(self, auth_headers):
        """Test GET /api/users - list all users"""
        res = requests.get(f"{BASE_URL}/api/users", headers=auth_headers)
        assert res.status_code == 200
        users = res.json()
        assert isinstance(users, list)
        print(f"Found {len(users)} users")
        
        # Verify structure - no password_hash exposed
        if users:
            assert "password_hash" not in users[0]
            assert "id" in users[0]
    
    def test_get_user_by_employee_id_existing(self, auth_headers, employees_list):
        """Test GET /api/users/{employee_id} - get user for existing employee"""
        # Find an employee that has a user account
        for emp in employees_list:
            res = requests.get(f"{BASE_URL}/api/users/{emp['id']}", headers=auth_headers)
            if res.status_code == 200:
                user = res.json()
                assert "password_hash" not in user
                assert user.get("employee_id") == emp['id']
                print(f"Found user for employee {emp['id']}: {user.get('username')}")
                return
        
        # If no user found, that's okay - just skip
        pytest.skip("No employee with user account found")
    
    def test_get_user_by_employee_id_nonexistent(self, auth_headers):
        """Test GET /api/users/{employee_id} - should return 404 for non-existent"""
        res = requests.get(f"{BASE_URL}/api/users/non-existent-id-12345", headers=auth_headers)
        assert res.status_code == 404


class TestCredentialsManagement:
    """Test credential update functionality"""
    
    def test_update_credentials_nonexistent_user(self, auth_headers):
        """Test PUT /api/users/{employee_id}/credentials - 404 for non-existent"""
        res = requests.put(
            f"{BASE_URL}/api/users/non-existent-id-12345/credentials",
            headers=auth_headers,
            json={"username": "newuser"}
        )
        assert res.status_code == 404
    
    def test_update_credentials_existing_user(self, auth_headers, employees_list):
        """Test PUT /api/users/{employee_id}/credentials - update existing user"""
        # Find an employee with user account
        for emp in employees_list:
            check_res = requests.get(f"{BASE_URL}/api/users/{emp['id']}", headers=auth_headers)
            if check_res.status_code == 200:
                user = check_res.json()
                original_username = user.get('username')
                
                # Just update password (don't change username to avoid issues)
                res = requests.put(
                    f"{BASE_URL}/api/users/{emp['id']}/credentials",
                    headers=auth_headers,
                    json={"password": "newpassword123"}
                )
                assert res.status_code == 200
                result = res.json()
                assert "message" in result
                print(f"Successfully updated credentials for {original_username}")
                return
        
        pytest.skip("No employee with user account found to test update")
    
    def test_update_credentials_short_password(self, auth_headers, employees_list):
        """Test PUT /api/users/{employee_id}/credentials - reject short password"""
        for emp in employees_list:
            check_res = requests.get(f"{BASE_URL}/api/users/{emp['id']}", headers=auth_headers)
            if check_res.status_code == 200:
                res = requests.put(
                    f"{BASE_URL}/api/users/{emp['id']}/credentials",
                    headers=auth_headers,
                    json={"password": "123"}  # Too short
                )
                assert res.status_code == 400
                print("Short password correctly rejected")
                return
        
        pytest.skip("No employee with user account found")


class TestDeleteEmployee:
    """Test DELETE /api/employees/{id} endpoint"""
    
    def test_delete_nonexistent_employee(self, auth_headers):
        """Test DELETE /api/employees/{id} - 404 for non-existent"""
        res = requests.delete(
            f"{BASE_URL}/api/employees/non-existent-id-12345",
            headers=auth_headers
        )
        assert res.status_code == 404
    
    def test_delete_employee_with_active_contract(self, auth_headers, employees_list):
        """Test DELETE /api/employees/{id} - should fail if employee has active contract"""
        # Find employee with active contract
        for emp in employees_list:
            contracts_res = requests.get(
                f"{BASE_URL}/api/contracts-v2?employee_id={emp['id']}",
                headers=auth_headers
            )
            if contracts_res.status_code == 200:
                contracts = contracts_res.json()
                active_contracts = [c for c in contracts if c.get('status') == 'active']
                if active_contracts:
                    # Try to delete - should fail
                    res = requests.delete(
                        f"{BASE_URL}/api/employees/{emp['id']}",
                        headers=auth_headers
                    )
                    assert res.status_code == 400
                    assert "عقد نشط" in res.json().get('detail', '') or "active contract" in res.json().get('detail', '').lower()
                    print(f"Correctly prevented deletion of employee {emp['id']} with active contract")
                    return
        
        pytest.skip("No employee with active contract found to test")


class TestEmployeesAPI:
    """Test basic employees API"""
    
    def test_list_employees(self, auth_headers):
        """Test GET /api/employees - list all employees"""
        res = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        assert res.status_code == 200
        employees = res.json()
        assert isinstance(employees, list)
        print(f"Found {len(employees)} employees")
    
    def test_get_single_employee(self, auth_headers, employees_list):
        """Test GET /api/employees/{id} - get single employee"""
        if not employees_list:
            pytest.skip("No employees to test")
        
        emp = employees_list[0]
        res = requests.get(f"{BASE_URL}/api/employees/{emp['id']}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data['id'] == emp['id']


class TestWorkLocationsAPI:
    """Test work locations API"""
    
    def test_list_work_locations(self, auth_headers):
        """Test GET /api/work-locations - list all locations"""
        res = requests.get(f"{BASE_URL}/api/work-locations", headers=auth_headers)
        assert res.status_code == 200
        locations = res.json()
        assert isinstance(locations, list)
        print(f"Found {len(locations)} work locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
