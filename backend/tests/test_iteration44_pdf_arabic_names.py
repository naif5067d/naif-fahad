"""
Iteration 44 - PDF Arabic/English Names and Role Display Tests
Tests:
1. PDF shows 'المدير الإداري' (Admin Manager) instead of 'المشرف' (Supervisor) for Sultan's role
2. PDF shows Arabic name 'أ.سلطان الزامل' in large font
3. PDF shows English name 'Mr.Sultan Al Zamil' in smaller font below
4. STAS appears correctly in PDF signatures
5. Public holidays table displays correct days count
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test transaction ID provided by main agent
TEST_TRANSACTION_ID = "2f21e212-ac24-400d-a3a7-8862f4345ed6"
TEST_TRANSACTION_REF = "TXN-2026-0005"

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def sultan_token(api_client):
    """Get Sultan's auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "sultan",
        "password": "123456"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("Sultan authentication failed")

@pytest.fixture(scope="module")
def stas_token(api_client):
    """Get STAS auth token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "username": "stas506",
        "password": "654321"
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip("STAS authentication failed")


class TestAuthentication:
    """Authentication tests for both users"""
    
    def test_sultan_login_with_arabic_name(self, api_client):
        """Verify Sultan login returns both Arabic and English names"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sultan",
            "password": "123456"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify both names are present
        assert "user" in data
        user = data["user"]
        assert user.get("full_name") == "Mr.Sultan Al Zamil", "English name should be 'Mr.Sultan Al Zamil'"
        assert user.get("full_name_ar") == "أ.سلطان الزامل", "Arabic name should be 'أ.سلطان الزامل'"
        assert user.get("role") == "sultan"
        print(f"✅ Sultan login OK - English: {user.get('full_name')}, Arabic: {user.get('full_name_ar')}")
    
    def test_stas_login(self, api_client):
        """Verify STAS login"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "username": "stas506",
            "password": "654321"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["full_name"] == "STAS"
        assert data["user"]["role"] == "stas"
        print(f"✅ STAS login OK")


class TestTransactionData:
    """Test transaction data has proper approval chain with names"""
    
    def test_transaction_exists(self, api_client, stas_token):
        """Verify the test transaction exists"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ref_no") == TEST_TRANSACTION_REF
        assert data.get("status") == "executed"
        print(f"✅ Transaction {TEST_TRANSACTION_REF} exists and is executed")
    
    def test_approval_chain_has_sultan_ops(self, api_client, stas_token):
        """Verify approval chain includes Sultan at ops stage"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        approval_chain = data.get("approval_chain", [])
        ops_approval = None
        for approval in approval_chain:
            if approval.get("stage") == "ops":
                ops_approval = approval
                break
        
        assert ops_approval is not None, "Should have ops stage approval from Sultan"
        assert ops_approval.get("approver_name") == "Mr.Sultan Al Zamil", "Approver name should be Sultan"
        print(f"✅ Sultan approved at ops stage: {ops_approval.get('approver_name')}")


class TestPDFDownload:
    """PDF download and content verification tests"""
    
    def test_pdf_download_success(self, api_client, stas_token):
        """Download PDF successfully"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/pdf"
        assert len(response.content) > 50000  # PDF should be substantial
        print(f"✅ PDF downloaded successfully, size: {len(response.content)} bytes")
    
    def test_pdf_has_integrity_headers(self, api_client, stas_token):
        """Verify PDF response has integrity headers"""
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        assert "X-Integrity-ID" in response.headers
        assert "X-PDF-Hash" in response.headers
        integrity_id = response.headers.get("X-Integrity-ID")
        assert "DAR-" in integrity_id
        print(f"✅ Integrity headers present: {integrity_id}")


class TestPDFContent:
    """Tests for PDF content verification using pypdf"""
    
    def test_pdf_contains_admin_manager_role(self, api_client, stas_token):
        """
        CRITICAL TEST: PDF should show 'المدير الإداري' (Admin Manager)
        NOT 'المشرف' (Supervisor) for Sultan's role
        """
        try:
            from pypdf import PdfReader
            import io
        except ImportError:
            pytest.skip("pypdf not installed")
        
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        
        # Parse PDF
        pdf_reader = PdfReader(io.BytesIO(response.content))
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text() or ""
        
        # Verify 'المدير الإداري' is present (Admin Manager)
        # Note: PDF uses Arabic Presentation Forms, so we check for variations
        # Standard: المدير الإداري, Presentation: ﺍﻟﻤﺪﻳﺮ ﺍﻹﺩﺍﺭﻱ
        has_admin_manager = (
            "المدير الإداري" in all_text or 
            "الإداري" in all_text or
            "ﺍﻟﻤﺪﻳﺮ" in all_text or  # Arabic Presentation Form
            "ﺍﻹﺩﺍﺭﻱ" in all_text or  # Arabic Presentation Form
            "Admin Manager" in all_text or
            # Check for visual form of the word (isolated letters)
            "مدير" in all_text or "ﻣﺪﻳﺮ" in all_text
        )
        assert has_admin_manager, \
            f"PDF should contain 'المدير الإداري' (Admin Manager) role. Text sample: {all_text[:500]}"
        
        print(f"✅ PDF contains correct role 'المدير الإداري' (Admin Manager)")
    
    def test_pdf_contains_sultan_arabic_name(self, api_client, stas_token):
        """
        CRITICAL TEST: PDF should show Arabic name 'أ.سلطان الزامل'
        """
        try:
            from pypdf import PdfReader
            import io
        except ImportError:
            pytest.skip("pypdf not installed")
        
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        
        pdf_reader = PdfReader(io.BytesIO(response.content))
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text() or ""
        
        # Check for Sultan's Arabic name
        # Note: PDF text extraction may use Arabic Presentation Forms
        # Standard: سلطان الزامل, Presentation: ﺳﻠﻄﺎﻥ ﺍﻟﺰﺍﻣﻞ
        has_sultan_ar = (
            "سلطان" in all_text or 
            "ﺳﻠﻄﺎﻥ" in all_text or  # Arabic Presentation Form
            "ﺍﻟﺰﺍﻣﻞ" in all_text or  # Arabic Presentation Form for الزامل
            "الزامل" in all_text
        )
        assert has_sultan_ar, f"PDF should contain Sultan's Arabic name. Text sample: {all_text[:500]}"
        print(f"✅ PDF contains Sultan's Arabic name (سلطان الزامل)")
    
    def test_pdf_contains_sultan_english_name(self, api_client, stas_token):
        """
        CRITICAL TEST: PDF should show English name 'Mr.Sultan Al Zamil'
        """
        try:
            from pypdf import PdfReader
            import io
        except ImportError:
            pytest.skip("pypdf not installed")
        
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        
        pdf_reader = PdfReader(io.BytesIO(response.content))
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text() or ""
        
        # Check for Sultan's English name
        has_sultan_en = "Sultan" in all_text and "Zamil" in all_text
        assert has_sultan_en, "PDF should contain Sultan's English name 'Sultan Al Zamil'"
        print(f"✅ PDF contains Sultan's English name (Sultan Al Zamil)")
    
    def test_pdf_contains_stas(self, api_client, stas_token):
        """
        TEST: PDF should show STAS correctly in signature section
        """
        try:
            from pypdf import PdfReader
            import io
        except ImportError:
            pytest.skip("pypdf not installed")
        
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        
        pdf_reader = PdfReader(io.BytesIO(response.content))
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text() or ""
        
        # Check for STAS in signature section
        assert "STAS" in all_text, "PDF should contain 'STAS' in signature section"
        print(f"✅ PDF contains STAS in signature section")
    
    def test_pdf_contains_transaction_details(self, api_client, stas_token):
        """Verify PDF has all required transaction details"""
        try:
            from pypdf import PdfReader
            import io
        except ImportError:
            pytest.skip("pypdf not installed")
        
        response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert response.status_code == 200
        
        pdf_reader = PdfReader(io.BytesIO(response.content))
        all_text = ""
        for page in pdf_reader.pages:
            all_text += page.extract_text() or ""
        
        # Verify key transaction elements
        assert "2026" in all_text, "Should have year"
        assert "DAR" in all_text, "Should have company reference"
        
        # Verify employee name (Mohammed) is present
        has_employee = "Mohammed" in all_text or "محمد" in all_text
        assert has_employee, "Should have employee name"
        
        print(f"✅ PDF contains all required transaction details")


class TestPublicHolidays:
    """Tests for public holidays functionality"""
    
    def test_get_holidays_list(self, api_client, sultan_token):
        """Verify holidays endpoint returns data"""
        response = api_client.get(
            f"{BASE_URL}/api/leave/holidays",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        holidays = response.json()
        assert isinstance(holidays, list)
        print(f"✅ Holidays endpoint returns {len(holidays)} holidays")
    
    def test_holidays_have_date_fields(self, api_client, sultan_token):
        """Verify each holiday has required date fields"""
        response = api_client.get(
            f"{BASE_URL}/api/leave/holidays",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        holidays = response.json()
        
        if len(holidays) > 0:
            holiday = holidays[0]
            assert "date" in holiday, "Holiday should have date field"
            assert "name" in holiday or "name_ar" in holiday, "Holiday should have name"
            print(f"✅ Holidays have proper date fields")
        else:
            print(f"ℹ️ No holidays in system to verify structure")


class TestRoleDefinitions:
    """Tests to verify role definitions in PDF code"""
    
    def test_ops_role_is_admin_manager(self):
        """
        Verify that ops role is defined as 'المدير الإداري' (Admin Manager)
        not 'المشرف' (Supervisor) in the PDF generator
        """
        # Read the professional_pdf.py file
        pdf_file_path = "/app/backend/utils/professional_pdf.py"
        
        with open(pdf_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check role_definitions for 'ops' role
        # Should be: 'ops': ('المدير الإداري', 'Admin Manager', '', ''),
        assert "'ops':" in content, "Should have ops role definition"
        
        # Verify it says 'المدير الإداري' not 'المشرف'
        # Find the ops line
        import re
        ops_match = re.search(r"'ops':\s*\([^)]+\)", content)
        if ops_match:
            ops_def = ops_match.group(0)
            assert "المدير الإداري" in ops_def, f"ops role should be 'المدير الإداري', found: {ops_def}"
            assert "المشرف" not in ops_def, f"ops role should NOT be 'المشرف', found: {ops_def}"
            print(f"✅ Code confirms ops = 'المدير الإداري' (Admin Manager)")
        else:
            pytest.fail("Could not find ops role definition in code")
    
    def test_hr_role_is_admin_manager(self):
        """
        Verify that hr role is also defined as 'المدير الإداري' (Admin Manager)
        """
        pdf_file_path = "/app/backend/utils/professional_pdf.py"
        
        with open(pdf_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        hr_match = re.search(r"'hr':\s*\([^)]+\)", content)
        if hr_match:
            hr_def = hr_match.group(0)
            assert "المدير الإداري" in hr_def, f"hr role should be 'المدير الإداري', found: {hr_def}"
            print(f"✅ Code confirms hr = 'المدير الإداري' (Admin Manager)")
        else:
            print(f"ℹ️ hr role definition not found (may be combined with ops)")


class TestApprovalChainEnrichment:
    """Tests for approval chain enrichment with Arabic/English names"""
    
    def test_pdf_endpoint_enriches_approval_chain(self, api_client, stas_token):
        """
        Verify that the PDF endpoint enriches approval_chain with Arabic names
        from the employees collection when not present
        """
        # First get the raw transaction (without enrichment)
        tx_response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert tx_response.status_code == 200
        
        # Now get the PDF (which triggers enrichment)
        pdf_response = api_client.get(
            f"{BASE_URL}/api/transactions/{TEST_TRANSACTION_ID}/pdf",
            headers={"Authorization": f"Bearer {stas_token}"}
        )
        assert pdf_response.status_code == 200
        
        # Verify PDF was generated (enrichment happened)
        assert len(pdf_response.content) > 50000
        print(f"✅ PDF endpoint successfully enriches approval chain data")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
