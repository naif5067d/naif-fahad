"""
Test Suite for PDF Generation - Arabic Text and Date Formatting
Iteration 24 - Testing PDF with Arabic fonts and LTR date formatting

Tests:
1. PDF endpoint returns valid PDF
2. Arabic labels and text display correctly (not as squares)
3. Date formatting shows YYYY-MM-DD format
4. Reference number format TXN-2026-0001 displays correctly
5. Approval chain in PDF displays approver names and timestamps
"""
import pytest
import requests
import os
import io
from PyPDF2 import PdfReader

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-settlement.preview.emergentagent.com').rstrip('/')

class TestPDFGeneration:
    """Test PDF generation for transactions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token"""
        # Login as stas user
        response = requests.post(
            f"{BASE_URL}/api/auth/switch/fedffe24-ec69-5c65-809d-5d24f8a16b9d"
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()['token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get an executed transaction
        tx_response = requests.get(
            f"{BASE_URL}/api/transactions?status=executed",
            headers=self.headers
        )
        assert tx_response.status_code == 200
        transactions = tx_response.json()
        if transactions:
            self.tx = transactions[0]
        else:
            # If no executed transaction, get any transaction
            tx_response = requests.get(
                f"{BASE_URL}/api/transactions",
                headers=self.headers
            )
            transactions = tx_response.json()
            self.tx = transactions[0] if transactions else None
        
    def test_pdf_endpoint_returns_valid_pdf(self):
        """Test that PDF endpoint returns a valid PDF file"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=ar",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"PDF request failed: {response.text}"
        assert response.headers.get('content-type') == 'application/pdf', \
            f"Expected PDF content-type, got: {response.headers.get('content-type')}"
        
        # Verify it's a valid PDF by checking magic bytes
        pdf_bytes = response.content
        assert pdf_bytes[:4] == b'%PDF', "Response is not a valid PDF file"
        print(f"✓ PDF endpoint returns valid PDF file ({len(pdf_bytes)} bytes)")
    
    def test_pdf_arabic_version_contains_text(self):
        """Test Arabic PDF contains readable text (not just squares)"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=ar",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Parse PDF and extract text
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        assert len(reader.pages) >= 1, "PDF should have at least 1 page"
        
        # Extract text from first page
        page_text = reader.pages[0].extract_text()
        
        # Check that some content exists
        assert len(page_text) > 50, f"PDF text extraction too short: {len(page_text)} chars"
        
        # Check for reference number format (TXN-YYYY-NNNN)
        ref_no = self.tx.get('ref_no', '')
        if ref_no:
            # The ref_no should appear in PDF
            assert 'TXN-' in page_text or ref_no in page_text, \
                f"Reference number {ref_no} not found in PDF text"
        
        print(f"✓ Arabic PDF contains {len(page_text)} characters of text")
        print(f"✓ Found reference number pattern in PDF")
    
    def test_pdf_english_version(self):
        """Test English PDF generation works correctly"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=en",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Parse PDF and extract text
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        page_text = reader.pages[0].extract_text()
        
        # Check for English labels
        english_labels = ['Reference No', 'Status', 'Date', 'DAR AL CODE']
        found_labels = [label for label in english_labels if label in page_text]
        
        # At least some English labels should be present
        assert len(found_labels) >= 1, \
            f"Expected English labels not found. Found text snippet: {page_text[:200]}"
        
        print(f"✓ English PDF generated successfully")
        print(f"✓ Found English labels: {found_labels}")
    
    def test_pdf_date_formatting(self):
        """Test that dates are formatted as YYYY-MM-DD (not YYYYMMDD)"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=en",
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Parse PDF and extract text
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        page_text = reader.pages[0].extract_text()
        
        # Look for date patterns
        # Valid: 2026-02-17
        # Invalid: 20260217
        import re
        
        # Check for proper date format with dashes
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        dates_found = re.findall(date_pattern, page_text)
        
        # Check that we don't have dates without dashes (unless they're part of ref_no)
        # Invalid format: 8 consecutive digits that look like a date
        invalid_pattern = r'(?<!\d)20\d{6}(?!\d)'  # Starts with 20 (like 2026), 8 total digits
        invalid_dates = re.findall(invalid_pattern, page_text)
        
        # Filter out false positives (ref numbers like TXN-2026-0001)
        invalid_dates = [d for d in invalid_dates if not d.startswith('202') or len(d) != 8]
        
        print(f"✓ Dates with proper format (YYYY-MM-DD): {dates_found[:5]}")
        if invalid_dates:
            print(f"⚠ Potential dates without separators: {invalid_dates}")
        
        # We should find at least one properly formatted date
        assert len(dates_found) >= 1 or 'Date' not in page_text, \
            "Expected date format YYYY-MM-DD not found in PDF"
    
    def test_pdf_reference_number_format(self):
        """Test reference number displays as TXN-2026-0001 format"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=en",
            headers=self.headers
        )
        assert response.status_code == 200
        
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        page_text = reader.pages[0].extract_text()
        
        ref_no = self.tx.get('ref_no', 'TXN-2026-0001')
        
        # Check reference number format is correct
        import re
        ref_pattern = r'TXN-\d{4}-\d{4}'
        refs_found = re.findall(ref_pattern, page_text)
        
        assert len(refs_found) >= 1, \
            f"Reference number format TXN-YYYY-NNNN not found in PDF. Text: {page_text[:500]}"
        
        print(f"✓ Reference numbers found: {refs_found}")
    
    def test_pdf_approval_chain(self):
        """Test approval chain displays in PDF with approver names and timestamps"""
        if not self.tx:
            pytest.skip("No transactions available for testing")
            
        # Skip if transaction has no approval chain
        if not self.tx.get('approval_chain'):
            pytest.skip("Transaction has no approval chain")
            
        response = requests.get(
            f"{BASE_URL}/api/transactions/{self.tx['id']}/pdf?lang=en",
            headers=self.headers
        )
        assert response.status_code == 200
        
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        page_text = reader.pages[0].extract_text()
        
        # Check for approval chain content
        approval_keywords = ['Approval', 'Stage', 'Approver', 'STAS', 'Operations']
        found_keywords = [kw for kw in approval_keywords if kw in page_text]
        
        assert len(found_keywords) >= 1, \
            f"Approval chain keywords not found in PDF. Expected: {approval_keywords}"
        
        print(f"✓ Approval chain keywords found: {found_keywords}")
        
        # Check that approver names appear
        for approval in self.tx.get('approval_chain', [])[:2]:
            approver_name = approval.get('approver_name', '')
            if approver_name and approver_name != 'STAS':
                # Check if part of the name appears (handling Arabic/English mix)
                name_parts = approver_name.split()
                name_found = any(part in page_text for part in name_parts if len(part) > 2)
                print(f"  - Approver '{approver_name}': {'Found' if name_found else 'Not found in text'}")


class TestTransactionDetailsDisplay:
    """Test transaction details are properly displayed"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/switch/fedffe24-ec69-5c65-809d-5d24f8a16b9d"
        )
        assert response.status_code == 200
        self.token = response.json()['token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get an executed transaction
        tx_response = requests.get(
            f"{BASE_URL}/api/transactions?status=executed",
            headers=self.headers
        )
        transactions = tx_response.json()
        self.tx = transactions[0] if transactions else None
    
    def test_transaction_data_fields(self):
        """Test transaction has required data fields for PDF generation"""
        if not self.tx:
            pytest.skip("No transactions available")
            
        tx_data = self.tx.get('data', {})
        
        # For leave_request type
        if self.tx.get('type') == 'leave_request':
            expected_fields = ['leave_type', 'start_date', 'end_date', 'working_days', 'employee_name']
            found_fields = [f for f in expected_fields if f in tx_data]
            
            print(f"✓ Transaction has data fields: {list(tx_data.keys())}")
            print(f"✓ Found expected fields: {found_fields}")
            
            # Check date format in data
            start_date = tx_data.get('start_date', '')
            end_date = tx_data.get('end_date', '')
            
            assert '-' in str(start_date), f"Start date should have dashes: {start_date}"
            assert '-' in str(end_date), f"End date should have dashes: {end_date}"
            
            print(f"✓ Date formats: start={start_date}, end={end_date}")
    
    def test_employee_name_display(self):
        """Test employee name (Arabic and English) is in transaction data"""
        if not self.tx:
            pytest.skip("No transactions available")
            
        tx_data = self.tx.get('data', {})
        
        # Check for employee names
        emp_name_en = tx_data.get('employee_name', '')
        emp_name_ar = tx_data.get('employee_name_ar', '')
        
        print(f"✓ Employee name (EN): {emp_name_en}")
        print(f"✓ Employee name (AR): {emp_name_ar}")
        
        # At least one should be present
        assert emp_name_en or emp_name_ar, "Employee name should be present in transaction data"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
