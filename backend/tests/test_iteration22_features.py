"""
Iteration 22 Backend Tests:
1. GET /api/health - returns version
2. GET /api/announcements - returns pinned & regular
3. POST /api/announcements - create new announcement
4. DELETE work_locations - check if protected
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test users
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
SULTAN_USER_ID = "0abb08a8-ed29-534d-84f6-c91e58a84f43"


@pytest.fixture(scope="module")
def session():
    """Create requests session"""
    return requests.Session()


@pytest.fixture(scope="module")
def stas_session():
    """Get session authenticated as STAS"""
    s = requests.Session()
    response = s.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    if response.status_code == 200:
        token = response.json().get("token")  # API returns 'token' not 'access_token'
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def sultan_session():
    """Get session authenticated as Sultan"""
    s = requests.Session()
    response = s.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    if response.status_code == 200:
        token = response.json().get("token")  # API returns 'token' not 'access_token'
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


class TestHealthEndpoint:
    """Test /api/health endpoint returns version"""
    
    def test_health_returns_version(self, session):
        """Health endpoint should return version field"""
        response = session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "ok"
        assert "version" in data, "version field should be in health response"
        assert data["version"] == "21.1", f"Expected version 21.1, got {data['version']}"
        assert "service" in data
        print(f"✅ Health endpoint returns version: {data['version']}")


class TestAnnouncementsAPI:
    """Test announcements CRUD operations"""
    
    def test_get_announcements_structure(self, stas_session):
        """GET /api/announcements should return pinned and regular arrays"""
        response = stas_session.get(f"{BASE_URL}/api/announcements")
        assert response.status_code == 200
        data = response.json()
        
        assert "pinned" in data, "Response should have 'pinned' array"
        assert "regular" in data, "Response should have 'regular' array"
        assert isinstance(data["pinned"], list), "'pinned' should be a list"
        assert isinstance(data["regular"], list), "'regular' should be a list"
        print(f"✅ Announcements structure correct: pinned={len(data['pinned'])}, regular={len(data['regular'])}")
    
    def test_create_regular_announcement(self, stas_session):
        """POST /api/announcements should create regular announcement"""
        announcement_data = {
            "message_ar": "إشعار تجريبي للاختبار",
            "message_en": "Test announcement",
            "is_pinned": False
        }
        
        response = stas_session.post(f"{BASE_URL}/api/announcements", json=announcement_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data, "Response should have id"
        assert data["message_ar"] == announcement_data["message_ar"]
        assert data["message_en"] == announcement_data["message_en"]
        assert data["is_pinned"] == False
        assert "created_by" in data
        print(f"✅ Created regular announcement: {data['id']}")
        
        # Cleanup
        cleanup_resp = stas_session.delete(f"{BASE_URL}/api/announcements/{data['id']}")
        assert cleanup_resp.status_code == 200
        print(f"✅ Cleaned up announcement")
    
    def test_create_pinned_announcement(self, stas_session):
        """POST /api/announcements with is_pinned=True should create pinned announcement"""
        announcement_data = {
            "message_ar": "إشعار مثبت تجريبي",
            "message_en": "Test pinned announcement",
            "is_pinned": True
        }
        
        response = stas_session.post(f"{BASE_URL}/api/announcements", json=announcement_data)
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_pinned"] == True
        print(f"✅ Created pinned announcement: {data['id']}")
        
        # Verify it appears in pinned list
        get_response = stas_session.get(f"{BASE_URL}/api/announcements")
        assert get_response.status_code == 200
        all_announcements = get_response.json()
        
        pinned_ids = [a["id"] for a in all_announcements["pinned"]]
        assert data["id"] in pinned_ids, "Pinned announcement should be in pinned list"
        print(f"✅ Verified announcement appears in pinned list")
        
        # Cleanup
        cleanup_resp = stas_session.delete(f"{BASE_URL}/api/announcements/{data['id']}")
        assert cleanup_resp.status_code == 200
    
    def test_dismiss_regular_announcement(self, stas_session):
        """POST /api/announcements/{id}/dismiss should dismiss regular announcement"""
        # Create announcement first
        announcement_data = {
            "message_ar": "إشعار للإخفاء",
            "message_en": "Announcement to dismiss",
            "is_pinned": False
        }
        create_resp = stas_session.post(f"{BASE_URL}/api/announcements", json=announcement_data)
        assert create_resp.status_code == 200
        ann_id = create_resp.json()["id"]
        
        # Dismiss it
        dismiss_resp = stas_session.post(f"{BASE_URL}/api/announcements/{ann_id}/dismiss")
        assert dismiss_resp.status_code == 200
        print(f"✅ Dismissed announcement: {ann_id}")
        
        # Verify it's not in regular list anymore
        get_resp = stas_session.get(f"{BASE_URL}/api/announcements")
        regular_ids = [a["id"] for a in get_resp.json()["regular"]]
        assert ann_id not in regular_ids, "Dismissed announcement should not be in regular list"
        print(f"✅ Dismissed announcement not in regular list")
        
        # Cleanup
        stas_session.delete(f"{BASE_URL}/api/announcements/{ann_id}")
    
    def test_cannot_dismiss_pinned_announcement(self, stas_session):
        """POST /api/announcements/{id}/dismiss should fail for pinned announcements"""
        # Create pinned announcement
        announcement_data = {
            "message_ar": "إشعار مثبت",
            "message_en": "Pinned announcement",
            "is_pinned": True
        }
        create_resp = stas_session.post(f"{BASE_URL}/api/announcements", json=announcement_data)
        assert create_resp.status_code == 200
        ann_id = create_resp.json()["id"]
        
        # Try to dismiss - should fail
        dismiss_resp = stas_session.post(f"{BASE_URL}/api/announcements/{ann_id}/dismiss")
        assert dismiss_resp.status_code == 400
        print(f"✅ Correctly rejected dismiss for pinned announcement")
        
        # Cleanup
        stas_session.delete(f"{BASE_URL}/api/announcements/{ann_id}")
    
    def test_get_all_announcements_admin(self, stas_session):
        """GET /api/announcements/all should return all announcements for admin"""
        response = stas_session.get(f"{BASE_URL}/api/announcements/all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return list of all announcements"
        print(f"✅ Admin can view all {len(data)} announcements")


class TestProtectedCollections:
    """Test that work_locations is in protected collections"""
    
    def test_collections_info_has_work_locations_protected(self, stas_session):
        """GET /api/maintenance/collections-info should show work_locations as protected"""
        response = stas_session.get(f"{BASE_URL}/api/maintenance/collections-info")
        assert response.status_code == 200
        data = response.json()
        
        protected = data.get("protected_collections", {}).get("collections", [])
        assert "work_locations" in protected, "work_locations should be in protected_collections"
        print(f"✅ work_locations is in protected_collections: {protected}")
    
    def test_storage_info_shows_work_locations(self, stas_session):
        """GET /api/maintenance/storage-info should show work_locations info"""
        response = stas_session.get(f"{BASE_URL}/api/maintenance/storage-info")
        assert response.status_code == 200
        data = response.json()
        
        collections = data.get("collections", {})
        assert "work_locations" in collections, "work_locations should be in storage info"
        
        wl_info = collections["work_locations"]
        assert wl_info.get("is_protected") == True, "work_locations should be marked as protected"
        print(f"✅ work_locations is protected in storage info: {wl_info}")


class TestWorkLocationsAPI:
    """Test work locations endpoints"""
    
    def test_get_work_locations(self, stas_session):
        """GET /api/work-locations should return list"""
        response = stas_session.get(f"{BASE_URL}/api/work-locations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return list of work locations"
        print(f"✅ Work locations API returns {len(data)} locations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
