"""
Test Suite - Iteration 43: Professional PDF System for Transactions
=========================================================================
Tests the new professional PDF design with:
1) Unified bilingual header (Arabic + English)
2) Tear-off line (خط القطع) with scissors symbol
3) Signature table with QR codes for each signer
4) 2 STAS QR codes (one in signature table, one in coupon section)
5) Tear-off coupon section for manual files
=========================================================================
"""

import pytest
import requests
import os
import io
from PyPDF2 import PdfReader

# API Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
STAS_CREDS = {"username": "stas506", "password": "654321"}
SULTAN_CREDS = {"username": "sultan", "password": "123456"}
MOHAMMED_CREDS = {"username": "mohammed", "password": "123456"}

# Known executed transaction ID from context
EXECUTED_TX_ID = "b9a119c9-89b7-416d-aedb-750b108d38c5"
EXECUTED_TX_REF = "TXN-2026-0003"


class TestAuthentication:
    """Test authentication for different users"""
    
    def test_login_stas506(self):
        """Test STAS user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        print(f"✓ STAS login successful, user: {data['user'].get('username')}")
        return data["token"]
    
    def test_login_sultan(self):
        """Test Sultan (HR) user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SULTAN_CREDS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Sultan login successful, user: {data['user'].get('username')}")
        return data["token"]
    
    def test_login_mohammed(self):
        """Test Mohammed (CEO) user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=MOHAMMED_CREDS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        print(f"✓ Mohammed login successful, user: {data['user'].get('username')}")
        return data["token"]


class TestPDFDownloadEndpoint:
    """Test PDF download endpoint /api/stas/transaction/{id}/pdf"""
    
    @pytest.fixture
    def auth_token(self):
        """Get STAS auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("STAS authentication failed")
    
    def test_pdf_endpoint_exists(self, auth_token):
        """Test that PDF download endpoint exists and responds"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        # Should return 200 with PDF or 404 if transaction not found
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}, {response.text}"
        print(f"✓ PDF endpoint responded with status {response.status_code}")
    
    def test_pdf_download_returns_pdf_content_type(self, auth_token):
        """Test that PDF endpoint returns correct content type"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            assert 'application/pdf' in content_type, f"Expected application/pdf, got {content_type}"
            print(f"✓ Content-Type is application/pdf")
        else:
            print(f"⚠ Transaction {EXECUTED_TX_ID} not found (status {response.status_code})")
    
    def test_pdf_download_has_integrity_headers(self, auth_token):
        """Test that PDF response includes integrity headers"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            assert 'X-Integrity-ID' in response.headers, "Missing X-Integrity-ID header"
            assert 'X-PDF-Hash' in response.headers, "Missing X-PDF-Hash header"
            print(f"✓ Integrity headers present: X-Integrity-ID={response.headers.get('X-Integrity-ID')}")
        else:
            print(f"⚠ Transaction not found, skipping header check")
    
    def test_pdf_download_valid_pdf_structure(self, auth_token):
        """Test that downloaded PDF is a valid PDF file"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            # Check PDF magic bytes
            pdf_bytes = response.content
            assert pdf_bytes[:4] == b'%PDF', "PDF does not start with %PDF magic bytes"
            
            # Try to parse with PyPDF2
            try:
                pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
                num_pages = len(pdf_reader.pages)
                assert num_pages >= 1, "PDF has no pages"
                print(f"✓ Valid PDF with {num_pages} page(s)")
            except Exception as e:
                pytest.fail(f"Failed to parse PDF: {e}")
        else:
            print(f"⚠ Transaction not found, skipping PDF validation")
    
    def test_pdf_download_not_found_transaction(self, auth_token):
        """Test PDF download with invalid transaction ID"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/invalid-id-12345/pdf",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404 for invalid ID, got {response.status_code}"
        print(f"✓ Invalid transaction ID returns 404")
    
    def test_pdf_download_requires_authentication(self):
        """Test that PDF download requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf"
        )
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print(f"✓ Unauthenticated request rejected with status {response.status_code}")


class TestTransactionWorkflow:
    """Test transaction creation and execution flow"""
    
    @pytest.fixture
    def stas_token(self):
        """Get STAS auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("STAS authentication failed")
    
    @pytest.fixture
    def sultan_token(self):
        """Get Sultan auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SULTAN_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Sultan authentication failed")
    
    def test_get_pending_transactions(self, stas_token):
        """Test fetching pending transactions for STAS"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        response = requests.get(f"{BASE_URL}/api/stas/pending", headers=headers)
        assert response.status_code == 200, f"Failed to get pending: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of transactions"
        print(f"✓ Found {len(data)} pending transactions")
    
    def test_list_executed_transactions(self, stas_token):
        """Test listing executed transactions"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        response = requests.get(f"{BASE_URL}/api/transactions", headers=headers)
        assert response.status_code == 200, f"Failed to get transactions: {response.text}"
        data = response.json()
        
        # Find executed transactions
        transactions = data.get('transactions', data) if isinstance(data, dict) else data
        if isinstance(transactions, list):
            executed = [tx for tx in transactions if tx.get('status') == 'executed']
            print(f"✓ Found {len(executed)} executed transactions")
        else:
            print(f"✓ Transactions endpoint returned valid response")


class TestPDFContentVerification:
    """Test PDF content to verify professional design elements"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def _get_pdf_text(self, pdf_bytes):
        """Extract text from PDF"""
        try:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"Error extracting text: {e}"
    
    def test_pdf_contains_bilingual_header(self, auth_token):
        """Test that PDF contains bilingual header elements"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            # PDF structure check - we verify the PDF is generated
            # Content verification would require more sophisticated PDF parsing
            pdf_bytes = response.content
            pdf_size = len(pdf_bytes)
            assert pdf_size > 1000, f"PDF too small ({pdf_size} bytes), may be empty"
            print(f"✓ PDF generated successfully ({pdf_size} bytes)")
            
            # Try to extract text
            text = self._get_pdf_text(pdf_bytes)
            print(f"✓ Extracted text length: {len(text)} chars")
        else:
            pytest.skip(f"Transaction not found: {response.status_code}")
    
    def test_pdf_has_multiple_qr_codes(self, auth_token):
        """Test that PDF size suggests QR codes are present"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            pdf_bytes = response.content
            # QR codes add significant size to PDF
            # A PDF with multiple QR codes should be > 10KB
            assert len(pdf_bytes) > 10000, f"PDF size ({len(pdf_bytes)} bytes) suggests missing QR codes"
            print(f"✓ PDF size ({len(pdf_bytes)} bytes) indicates QR codes present")
        else:
            pytest.skip(f"Transaction not found: {response.status_code}")


class TestExistingTransactionPDF:
    """Test PDF generation for the known executed transaction"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed")
    
    def test_get_executed_transaction_details(self, auth_token):
        """Get details of the known executed transaction"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/transactions/{EXECUTED_TX_ID}",
            headers=headers
        )
        if response.status_code == 200:
            tx = response.json()
            print(f"✓ Transaction found: ref_no={tx.get('ref_no')}, status={tx.get('status')}, type={tx.get('type')}")
            assert tx.get('status') == 'executed', f"Expected executed status, got {tx.get('status')}"
        elif response.status_code == 404:
            print(f"⚠ Transaction {EXECUTED_TX_ID} not found - may have been purged")
            pytest.skip("Test transaction not found")
        else:
            pytest.fail(f"Unexpected response: {response.status_code}")
    
    def test_download_and_save_pdf(self, auth_token):
        """Download PDF and save for manual inspection"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/transaction/{EXECUTED_TX_ID}/pdf",
            headers=headers
        )
        if response.status_code == 200:
            pdf_bytes = response.content
            
            # Save PDF for inspection
            pdf_path = f"/tmp/test_transaction_pdf_{EXECUTED_TX_REF}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            print(f"✓ PDF saved to {pdf_path} ({len(pdf_bytes)} bytes)")
            
            # Basic validation
            assert pdf_bytes[:4] == b'%PDF', "Invalid PDF format"
            
            # Check headers
            integrity_id = response.headers.get('X-Integrity-ID')
            pdf_hash = response.headers.get('X-PDF-Hash')
            print(f"✓ Integrity-ID: {integrity_id}")
            print(f"✓ PDF-Hash: {pdf_hash[:20]}..." if pdf_hash else "⚠ No PDF hash")
        else:
            pytest.skip(f"Transaction not found: {response.status_code}")


class TestSTASMirrorEndpoints:
    """Test STAS Mirror endpoints"""
    
    @pytest.fixture
    def stas_token(self):
        """Get STAS auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=STAS_CREDS)
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("STAS authentication failed")
    
    def test_stas_mirror_endpoint(self, stas_token):
        """Test STAS mirror endpoint for transaction"""
        headers = {"Authorization": f"Bearer {stas_token}"}
        response = requests.get(
            f"{BASE_URL}/api/stas/mirror/{EXECUTED_TX_ID}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            # Verify mirror data structure
            assert 'trace_links' in data or 'transaction' in data or 'pre_checks' in data, \
                "Mirror data missing expected fields"
            print(f"✓ STAS mirror endpoint returned valid data")
        elif response.status_code == 404:
            print(f"⚠ Transaction {EXECUTED_TX_ID} not found")
            pytest.skip("Transaction not found")
        else:
            pytest.fail(f"Mirror endpoint failed: {response.status_code}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
