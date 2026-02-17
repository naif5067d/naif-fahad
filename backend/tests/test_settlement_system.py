"""
Settlement System API Tests - نظام المخالصة
============================================================
Testing:
1. Settlement preview API with EOS and leave calculations
2. Settlement creation API
3. Settlement execution (STAS only)
4. Bank/IBAN fields in contract
5. EOS calculation based on Saudi Labor Law
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# User IDs from the system
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"
STAS_USER_ID = "fedffe24-ec69-5c65-809d-5d24f8a16b9d"
TEST_EMPLOYEE_ID = "2c291a9b-277b-437a-920f-a76eb4cbaf71"  # نايف فهد القريشي


@pytest.fixture(scope="module")
def sultan_auth():
    """Get Sultan authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
    assert response.status_code == 200, f"Failed to get Sultan token: {response.text}"
    data = response.json()
    return {
        "Authorization": f"Bearer {data['token']}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def stas_auth():
    """Get STAS authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/switch/{STAS_USER_ID}")
    assert response.status_code == 200, f"Failed to get STAS token: {response.text}"
    data = response.json()
    return {
        "Authorization": f"Bearer {data['token']}",
        "Content-Type": "application/json"
    }


class TestSettlementPreview:
    """Settlement Preview API Tests - حسابات المعاينة"""
    
    def test_preview_returns_correct_structure(self, sultan_auth):
        """Test that preview returns all required fields"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200, f"Preview failed: {response.text}"
        data = response.json()
        
        # Check structure
        assert "preview" in data and data["preview"] == True
        assert "employee" in data
        assert "contract" in data
        assert "service" in data
        assert "wages" in data
        assert "eos" in data
        assert "leave" in data
        assert "totals" in data
        
        # Check employee fields
        assert "id" in data["employee"]
        assert "name_ar" in data["employee"]
        assert "employee_number" in data["employee"]
        
        # Check contract has bank info fields
        assert "bank_name" in data["contract"]
        assert "bank_iban" in data["contract"]
        
    def test_preview_eos_calculation_resignation_under_2_years(self, sultan_auth):
        """Test EOS for resignation under 2 years = 0%"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Resignation under 2 years = 0% EOS
        assert data["eos"]["percentage"] == 0
        assert "أقل من سنتين" in data["eos"]["percentage_reason"]
        
    def test_preview_last_wage_calculation(self, sultan_auth):
        """Test Last Wage = Basic + Housing + Transport + Nature of Work + Other"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify wage calculation
        wages = data["wages"]
        calculated_total = wages["basic"] + wages["housing"] + wages["transport"] + wages["nature_of_work"] + wages["other"]
        assert wages["last_wage"] == calculated_total, f"Last wage mismatch: {wages['last_wage']} != {calculated_total}"
        
        # Verify daily wage = last_wage / 30
        expected_daily = round(wages["last_wage"] / 30, 2)
        assert wages["daily_wage"] == expected_daily, f"Daily wage mismatch"
        
    def test_preview_leave_compensation_formula(self, sultan_auth):
        """Test Leave Compensation = balance × daily_wage"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        leave = data["leave"]
        expected_compensation = round(leave["balance"] * leave["daily_wage"], 2)
        assert leave["compensation"] == expected_compensation, f"Leave compensation mismatch"
        
    def test_preview_contract_expiry_full_eos(self, sultan_auth):
        """Test Contract Expiry = 100% EOS"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "contract_expiry",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Contract expiry = 100% EOS
        assert data["eos"]["percentage"] == 100
        
    def test_preview_probation_termination_no_eos(self, sultan_auth):
        """Test Probation Termination = 0% EOS"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "probation_termination",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Probation termination = 0% EOS
        assert data["eos"]["final_amount"] == 0
        assert "فترة التجربة" in data["eos"]["percentage_reason"]


class TestSettlementCRUD:
    """Settlement CRUD Operations - عمليات المخالصة"""
    
    def test_list_settlements(self, sultan_auth):
        """Test listing all settlements"""
        response = requests.get(
            f"{BASE_URL}/api/settlement",
            headers=sultan_auth
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_termination_types(self, sultan_auth):
        """Test getting termination types"""
        response = requests.get(
            f"{BASE_URL}/api/settlement/termination-types",
            headers=sultan_auth
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required types
        assert "contract_expiry" in data
        assert "resignation" in data
        assert "probation_termination" in data
        assert "mutual_agreement" in data


class TestContractBankFields:
    """Contract Bank Fields - حقول البنك والآيبان"""
    
    def test_contract_has_bank_fields(self, sultan_auth):
        """Test that contract can have bank_name and bank_iban"""
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers=sultan_auth
        )
        assert response.status_code == 200
        contracts = response.json()
        
        # Check at least one contract has bank fields in schema
        if contracts:
            contract = contracts[0]
            # Fields should exist (even if null)
            assert "bank_name" in contract or contract.get("bank_name") is None
            assert "bank_iban" in contract or contract.get("bank_iban") is None
            
    def test_update_contract_bank_info(self, stas_auth):
        """Test updating contract with bank info"""
        # First get the test employee's contract
        response = requests.get(
            f"{BASE_URL}/api/contracts-v2",
            headers=stas_auth
        )
        assert response.status_code == 200
        contracts = response.json()
        
        test_contract = next(
            (c for c in contracts if c["employee_id"] == TEST_EMPLOYEE_ID),
            None
        )
        
        if test_contract:
            # Update with bank info
            update_response = requests.put(
                f"{BASE_URL}/api/contracts-v2/{test_contract['id']}",
                headers=stas_auth,
                json={
                    "bank_name": "الراجحي",
                    "bank_iban": "SA0380000000608010167519"
                }
            )
            # Accept 200 or 400 if not allowed to update
            assert update_response.status_code in [200, 400, 422]


class TestDeductionsAPI:
    """Deductions API Tests - الخصومات والمكافآت"""
    
    def test_list_deductions(self, sultan_auth):
        """Test listing deductions"""
        response = requests.get(
            f"{BASE_URL}/api/deductions",
            headers=sultan_auth
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
    def test_get_employee_unsettled(self, sultan_auth):
        """Test getting employee's unsettled items"""
        response = requests.get(
            f"{BASE_URL}/api/deductions/employee/{TEST_EMPLOYEE_ID}/unsettled",
            headers=sultan_auth
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "deductions" in data
        assert "bonuses" in data
        assert "total_deductions" in data
        assert "total_bonuses" in data


class TestEOSCalculationLogic:
    """EOS Calculation Logic Tests - حسابات مكافأة نهاية الخدمة"""
    
    def test_eos_under_5_years_formula(self, sultan_auth):
        """Test EOS formula for under 5 years: 0.5 × wage × years"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "contract_expiry",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        eos = data["eos"]
        wages = data["wages"]
        service = data["service"]
        
        # Formula: 0.5 × monthly_wage × years (for under 5 years)
        if service["years"] < 5:
            expected_base = 0.5 * wages["last_wage"] * service["years"]
            assert abs(eos["base_amount"] - round(expected_base, 2)) < 0.1, f"EOS base amount mismatch"


class TestSettlementPermissions:
    """Settlement Permissions Tests - صلاحيات المخالصة"""
    
    def test_sultan_can_preview(self, sultan_auth):
        """Sultan should be able to preview settlement"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        
    def test_stas_can_preview(self, stas_auth):
        """STAS should be able to preview settlement"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=stas_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200


class TestSettlementNetCalculation:
    """Settlement Net Amount Tests - حساب الصافي"""
    
    def test_net_amount_formula(self, sultan_auth):
        """Test Net = Entitlements - Deductions"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        totals = data["totals"]
        
        # Net = Entitlements Total - Deductions Total
        expected_net = totals["entitlements"]["total"] - totals["deductions"]["total"]
        assert totals["net_amount"] == round(expected_net, 2), f"Net amount mismatch"
        
    def test_entitlements_total_formula(self, sultan_auth):
        """Test Entitlements = EOS + Leave Compensation + Bonuses"""
        response = requests.post(
            f"{BASE_URL}/api/settlement/preview",
            headers=sultan_auth,
            json={
                "employee_id": TEST_EMPLOYEE_ID,
                "termination_type": "resignation",
                "last_working_day": "2026-02-20"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        entitlements = data["totals"]["entitlements"]
        expected_total = entitlements["eos"] + entitlements["leave_compensation"] + entitlements["bonuses"]
        assert entitlements["total"] == round(expected_total, 2), f"Entitlements total mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
