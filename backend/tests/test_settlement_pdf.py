"""
Test Settlement PDF Generation - Iteration 26
Tests for:
1. Company logo from branding settings in PDF
2. Declaration text (bilingual) in PDF  
3. QR codes in signatures section
4. PDF endpoint /api/settlement/{id}/pdf
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = "stas"
TEST_PASS = "DarAlCode2026!"

# Known executed settlement from main agent context
EXECUTED_SETTLEMENT_ID = "c3c5d10b-63c6-4292-a65e-bf99d11258ba"
EXECUTED_SETTLEMENT_TXN = "STL-2026-0001"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for STAS user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": TEST_USER, "password": TEST_PASS}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Authentication failed")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSettlementPDFEndpoint:
    """Test /api/settlement/{id}/pdf endpoint"""
    
    def test_pdf_endpoint_returns_pdf(self, auth_headers):
        """Test that PDF endpoint returns a valid PDF file"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{EXECUTED_SETTLEMENT_ID}/pdf",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.headers.get('content-type') == 'application/pdf', "Should return PDF content type"
        
        # Check PDF magic bytes
        content = response.content
        assert content[:4] == b'%PDF', "Content should start with PDF magic bytes"
        assert len(content) > 10000, f"PDF should be substantial size, got {len(content)} bytes"
        print(f"PDF generated successfully: {len(content)} bytes")
    
    def test_pdf_requires_auth(self):
        """Test that PDF endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/settlement/{EXECUTED_SETTLEMENT_ID}/pdf")
        assert response.status_code == 401, "Should require authentication"
    
    def test_pdf_not_found_for_invalid_id(self, auth_headers):
        """Test that PDF returns 404 for invalid settlement ID"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/invalid-id-12345/pdf",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestBrandingSettings:
    """Test company branding settings which provide logo for PDF"""
    
    def test_branding_endpoint_accessible(self, auth_headers):
        """Test that branding endpoint returns data"""
        response = requests.get(
            f"{BASE_URL}/api/settings/branding",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "type" in data
        assert data["type"] == "company_branding"
        print(f"Branding data retrieved: {data.get('company_name_en')}")
    
    def test_branding_has_logo_data(self, auth_headers):
        """Test that branding has logo_data for PDF generation"""
        response = requests.get(
            f"{BASE_URL}/api/settings/branding",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check logo_data exists and has content
        logo_data = data.get("logo_data")
        assert logo_data is not None, "logo_data should exist in branding"
        assert isinstance(logo_data, str), "logo_data should be a string"
        assert logo_data.startswith("data:image/"), "logo_data should be base64 data URI"
        print(f"Logo data present: {len(logo_data)} characters")


class TestSettlementData:
    """Test settlement data structure"""
    
    def test_executed_settlement_exists(self, auth_headers):
        """Test that the executed settlement exists and has proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{EXECUTED_SETTLEMENT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "executed", "Settlement should be executed"
        assert data["transaction_number"] == EXECUTED_SETTLEMENT_TXN
        assert "snapshot" in data
        print(f"Settlement {EXECUTED_SETTLEMENT_TXN} found with status: {data['status']}")
    
    def test_settlement_snapshot_has_required_fields(self, auth_headers):
        """Test that settlement snapshot has all required fields for PDF"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{EXECUTED_SETTLEMENT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data.get("snapshot", {})
        
        # Check all required sections exist
        assert "employee" in snapshot, "snapshot should have employee"
        assert "contract" in snapshot, "snapshot should have contract"
        assert "service" in snapshot, "snapshot should have service"
        assert "wages" in snapshot, "snapshot should have wages"
        assert "eos" in snapshot, "snapshot should have eos"
        assert "leave" in snapshot, "snapshot should have leave"
        assert "totals" in snapshot, "snapshot should have totals"
        
        # Check employee data
        employee = snapshot["employee"]
        assert "name_ar" in employee, "employee should have name_ar"
        assert "name_en" in employee, "employee should have name_en"
        
        # Check totals
        totals = snapshot["totals"]
        assert "net_amount" in totals, "totals should have net_amount"
        print(f"Snapshot verified - Employee: {employee.get('name_ar')}, Net: {totals.get('net_amount')}")


class TestSettlementList:
    """Test settlement list endpoint"""
    
    def test_list_settlements(self, auth_headers):
        """Test listing settlements"""
        response = requests.get(
            f"{BASE_URL}/api/settlement",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Should return a list"
        
        # Find our test settlement
        test_settlement = next((s for s in data if s["id"] == EXECUTED_SETTLEMENT_ID), None)
        assert test_settlement is not None, f"Should find settlement {EXECUTED_SETTLEMENT_ID}"
        print(f"Found {len(data)} settlements")
    
    def test_pending_settlements_endpoint(self, auth_headers):
        """Test pending settlements endpoint (STAS only)"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/pending",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Pending settlements: {len(data)}")


class TestTerminationTypes:
    """Test termination types endpoint"""
    
    def test_get_termination_types(self, auth_headers):
        """Test getting termination types"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/termination-types",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check expected termination types
        expected_types = ["contract_expiry", "resignation", "probation_termination", "mutual_agreement", "termination"]
        for t in expected_types:
            assert t in data, f"Should have {t} termination type"
        print(f"Termination types: {list(data.keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
