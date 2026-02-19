"""
Backend tests for Iteration 4 features:
1. Role-based status colors - Pending Supervisor should be blue (#1D4ED8), Pending Ops should be orange (#F97316)
2. Work Locations API - create, list, update, delete locations
3. Work Locations page accessible for Sultan/Naif/STAS roles

API URL: Uses REACT_APP_BACKEND_URL from environment
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-system-staging.preview.emergentagent.com')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def users_map(api_client):
    """Get all users and map by username"""
    response = api_client.get(f"{BASE_URL}/api/auth/users")
    assert response.status_code == 200
    users = response.json()
    return {u['username']: u for u in users}


def get_token(api_client, user_id):
    """Get auth token for user via switch endpoint"""
    response = api_client.post(f"{BASE_URL}/api/auth/switch/{user_id}")
    if response.status_code == 200:
        return response.json().get('token')
    return None


def auth_headers(token):
    """Return auth headers with token"""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ==================== HEALTH CHECK ====================
class TestHealthCheck:
    """Basic API health check"""
    
    def test_api_health(self, api_client):
        """Test health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get('status') == 'ok'
        print(f"✓ API health check passed")


# ==================== ROLE-BASED STATUS COLORS (API Values) ====================
class TestStatusValues:
    """
    Verify transaction status values returned by API.
    Frontend maps statuses to colors:
    - pending_supervisor: #1D4ED8 (supervisor blue)
    - pending_ops: #F97316 (sultan orange)
    - pending_finance: #0D9488 (salah teal)
    - pending_ceo: #B91C1C (mohammed red)
    - pending_stas: #7C3AED (stas purple)
    - executed: #16A34A (green)
    - rejected: #DC2626 (red)
    """
    
    def test_transaction_status_values_valid(self, api_client, users_map):
        """Verify transactions have valid status values"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/transactions", headers=auth_headers(token))
        assert response.status_code == 200
        transactions = response.json()
        
        valid_statuses = [
            'pending_supervisor', 'pending_ops', 'pending_finance', 
            'pending_ceo', 'pending_stas', 'executed', 'rejected'
        ]
        
        status_counts = {}
        for tx in transactions:
            status = tx.get('status')
            status_counts[status] = status_counts.get(status, 0) + 1
            assert status in valid_statuses, f"Invalid status '{status}' in TX {tx.get('ref_no')}"
        
        print(f"✓ All {len(transactions)} transactions have valid statuses")
        print(f"  Status breakdown: {status_counts}")


# ==================== WORK LOCATIONS API ====================
class TestWorkLocationsAPI:
    """Test Work Locations API - CRUD operations"""
    
    def test_list_work_locations_unauthenticated_fails(self, api_client):
        """Test that unauthenticated access fails"""
        response = api_client.get(f"{BASE_URL}/api/work-locations")
        assert response.status_code in [401, 403, 422], f"Expected 401/403/422, got {response.status_code}"
        print(f"✓ Unauthenticated access correctly blocked (status {response.status_code})")
    
    def test_list_work_locations_as_stas(self, api_client, users_map):
        """STAS should be able to list work locations"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, list)
        print(f"✓ STAS can list work locations - found {len(locations)} locations")
        
        if locations:
            loc = locations[0]
            print(f"  First location: {loc.get('name')} / {loc.get('name_ar')}")
    
    def test_list_work_locations_as_sultan(self, api_client, users_map):
        """Sultan should be able to list work locations"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, list)
        print(f"✓ Sultan can list work locations - found {len(locations)} locations")
    
    def test_list_work_locations_as_naif(self, api_client, users_map):
        """Naif should be able to list work locations"""
        naif = users_map.get('naif')
        token = get_token(api_client, naif['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        assert isinstance(locations, list)
        print(f"✓ Naif can list work locations - found {len(locations)} locations")
    
    def test_list_work_locations_as_employee(self, api_client, users_map):
        """Employee should also be able to list work locations (read access)"""
        employee = users_map.get('employee1')
        if not employee:
            pytest.skip("employee1 not found")
        token = get_token(api_client, employee['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        print(f"✓ Employee can list work locations (read access)")
    
    def test_create_work_location_as_stas(self, api_client, users_map):
        """STAS should be able to create work locations"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        location_data = {
            "name": f"TEST_STAS_Location_{uuid.uuid4().hex[:6]}",
            "name_ar": "موقع اختبار",
            "latitude": 24.7136,
            "longitude": 46.6753,
            "radius_meters": 300,
            "work_start": "09:00",
            "work_end": "18:00",
            "work_days": {
                "saturday": True,
                "sunday": True,
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": False
            },
            "assigned_employees": []
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/work-locations",
            json=location_data,
            headers=auth_headers(token)
        )
        assert response.status_code == 200
        location = response.json()
        
        assert location.get('name') == location_data['name']
        assert location.get('name_ar') == location_data['name_ar']
        assert location.get('latitude') == location_data['latitude']
        assert location.get('longitude') == location_data['longitude']
        assert 'id' in location
        
        print(f"✓ STAS created work location: {location.get('id')}")
        return location
    
    def test_create_work_location_as_sultan(self, api_client, users_map):
        """Sultan should be able to create work locations"""
        sultan = users_map.get('sultan')
        token = get_token(api_client, sultan['id'])
        
        location_data = {
            "name": f"TEST_Sultan_Location_{uuid.uuid4().hex[:6]}",
            "name_ar": "موقع سلطان",
            "latitude": 24.8000,
            "longitude": 46.7000,
            "radius_meters": 400,
            "work_start": "08:30",
            "work_end": "17:30",
            "work_days": {
                "saturday": True,
                "sunday": True,
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": False,
                "friday": False
            },
            "assigned_employees": []
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/work-locations",
            json=location_data,
            headers=auth_headers(token)
        )
        assert response.status_code == 200
        location = response.json()
        assert location.get('name') == location_data['name']
        print(f"✓ Sultan created work location: {location.get('id')}")
        return location
    
    def test_create_work_location_as_employee_fails(self, api_client, users_map):
        """Employee should NOT be able to create work locations"""
        employee = users_map.get('employee1')
        if not employee:
            pytest.skip("employee1 not found")
        token = get_token(api_client, employee['id'])
        
        location_data = {
            "name": "TEST_Employee_Location",
            "name_ar": "موقع موظف",
            "latitude": 24.5000,
            "longitude": 46.5000,
            "radius_meters": 200,
            "work_start": "08:00",
            "work_end": "17:00",
            "work_days": {
                "saturday": True, "sunday": True, "monday": True,
                "tuesday": True, "wednesday": True, "thursday": True, "friday": False
            },
            "assigned_employees": []
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/work-locations",
            json=location_data,
            headers=auth_headers(token)
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print(f"✓ Employee correctly denied from creating work locations (403)")
    
    def test_update_work_location_as_stas(self, api_client, users_map):
        """STAS should be able to update work locations"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # First, create a location
        create_data = {
            "name": f"TEST_Update_{uuid.uuid4().hex[:6]}",
            "name_ar": "موقع تحديث",
            "latitude": 24.6000,
            "longitude": 46.5500,
            "radius_meters": 250,
            "work_start": "08:00",
            "work_end": "17:00",
            "work_days": {
                "saturday": True, "sunday": True, "monday": True,
                "tuesday": True, "wednesday": True, "thursday": True, "friday": False
            },
            "assigned_employees": []
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/work-locations",
            json=create_data,
            headers=auth_headers(token)
        )
        assert create_response.status_code == 200
        location = create_response.json()
        location_id = location['id']
        
        # Update the location
        update_data = {
            "name": f"TEST_Updated_{uuid.uuid4().hex[:6]}",
            "radius_meters": 600
        }
        
        update_response = api_client.put(
            f"{BASE_URL}/api/work-locations/{location_id}",
            json=update_data,
            headers=auth_headers(token)
        )
        assert update_response.status_code == 200
        updated_location = update_response.json()
        
        assert updated_location.get('radius_meters') == 600
        print(f"✓ STAS updated work location {location_id}")
    
    def test_delete_work_location_as_stas(self, api_client, users_map):
        """STAS should be able to delete (deactivate) work locations"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # First, create a location to delete
        create_data = {
            "name": f"TEST_Delete_{uuid.uuid4().hex[:6]}",
            "name_ar": "موقع حذف",
            "latitude": 24.5500,
            "longitude": 46.4500,
            "radius_meters": 200,
            "work_start": "08:00",
            "work_end": "17:00",
            "work_days": {
                "saturday": True, "sunday": True, "monday": True,
                "tuesday": True, "wednesday": True, "thursday": True, "friday": False
            },
            "assigned_employees": []
        }
        
        create_response = api_client.post(
            f"{BASE_URL}/api/work-locations",
            json=create_data,
            headers=auth_headers(token)
        )
        assert create_response.status_code == 200
        location = create_response.json()
        location_id = location['id']
        
        # Delete the location
        delete_response = api_client.delete(
            f"{BASE_URL}/api/work-locations/{location_id}",
            headers=auth_headers(token)
        )
        assert delete_response.status_code == 200
        print(f"✓ STAS deleted work location {location_id}")
        
        # Verify it's deactivated (should still return but with is_active=False or not appear in list)
        list_response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        locations = list_response.json()
        deleted_loc = next((l for l in locations if l['id'] == location_id), None)
        # If the location still appears, it should have is_active=False
        if deleted_loc:
            assert deleted_loc.get('is_active') == False, "Deleted location should have is_active=False"
    
    def test_get_single_work_location(self, api_client, users_map):
        """Test getting a single work location by ID"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        # First list locations
        list_response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert list_response.status_code == 200
        locations = list_response.json()
        
        if not locations:
            pytest.skip("No work locations to test")
        
        # Get first location by ID
        location_id = locations[0]['id']
        response = api_client.get(f"{BASE_URL}/api/work-locations/{location_id}", headers=auth_headers(token))
        assert response.status_code == 200
        location = response.json()
        
        assert location.get('id') == location_id
        assert 'name' in location
        assert 'latitude' in location
        assert 'longitude' in location
        print(f"✓ Retrieved work location by ID: {location.get('name')}")


# ==================== WORK LOCATION DATA VALIDATION ====================
class TestWorkLocationDataStructure:
    """Test that work location data structure is correct"""
    
    def test_work_location_has_required_fields(self, api_client, users_map):
        """Verify work locations have all required fields"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        
        if not locations:
            pytest.skip("No work locations to verify")
        
        required_fields = [
            'id', 'name', 'name_ar', 'latitude', 'longitude',
            'radius_meters', 'work_start', 'work_end', 'work_days'
        ]
        
        for loc in locations:
            for field in required_fields:
                assert field in loc, f"Location {loc.get('id')} missing required field: {field}"
        
        print(f"✓ All {len(locations)} locations have required fields")
    
    def test_work_days_structure(self, api_client, users_map):
        """Verify work_days has correct structure"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        
        if not locations:
            pytest.skip("No work locations to verify")
        
        expected_days = ['saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        for loc in locations:
            work_days = loc.get('work_days', {})
            for day in expected_days:
                assert day in work_days, f"Location {loc.get('id')} missing day: {day}"
                assert isinstance(work_days[day], bool), f"Day {day} should be boolean"
        
        print(f"✓ All locations have correct work_days structure")


# ==================== CLEANUP TEST DATA ====================
class TestCleanupTestData:
    """Cleanup TEST_ prefixed locations after tests"""
    
    def test_cleanup_test_locations(self, api_client, users_map):
        """Remove all TEST_ prefixed locations"""
        stas = users_map.get('stas')
        token = get_token(api_client, stas['id'])
        
        response = api_client.get(f"{BASE_URL}/api/work-locations", headers=auth_headers(token))
        assert response.status_code == 200
        locations = response.json()
        
        test_locations = [l for l in locations if l.get('name', '').startswith('TEST_')]
        
        deleted_count = 0
        for loc in test_locations:
            del_response = api_client.delete(
                f"{BASE_URL}/api/work-locations/{loc['id']}",
                headers=auth_headers(token)
            )
            if del_response.status_code == 200:
                deleted_count += 1
        
        print(f"✓ Cleaned up {deleted_count} test locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
