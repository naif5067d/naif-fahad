"""
Iteration 14 Tests: System Maintenance Features
- Storage Info API (total_size_kb, transaction_size_kb, protected_size_kb)
- Archives Upload Endpoint
- Date Formatting (Gregorian + Hijri)
"""
import pytest
import requests
import os
import json
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-timezone-fix.preview.emergentagent.com').rstrip('/')
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"


@pytest.fixture(scope="module")
def stas_token():
    """Get STAS user token for maintenance operations"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert resp.status_code == 200, f"Failed to get token: {resp.text}"
    return resp.json()['token']


@pytest.fixture
def auth_headers(stas_token):
    """Auth headers with STAS token"""
    return {"Authorization": f"Bearer {stas_token}"}


class TestStorageInfoAPI:
    """Tests for /api/maintenance/storage-info endpoint"""
    
    def test_storage_info_returns_total_size_kb(self, auth_headers):
        """P0: storage-info should return totals.total_size_kb"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify totals exist
        assert 'totals' in data, "Response should have 'totals' field"
        totals = data['totals']
        
        # Verify total_size_kb is returned
        assert 'total_size_kb' in totals, "totals should have total_size_kb"
        assert isinstance(totals['total_size_kb'], (int, float)), "total_size_kb should be numeric"
        assert totals['total_size_kb'] >= 0, "total_size_kb should be non-negative"
        
        print(f"Total size: {totals['total_size_kb']} KB")
    
    def test_storage_info_returns_transaction_size_kb(self, auth_headers):
        """P0: storage-info should return totals.transaction_size_kb"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        totals = data['totals']
        
        assert 'transaction_size_kb' in totals, "totals should have transaction_size_kb"
        assert isinstance(totals['transaction_size_kb'], (int, float)), "transaction_size_kb should be numeric"
        
        print(f"Transaction size: {totals['transaction_size_kb']} KB")
    
    def test_storage_info_returns_protected_size_kb(self, auth_headers):
        """P0: storage-info should return totals.protected_size_kb"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        totals = data['totals']
        
        assert 'protected_size_kb' in totals, "totals should have protected_size_kb"
        assert isinstance(totals['protected_size_kb'], (int, float)), "protected_size_kb should be numeric"
        
        print(f"Protected size: {totals['protected_size_kb']} KB")
    
    def test_storage_info_categories(self, auth_headers):
        """Storage-info should have categories breakdown"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'categories' in data, "Response should have 'categories' field"
        categories = data['categories']
        
        assert 'transactions' in categories, "categories should have 'transactions'"
        assert 'protected' in categories, "categories should have 'protected'"
        
        print(f"Transaction collections: {categories['transactions']['collections']}")
        print(f"Protected collections: {categories['protected']['collections']}")
    
    def test_storage_info_collections_detail(self, auth_headers):
        """Storage-info should list individual collections with sizes"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'collections' in data, "Response should have 'collections' field"
        collections = data['collections']
        
        # Should have multiple collections
        assert len(collections) > 0, "Should have at least one collection"
        
        # Each collection should have size info
        for coll_name, coll_info in collections.items():
            assert 'documents' in coll_info, f"Collection {coll_name} should have documents count"
            assert 'estimated_size_kb' in coll_info, f"Collection {coll_name} should have estimated_size_kb"
            print(f"  {coll_name}: {coll_info['documents']} docs, {coll_info['estimated_size_kb']} KB")
    
    def test_storage_info_requires_stas_role(self):
        """Storage-info endpoint requires STAS role"""
        # Try without auth
        resp = requests.get(f"{BASE_URL}/api/maintenance/storage-info")
        assert resp.status_code == 401 or resp.status_code == 403
        
        # Try with non-STAS user
        emp_resp = requests.post(f"{BASE_URL}/api/auth/switch/46c9dd1a-7f0f-584b-9bab-b37b949afece")  # Employee user
        if emp_resp.status_code == 200:
            emp_token = emp_resp.json()['token']
            resp = requests.get(
                f"{BASE_URL}/api/maintenance/storage-info", 
                headers={"Authorization": f"Bearer {emp_token}"}
            )
            assert resp.status_code == 403, "Non-STAS users should be denied"


class TestArchivesUploadAPI:
    """Tests for /api/maintenance/archives/upload endpoint"""
    
    def test_upload_endpoint_exists(self, auth_headers):
        """P0: Upload endpoint should exist"""
        # Create a minimal valid archive JSON
        archive_data = {
            "id": "TEST-ARCHIVE-001",
            "name": "Test Archive",
            "collections": {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(archive_data, f)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test_archive.json', f, 'application/json')}
                # Just check endpoint responds (we won't actually restore since it's destructive)
                resp = requests.post(
                    f"{BASE_URL}/api/maintenance/archives/upload",
                    headers=auth_headers,
                    files=files
                )
            
            # Should either succeed (200) or fail validation (400) - not 404
            assert resp.status_code != 404, "Upload endpoint should exist"
            print(f"Upload endpoint response: {resp.status_code}")
        finally:
            os.unlink(temp_path)
    
    def test_upload_rejects_non_json(self, auth_headers):
        """Upload should reject non-JSON files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not JSON")
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                resp = requests.post(
                    f"{BASE_URL}/api/maintenance/archives/upload",
                    headers=auth_headers,
                    files=files
                )
            
            # Should be rejected (either by file extension check or content validation)
            assert resp.status_code in [400, 422], f"Expected 400/422, got {resp.status_code}"
            print(f"Non-JSON rejection: {resp.status_code}")
        finally:
            os.unlink(temp_path)
    
    def test_upload_requires_auth(self):
        """Upload endpoint requires authentication"""
        archive_data = {"collections": {}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(archive_data, f)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                files = {'file': ('test.json', f, 'application/json')}
                resp = requests.post(
                    f"{BASE_URL}/api/maintenance/archives/upload",
                    files=files
                )
            
            assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        finally:
            os.unlink(temp_path)


class TestArchiveCRUD:
    """Tests for archive CRUD operations"""
    
    def test_list_archives(self, auth_headers):
        """Can list archives"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/archives", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'archives' in data
        assert 'total' in data
        print(f"Current archives: {data['total']}")
    
    def test_create_archive(self, auth_headers):
        """Can create a full archive"""
        resp = requests.post(
            f"{BASE_URL}/api/maintenance/archive-full",
            headers=auth_headers,
            json={"name": "TEST-Archive", "description": "Testing archive creation"}
        )
        
        assert resp.status_code == 200, f"Failed to create archive: {resp.text}"
        data = resp.json()
        
        assert 'archive_id' in data
        assert 'stats' in data
        print(f"Created archive: {data['archive_id']}, docs: {data['stats']['total_documents']}")
        
        return data['archive_id']
    
    def test_download_archive(self, auth_headers):
        """Can download an archive as JSON"""
        # First create an archive
        create_resp = requests.post(
            f"{BASE_URL}/api/maintenance/archive-full",
            headers=auth_headers,
            json={"name": "TEST-Download-Archive", "description": "For download test"}
        )
        
        if create_resp.status_code != 200:
            pytest.skip("Could not create archive for download test")
        
        archive_id = create_resp.json()['archive_id']
        
        # Download it
        download_resp = requests.get(
            f"{BASE_URL}/api/maintenance/archives/{archive_id}/download",
            headers=auth_headers
        )
        
        assert download_resp.status_code == 200
        data = download_resp.json()
        
        assert 'collections' in data, "Downloaded archive should have collections"
        assert 'id' in data, "Downloaded archive should have id"
        print(f"Downloaded archive with {len(data.get('collections', {}))} collections")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/maintenance/archives/{archive_id}", headers=auth_headers)


class TestMaintenanceLogs:
    """Tests for maintenance logs"""
    
    def test_get_logs(self, auth_headers):
        """Can retrieve maintenance logs"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/logs", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'logs' in data
        assert 'total' in data
        print(f"Maintenance logs: {data['total']}")


class TestCollectionsInfo:
    """Tests for collections info endpoint"""
    
    def test_get_collections_info(self, auth_headers):
        """Can get collections classification info"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/collections-info", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'transaction_collections' in data
        assert 'protected_collections' in data
        assert 'all_collections' in data
        
        print(f"Transaction collections: {data['transaction_collections']['count']}")
        print(f"Protected collections: {data['protected_collections']['count']}")


class TestDateFormatEndpoints:
    """Test that date fields are present in API responses for date format verification"""
    
    def test_transactions_have_created_at(self, auth_headers):
        """Transactions should have created_at timestamp for date formatting"""
        resp = requests.get(f"{BASE_URL}/api/transactions", headers=auth_headers)
        
        assert resp.status_code == 200
        data = resp.json()
        
        if len(data) > 0:
            tx = data[0]
            assert 'created_at' in tx, "Transaction should have created_at field"
            print(f"Transaction date example: {tx['created_at']}")
    
    def test_archives_have_created_at(self, auth_headers):
        """Archives should have created_at timestamp for date formatting"""
        # Create a test archive first
        create_resp = requests.post(
            f"{BASE_URL}/api/maintenance/archive-full",
            headers=auth_headers,
            json={"name": "TEST-Date-Archive"}
        )
        
        if create_resp.status_code != 200:
            pytest.skip("Could not create archive")
        
        archive_id = create_resp.json()['archive_id']
        
        # Get archives list
        list_resp = requests.get(f"{BASE_URL}/api/maintenance/archives", headers=auth_headers)
        assert list_resp.status_code == 200
        
        archives = list_resp.json().get('archives', [])
        if len(archives) > 0:
            archive = archives[0]
            assert 'created_at' in archive, "Archive should have created_at field"
            print(f"Archive date example: {archive['created_at']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/maintenance/archives/{archive_id}", headers=auth_headers)
    
    def test_maintenance_logs_have_timestamp(self, auth_headers):
        """Maintenance logs should have timestamp for date formatting"""
        resp = requests.get(f"{BASE_URL}/api/maintenance/logs", headers=auth_headers)
        
        assert resp.status_code == 200
        logs = resp.json().get('logs', [])
        
        if len(logs) > 0:
            log = logs[0]
            assert 'timestamp' in log, "Log should have timestamp field"
            print(f"Log timestamp example: {log['timestamp']}")
    
    def test_holidays_have_date_field(self, auth_headers):
        """Holidays should have date field for Hijri formatting"""
        resp = requests.get(f"{BASE_URL}/api/leave/holidays", headers=auth_headers)
        
        assert resp.status_code == 200
        holidays = resp.json()
        
        if len(holidays) > 0:
            holiday = holidays[0]
            assert 'date' in holiday, "Holiday should have date field"
            print(f"Holiday date example: {holiday['date']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
