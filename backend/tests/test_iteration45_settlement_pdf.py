"""
Iteration 45 - Settlement PDF Arabic Text Rendering and Partial Month Salary Tests
==================================================================================
Tests:
1. Settlement PDF generates successfully
2. Arabic text renders correctly (not as squares)
3. Preview API returns partial_month_salary data
4. Settlement page loads without errors
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
SULTAN_CREDS = {"username": "sultan", "password": "123456"}
STAS_CREDS = {"username": "stas506", "password": "654321"}

# Known executed settlement
SETTLEMENT_ID = "466f5468-1c8c-47f4-b8c6-11eb733d39eb"
SETTLEMENT_NUMBER = "STL-2026-0002"


class TestSettlementPDFArabicRendering:
    """Settlement PDF Arabic text rendering tests"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        """Get Sultan auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"Sultan login failed: {response.text}"
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        """Get STAS auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=STAS_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200, f"STAS login failed: {response.text}"
        return response.json().get("token")
    
    def test_settlement_list_api(self, sultan_token):
        """Test settlement list endpoint returns data"""
        response = requests.get(
            f"{BASE_URL}/api/settlement",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 1, "Should have at least one settlement"
        print(f"✓ Found {len(data)} settlements")
    
    def test_settlement_get_by_id(self, sultan_token):
        """Test get single settlement by ID"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{SETTLEMENT_ID}",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == SETTLEMENT_ID
        assert data["transaction_number"] == SETTLEMENT_NUMBER
        assert data["status"] == "executed"
        print(f"✓ Settlement {SETTLEMENT_NUMBER} fetched successfully")
    
    def test_settlement_pdf_generates(self, sultan_token):
        """Test settlement PDF generates without errors"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{SETTLEMENT_ID}/pdf",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        
        # Check PDF size is reasonable (should be > 10KB for a proper PDF)
        pdf_content = response.content
        assert len(pdf_content) > 10000, f"PDF too small ({len(pdf_content)} bytes) - might be empty or error"
        print(f"✓ PDF generated successfully ({len(pdf_content)} bytes)")
    
    def test_settlement_pdf_contains_arabic_text(self, sultan_token):
        """Test PDF contains Arabic text (not rendered as squares)"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{SETTLEMENT_ID}/pdf",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        
        # Check PDF binary for Arabic font embedding
        pdf_content = response.content
        
        # Check for font reference in PDF (Amiri or NotoNaskh)
        pdf_str = pdf_content.decode('latin-1', errors='ignore')
        
        # PDF should contain font references
        has_amiri = 'Amiri' in pdf_str
        has_noto = 'NotoNaskh' in pdf_str
        assert has_amiri or has_noto, "PDF should embed Arabic font (Amiri or NotoNaskh)"
        
        print(f"✓ PDF embeds Arabic font: Amiri={has_amiri}, NotoNaskh={has_noto}")
    
    def test_settlement_pdf_content_disposition(self, sultan_token):
        """Test PDF has proper filename in content-disposition"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{SETTLEMENT_ID}/pdf",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        assert response.status_code == 200
        
        content_disp = response.headers.get("content-disposition", "")
        assert "settlement_" in content_disp or "STL-" in content_disp, \
            f"Content-Disposition should contain settlement identifier: {content_disp}"
        print(f"✓ Content-Disposition: {content_disp}")


class TestSettlementPreviewPartialMonthSalary:
    """Settlement preview API with partial_month_salary tests"""
    
    @pytest.fixture(scope="class")
    def sultan_token(self):
        """Get Sultan auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def stas_token(self):
        """Get STAS auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=STAS_CREDS,
            headers={"Content-Type": "application/json"}
        )
        return response.json().get("token")
    
    @pytest.fixture(scope="class")
    def eligible_employee(self, sultan_token):
        """Find an employee with active/terminated contract"""
        # Get employees
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        employees = emp_response.json()
        
        # Get contracts
        contract_response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers={"Authorization": f"Bearer {sultan_token}"}
        )
        contracts = contract_response.json()
        
        # Find employee with active contract
        for emp in employees:
            if emp.get("is_active") == False:
                continue
            for contract in contracts:
                if contract.get("employee_id") == emp.get("id") and contract.get("status") in ["active", "terminated"]:
                    return {
                        "employee_id": emp["id"],
                        "employee_name": emp.get("full_name_ar") or emp.get("full_name"),
                        "contract_status": contract["status"]
                    }
        return None
    
    def test_preview_returns_partial_month_salary(self, sultan_token, eligible_employee):
        """Test preview API returns partial_month_salary field"""
        if not eligible_employee:
            pytest.skip("No eligible employee found for preview test")
        
        preview_data = {
            "employee_id": eligible_employee["employee_id"],
            "termination_type": "resignation",
            "last_working_day": "2026-02-15"  # Mid-month to test partial calculation
        }
        
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            json=preview_data,
            headers={
                "Authorization": f"Bearer {sultan_token}",
                "Content-Type": "application/json"
            }
        )
        
        # If employee has pending settlement, skip this test
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "قيد المعالجة" in detail:
                pytest.skip(f"Employee has pending settlement: {detail}")
        
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()
        
        # Check partial_month_salary exists
        assert "partial_month_salary" in data, "Preview should return partial_month_salary field"
        
        partial = data["partial_month_salary"]
        assert "days" in partial, "partial_month_salary should have 'days' field"
        assert "amount" in partial, "partial_month_salary should have 'amount' field"
        assert "daily_wage" in partial, "partial_month_salary should have 'daily_wage' field"
        
        # For 2026-02-15, days should be 15
        assert partial["days"] == 15, f"Days should be 15 for Feb 15, got {partial['days']}"
        
        # Amount should be days * daily_wage
        expected_amount = partial["days"] * partial["daily_wage"]
        assert abs(partial["amount"] - expected_amount) < 0.01, \
            f"Amount ({partial['amount']}) should equal days ({partial['days']}) * daily_wage ({partial['daily_wage']})"
        
        print(f"✓ Preview returns partial_month_salary: {partial['days']} days = {partial['amount']} SAR")
    
    def test_preview_partial_month_in_totals(self, sultan_token, eligible_employee):
        """Test partial_month_salary is included in entitlements total"""
        if not eligible_employee:
            pytest.skip("No eligible employee found for preview test")
        
        preview_data = {
            "employee_id": eligible_employee["employee_id"],
            "termination_type": "resignation",
            "last_working_day": "2026-02-20"  # 20 days into month
        }
        
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            json=preview_data,
            headers={
                "Authorization": f"Bearer {sultan_token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "قيد المعالجة" in detail:
                pytest.skip(f"Employee has pending settlement: {detail}")
        
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()
        
        # Check totals includes partial_month_salary
        totals = data.get("totals", {})
        entitlements = totals.get("entitlements", {})
        
        assert "partial_month_salary" in entitlements, \
            "entitlements.partial_month_salary should be present in totals"
        
        # Verify calculation
        eos = entitlements.get("eos", 0)
        leave_comp = entitlements.get("leave_compensation", 0)
        bonuses = entitlements.get("bonuses", 0)
        partial = entitlements.get("partial_month_salary", 0)
        total = entitlements.get("total", 0)
        
        expected_total = eos + leave_comp + bonuses + partial
        assert abs(total - expected_total) < 0.01, \
            f"Total entitlements ({total}) should equal sum of components ({expected_total})"
        
        print(f"✓ Entitlements total correctly includes partial_month_salary: {partial} SAR")


class TestSettlementPageLoad:
    """Settlement page accessibility tests"""
    
    def test_settlement_api_accessible(self):
        """Test settlement API is accessible"""
        # First login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        assert login_response.status_code == 200
        token = login_response.json().get("token")
        
        # Then access settlements
        response = requests.get(
            f"{BASE_URL}/api/settlement",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print("✓ Settlement API accessible")
    
    def test_termination_types_api(self):
        """Test termination types endpoint"""
        # First login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        token = login_response.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/settlement/termination-types",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected types exist
        expected_types = ["contract_expiry", "resignation", "probation_termination", "mutual_agreement", "termination"]
        for t in expected_types:
            assert t in data, f"Missing termination type: {t}"
        
        print(f"✓ Termination types: {list(data.keys())}")
    
    def test_employees_api_for_settlement(self):
        """Test employees API needed for settlement creation"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        token = login_response.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        employees = response.json()
        assert len(employees) > 0, "Should have employees"
        print(f"✓ Employees API returns {len(employees)} employees")
    
    def test_contracts_api_for_settlement(self):
        """Test contracts API needed for settlement creation"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        token = login_response.json().get("token")
        
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        contracts = response.json()
        assert len(contracts) > 0, "Should have contracts"
        
        # Check for active contracts
        active_contracts = [c for c in contracts if c.get("status") in ["active", "terminated"]]
        print(f"✓ Contracts API returns {len(contracts)} contracts ({len(active_contracts)} active/terminated)")


class TestSettlementPDFSnapshot:
    """Test settlement snapshot data for PDF generation"""
    
    @pytest.fixture(scope="class")
    def token(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SULTAN_CREDS,
            headers={"Content-Type": "application/json"}
        )
        return response.json().get("token")
    
    def test_settlement_snapshot_has_all_fields(self, token):
        """Test settlement snapshot contains all required PDF fields"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/{SETTLEMENT_ID}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        snapshot = data.get("snapshot", {})
        
        # Check all required sections exist
        required_sections = ["employee", "contract", "service", "wages", "eos", "leave", "totals"]
        for section in required_sections:
            assert section in snapshot, f"Snapshot missing section: {section}"
        
        # Check employee fields
        employee = snapshot["employee"]
        assert employee.get("name_ar"), "Employee should have Arabic name"
        assert employee.get("employee_number"), "Employee should have number"
        
        # Check service fields
        service = snapshot["service"]
        assert "years" in service, "Service should have years"
        assert "months" in service or "remaining_months" in service, "Service should have months"
        
        # Check wages fields
        wages = snapshot["wages"]
        assert "basic" in wages, "Wages should have basic"
        assert "last_wage" in wages, "Wages should have last_wage"
        assert "daily_wage" in wages, "Wages should have daily_wage"
        
        # Check totals
        totals = snapshot["totals"]
        assert "entitlements" in totals, "Totals should have entitlements"
        assert "deductions" in totals, "Totals should have deductions"
        assert "net_amount" in totals, "Totals should have net_amount"
        
        print(f"✓ Snapshot has all required fields for PDF generation")
        print(f"  - Employee: {employee.get('name_ar')}")
        print(f"  - Service: {service.get('formatted_ar')}")
        print(f"  - Net Amount: {totals.get('net_amount')} SAR")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
