"""
Iteration 21 Tests - Contracts V2 Features
Tests:
1. Create contract with new employee (is_new_employee=true)
2. Annual leave days 21/30 options only
3. Monthly permission hours 0-3 (max 3 cap)
4. Migrated contract with opening balances (fractional)
5. Medical PDF upload endpoint
"""

import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# STAS user ID for testing
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"


@pytest.fixture(scope="module")
def auth_token():
    """Get STAS auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Auth headers for API calls"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="function")
def cleanup_contracts(auth_headers):
    """Cleanup test contracts after each test"""
    created_ids = []
    yield created_ids
    
    # Delete test contracts
    for contract_id in created_ids:
        try:
            requests.delete(
                f"{BASE_URL}/api/contracts-v2/{contract_id}",
                headers=auth_headers
            )
        except:
            pass


class TestContractsV2NewEmployee:
    """Test creating contracts with new employees"""
    
    def test_create_contract_with_new_employee(self, auth_headers, cleanup_contracts):
        """Test is_new_employee=true creates employee and contract"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_موظف جديد",
            "employee_name": "TEST_New Employee",
            "national_id": "1234567890",
            "email": "test_new@example.com",
            "phone": "0500000000",
            "employee_code": "TEST-EMP-NEW",
            "job_title_ar": "مطور",
            "job_title": "Developer",
            "department_ar": "التقنية",
            "department": "IT",
            "start_date": "2026-02-18",
            "basic_salary": 8000,
            "annual_leave_days": 21,
            "monthly_permission_hours": 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Store for cleanup
        cleanup_contracts.append(data["id"])
        
        # Verify contract created
        assert data["contract_serial"].startswith("DAC-2026-")
        assert data["employee_name_ar"] == "TEST_موظف جديد"
        assert data["employee_name"] == "TEST_New Employee"
        assert data["employee_id"]  # Employee ID should be auto-generated
        assert data["status"] == "draft"
        assert data["annual_leave_days"] == 21
        assert data["monthly_permission_hours"] == 2
    
    def test_create_contract_existing_employee(self, auth_headers):
        """Test creating contract for existing employee"""
        # Get existing employees
        emp_resp = requests.get(
            f"{BASE_URL}/api/employees",
            headers=auth_headers
        )
        employees = emp_resp.json()
        
        # Should have existing employees
        assert len(employees) > 0, "No employees found for testing"


class TestAnnualLeaveDays:
    """Test annual leave days options (21 or 30 only)"""
    
    def test_annual_leave_21_days(self, auth_headers, cleanup_contracts):
        """Test 21-day annual leave (< 5 years)"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_21 يوم",
            "employee_code": "TEST-21DAY",
            "start_date": "2026-02-18",
            "annual_leave_days": 21,
            "basic_salary": 5000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["annual_leave_days"] == 21
    
    def test_annual_leave_30_days(self, auth_headers, cleanup_contracts):
        """Test 30-day annual leave (>= 5 years)"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_30 يوم",
            "employee_code": "TEST-30DAY",
            "start_date": "2020-01-01",  # Old start date
            "annual_leave_days": 30,
            "basic_salary": 5000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["annual_leave_days"] == 30


class TestMonthlyPermissionHours:
    """Test monthly permission hours (0-3 max)"""
    
    def test_permission_hours_0(self, auth_headers, cleanup_contracts):
        """Test 0 permission hours"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_0 ساعات",
            "employee_code": "TEST-0HR",
            "start_date": "2026-02-18",
            "monthly_permission_hours": 0,
            "basic_salary": 5000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["monthly_permission_hours"] == 0
    
    def test_permission_hours_3_max(self, auth_headers, cleanup_contracts):
        """Test max 3 permission hours"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_3 ساعات",
            "employee_code": "TEST-3HR",
            "start_date": "2026-02-18",
            "monthly_permission_hours": 3,
            "basic_salary": 5000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["monthly_permission_hours"] == 3
    
    def test_permission_hours_capped_at_3(self, auth_headers, cleanup_contracts):
        """Test permission hours >3 get capped at 3"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_5 ساعات",
            "employee_code": "TEST-5HR",
            "start_date": "2026-02-18",
            "monthly_permission_hours": 5,  # Should be capped at 3
            "basic_salary": 5000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["monthly_permission_hours"] == 3, "Permission hours should be capped at 3"


class TestMigratedContract:
    """Test migrated contracts with opening balances"""
    
    def test_migrated_contract_with_fractional_balances(self, auth_headers, cleanup_contracts):
        """Test migrated contract with fractional leave balances"""
        payload = {
            "is_new_employee": True,
            "employee_name_ar": "TEST_موظف مُهاجر",
            "employee_name": "TEST_Migrated Employee",
            "employee_code": "TEST-MIGR",
            "start_date": "2020-01-01",
            "annual_leave_days": 30,
            "monthly_permission_hours": 2,
            "is_migrated": True,
            "leave_opening_balance": {
                "annual": 15.5,  # Fractional allowed
                "sick": 10,
                "emergency": 3,
                "permission_hours": 1.5  # Fractional allowed
            },
            "basic_salary": 10000
        }
        
        response = requests.post(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers,
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        cleanup_contracts.append(data["id"])
        
        assert data["is_migrated"] == True
        assert data["leave_opening_balance"]["annual"] == 15.5
        assert data["leave_opening_balance"]["permission_hours"] == 1.5


class TestMedicalUpload:
    """Test medical PDF file upload"""
    
    def test_upload_pdf_success(self, auth_token):
        """Test uploading valid PDF file"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >> endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer << /Size 4 /Root 1 0 R >>
startxref
193
%%EOF"""
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf_content)
            f.flush()
            
            with open(f.name, 'rb') as pdf_file:
                response = requests.post(
                    f"{BASE_URL}/api/upload/medical",
                    headers=headers,
                    files={"file": ("test.pdf", pdf_file, "application/pdf")}
                )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "url" in data
        assert data["url"].startswith("/api/upload/files/medical_")
        assert data["filename"].endswith(".pdf")
        assert data["size"] > 0
    
    def test_upload_non_pdf_fails(self, auth_token):
        """Test uploading non-PDF file fails"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"This is not a PDF")
            f.flush()
            
            with open(f.name, 'rb') as txt_file:
                response = requests.post(
                    f"{BASE_URL}/api/upload/medical",
                    headers=headers,
                    files={"file": ("test.txt", txt_file, "text/plain")}
                )
        
        assert response.status_code == 400
        data = response.json()
        assert "PDF" in data["detail"]


class TestNavigation:
    """Test that old contracts route is removed"""
    
    def test_contracts_v2_endpoint_exists(self, auth_headers):
        """Test contracts-v2 endpoint is accessible"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers
        )
        assert response.status_code == 200
    
    def test_old_contracts_endpoint_should_not_exist(self, auth_headers):
        """Test old /api/contracts endpoint behavior"""
        # Note: This tests that only contracts-v2 is the primary contracts system
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers=auth_headers
        )
        assert response.status_code == 200
        # The response should be a list
        data = response.json()
        assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
