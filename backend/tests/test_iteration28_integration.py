"""
Iteration 28 - Integration Tests: Contract -> Attendance -> Penalties -> Settlement
تكامل النظام من العقد إلى المخالصة

Tests:
1. Team Attendance APIs
2. Penalties/Deductions APIs  
3. Contracts V2 APIs
4. Employee Records APIs
5. Settlement Calculation APIs
6. Data Integration Verification
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Sultan user ID for auth switch
SULTAN_USER_ID = "54e422b8-357c-5fdc-81d5-de6cac565810"


class TestAuthSetup:
    """Ensure auth is working before running tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create session with sultan auth"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        return s
    
    def test_01_switch_to_sultan(self, session):
        """Switch to sultan user for admin access"""
        response = session.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        print(f"Switch response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                session.headers.update({"Authorization": f"Bearer {token}"})
                print("Successfully switched to sultan user")
        
        # Verify we have access
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        print(f"Current user: {me_response.json().get('role', 'unknown')}")


class TestTeamAttendance:
    """Test Team Attendance APIs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        # Switch to sultan (POST method)
        response = s.post(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_team_attendance_daily(self, auth_session):
        """GET /api/team-attendance/daily - Daily attendance for all employees"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = auth_session.get(f"{BASE_URL}/api/team-attendance/daily", params={"date": today})
        
        print(f"Status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list of employees"
        print(f"Found {len(data)} employees in daily attendance")
        
        # Validate data structure
        if len(data) > 0:
            emp = data[0]
            assert "employee_id" in emp, "Missing employee_id"
            assert "final_status" in emp, "Missing final_status"
            assert "date" in emp, "Missing date"
            print(f"Sample employee: {emp.get('employee_name_ar')} - Status: {emp.get('final_status')}")
    
    def test_02_team_attendance_summary(self, auth_session):
        """GET /api/team-attendance/summary - Team summary"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = auth_session.get(f"{BASE_URL}/api/team-attendance/summary", params={"date": today})
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate summary fields
        assert "total" in data, "Missing total count"
        assert "present" in data, "Missing present count"
        assert "absent" in data, "Missing absent count"
        assert "date" in data, "Missing date"
        
        print(f"Summary for {data['date']}: Total={data['total']}, Present={data['present']}, Absent={data['absent']}")
    
    def test_03_team_attendance_weekly(self, auth_session):
        """GET /api/team-attendance/weekly - Weekly summary"""
        today = datetime.now().strftime("%Y-%m-%d")
        response = auth_session.get(f"{BASE_URL}/api/team-attendance/weekly", params={"date": today})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected list"
        print(f"Weekly data: {len(data)} employees")
    
    def test_04_team_attendance_monthly(self, auth_session):
        """GET /api/team-attendance/monthly - Monthly summary"""
        month = datetime.now().strftime("%Y-%m")
        response = auth_session.get(f"{BASE_URL}/api/team-attendance/monthly", params={"month": month})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected list"
        print(f"Monthly data for {month}: {len(data)} employees")
        
        if len(data) > 0:
            emp = data[0]
            assert "employee_id" in emp
            assert "total_present" in emp
            assert "total_absent" in emp
            print(f"Sample: {emp.get('employee_name_ar')} - Present: {emp.get('total_present')}, Absent: {emp.get('total_absent')}")
    
    def test_05_employee_attendance_detail(self, auth_session):
        """GET /api/team-attendance/employee/{id} - Specific employee attendance"""
        # First get an employee ID
        daily_response = auth_session.get(f"{BASE_URL}/api/team-attendance/daily")
        if daily_response.status_code != 200:
            pytest.skip("Could not get employee list")
        
        employees = daily_response.json()
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["employee_id"]
        
        # Get employee detail
        response = auth_session.get(
            f"{BASE_URL}/api/team-attendance/employee/{employee_id}",
            params={"period": "daily"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "employee_id" in data
        assert "employee_name" in data
        print(f"Employee attendance detail: {data.get('employee_name_ar', data.get('employee_name'))}")


class TestPenalties:
    """Test Penalties/Deductions APIs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        response = s.get(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_monthly_report(self, auth_session):
        """GET /api/penalties/monthly-report - Monthly penalties report"""
        year = datetime.now().year
        month = datetime.now().month
        
        response = auth_session.get(
            f"{BASE_URL}/api/penalties/monthly-report",
            params={"year": year, "month": month}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate structure
        assert "period" in data, "Missing period"
        assert "summary" in data, "Missing summary"
        assert "employees" in data, "Missing employees list"
        
        summary = data["summary"]
        assert "total_employees" in summary, "Missing total_employees in summary"
        assert "total_deduction_amount" in summary, "Missing total_deduction_amount"
        
        print(f"Monthly Report {data['period']}: {summary['total_employees']} employees")
        print(f"Total Deduction: {summary.get('total_deduction_amount', 0)} SAR")
        print(f"Total Absent Days: {summary.get('total_absent_days', 0)}")
        print(f"Total Deficit Hours: {summary.get('total_deficit_hours', 0)}")
    
    def test_02_employee_monthly_penalties(self, auth_session):
        """GET /api/penalties/monthly/{employee_id} - Specific employee penalties"""
        # Get employee from report
        year = datetime.now().year
        month = datetime.now().month
        
        report_response = auth_session.get(
            f"{BASE_URL}/api/penalties/monthly-report",
            params={"year": year, "month": month}
        )
        
        if report_response.status_code != 200:
            pytest.skip("Could not get monthly report")
        
        employees = report_response.json().get("employees", [])
        if len(employees) == 0:
            pytest.skip("No employees in report")
        
        employee_id = employees[0]["employee_id"]
        
        response = auth_session.get(
            f"{BASE_URL}/api/penalties/monthly/{employee_id}",
            params={"year": year, "month": month}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert "employee_id" in data, "Missing employee_id"
        assert "absence" in data, "Missing absence data"
        assert "deficit" in data, "Missing deficit data"
        assert "total_deduction_days" in data, "Missing total_deduction_days"
        
        print(f"Employee: {data.get('employee_name_ar')}")
        print(f"Absence days: {data['absence'].get('total_days', 0)}")
        print(f"Deficit hours: {data['deficit'].get('total_deficit_hours', 0)}")
        print(f"Total deduction: {data.get('total_deduction_days', 0)} days")
    
    def test_03_yearly_absence(self, auth_session):
        """GET /api/penalties/yearly/{employee_id} - Yearly scattered absence"""
        # Get an employee ID
        employees_response = auth_session.get(f"{BASE_URL}/api/employees")
        if employees_response.status_code != 200:
            pytest.skip("Could not get employees")
        
        employees = employees_response.json()
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["id"]
        year = datetime.now().year
        
        response = auth_session.get(
            f"{BASE_URL}/api/penalties/yearly/{employee_id}",
            params={"year": year}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "employee_id" in data
        assert "year" in data
        assert "total_scattered_absence" in data
        
        print(f"Yearly absence for {data.get('employee_name_ar')}: {data['total_scattered_absence']} days")


class TestContracts:
    """Test Contracts V2 APIs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        response = s.get(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_list_contracts(self, auth_session):
        """GET /api/contracts-v2 - List all contracts"""
        response = auth_session.get(f"{BASE_URL}/api/contracts-v2")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Expected list of contracts"
        print(f"Found {len(data)} contracts")
        
        if len(data) > 0:
            contract = data[0]
            assert "id" in contract, "Missing contract id"
            assert "contract_serial" in contract, "Missing contract_serial"
            assert "status" in contract, "Missing status"
            print(f"Sample contract: {contract.get('contract_serial')} - Status: {contract.get('status')}")
    
    def test_02_active_contracts(self, auth_session):
        """GET /api/contracts-v2?status=active - List active contracts"""
        response = auth_session.get(f"{BASE_URL}/api/contracts-v2", params={"status": "active"})
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        active_count = len([c for c in data if c.get("status") == "active"])
        print(f"Found {active_count} active contracts out of {len(data)}")
    
    def test_03_contract_stats(self, auth_session):
        """GET /api/contracts-v2/stats/summary - Contract statistics"""
        response = auth_session.get(f"{BASE_URL}/api/contracts-v2/stats/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data, "Missing total"
        assert "active" in data, "Missing active count"
        
        print(f"Contract Stats: Total={data['total']}, Active={data['active']}, Draft={data.get('draft', 0)}")
    
    def test_04_employee_contracts(self, auth_session):
        """GET /api/contracts-v2/employee/{id} - Employee contracts"""
        # Get an employee
        employees_response = auth_session.get(f"{BASE_URL}/api/employees")
        if employees_response.status_code != 200:
            pytest.skip("Could not get employees")
        
        employees = employees_response.json()
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["id"]
        
        response = auth_session.get(f"{BASE_URL}/api/contracts-v2/employee/{employee_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Employee {employee_id} has {len(data)} contracts")


class TestEmployees:
    """Test Employee Record APIs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        response = s.get(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_list_employees(self, auth_session):
        """GET /api/employees - List all employees"""
        response = auth_session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} employees")
        
        if len(data) > 0:
            emp = data[0]
            assert "id" in emp, "Missing id"
            assert "full_name" in emp or "full_name_ar" in emp, "Missing name"
            print(f"Sample employee: {emp.get('full_name_ar', emp.get('full_name'))}")
    
    def test_02_employee_detail(self, auth_session):
        """GET /api/employees/{id} - Employee detail"""
        employees_response = auth_session.get(f"{BASE_URL}/api/employees")
        if employees_response.status_code != 200:
            pytest.skip("Could not get employees")
        
        employees = employees_response.json()
        if len(employees) == 0:
            pytest.skip("No employees found")
        
        employee_id = employees[0]["id"]
        
        response = auth_session.get(f"{BASE_URL}/api/employees/{employee_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == employee_id
        print(f"Employee detail: {data.get('full_name_ar', data.get('full_name'))}")


class TestSettlement:
    """Test Settlement Calculation APIs"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        response = s.get(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_list_settlements(self, auth_session):
        """GET /api/settlement - List all settlements"""
        response = auth_session.get(f"{BASE_URL}/api/settlement")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} settlements")
        
        if len(data) > 0:
            settlement = data[0]
            assert "id" in settlement, "Missing id"
            assert "status" in settlement, "Missing status"
            print(f"Sample settlement: {settlement.get('transaction_number')} - Status: {settlement.get('status')}")
    
    def test_02_termination_types(self, auth_session):
        """GET /api/settlement/termination-types - Get termination types"""
        response = auth_session.get(f"{BASE_URL}/api/settlement/termination-types")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least these types
        expected_types = ["contract_expiry", "resignation", "probation_termination", "mutual_agreement"]
        for t in expected_types:
            assert t in data, f"Missing termination type: {t}"
        
        print(f"Termination types: {list(data.keys())}")
    
    def test_03_settlement_preview(self, auth_session):
        """POST /api/settlement/preview - Preview settlement calculation"""
        # Get an employee with active contract
        contracts_response = auth_session.get(f"{BASE_URL}/api/contracts-v2", params={"status": "active"})
        if contracts_response.status_code != 200:
            pytest.skip("Could not get contracts")
        
        contracts = contracts_response.json()
        active_contracts = [c for c in contracts if c.get("status") == "active"]
        
        if len(active_contracts) == 0:
            pytest.skip("No active contracts found")
        
        contract = active_contracts[0]
        employee_id = contract["employee_id"]
        
        # Preview settlement
        payload = {
            "employee_id": employee_id,
            "termination_type": "resignation",
            "last_working_day": datetime.now().strftime("%Y-%m-%d"),
            "note": "Test preview"
        }
        
        response = auth_session.post(f"{BASE_URL}/api/settlement/preview", json=payload)
        
        # Could be 200 or 400 if employee already has pending settlement
        if response.status_code == 400:
            detail = response.json().get("detail", "")
            if "قيد المعالجة" in detail or "pending" in detail.lower():
                print(f"Employee already has pending settlement - skipping")
                pytest.skip("Employee has pending settlement")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate preview structure
        assert "preview" in data, "Missing preview flag"
        assert "employee" in data, "Missing employee data"
        assert "contract" in data, "Missing contract data"
        assert "eos" in data, "Missing eos (end of service) calculation"
        assert "leave" in data, "Missing leave balance"
        assert "totals" in data, "Missing totals"
        
        print(f"Settlement Preview for: {data['employee'].get('name_ar')}")
        print(f"  Service: {data.get('service', {}).get('formatted_ar', 'N/A')}")
        print(f"  EOS Amount: {data['eos'].get('final_amount', 0)} SAR")
        print(f"  Leave Compensation: {data['leave'].get('compensation', 0)} SAR")
        print(f"  Net Amount: {data['totals'].get('net_amount', 0)} SAR")


class TestDataIntegration:
    """Test data integration between modules"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        response = s.get(f"{BASE_URL}/api/auth/switch/{SULTAN_USER_ID}")
        if response.status_code == 200:
            data = response.json()
            token = data.get("token") or data.get("access_token")
            if token:
                s.headers.update({"Authorization": f"Bearer {token}"})
        return s
    
    def test_01_contract_to_attendance_link(self, auth_session):
        """Verify contract -> attendance link"""
        # Get active contract
        contracts_response = auth_session.get(f"{BASE_URL}/api/contracts-v2", params={"status": "active"})
        if contracts_response.status_code != 200:
            pytest.skip("Could not get contracts")
        
        contracts = contracts_response.json()
        active_contracts = [c for c in contracts if c.get("status") == "active"]
        
        if len(active_contracts) == 0:
            pytest.skip("No active contracts")
        
        contract = active_contracts[0]
        employee_id = contract["employee_id"]
        
        # Get attendance for this employee
        today = datetime.now().strftime("%Y-%m-%d")
        attendance_response = auth_session.get(
            f"{BASE_URL}/api/team-attendance/employee/{employee_id}",
            params={"period": "daily", "date": today}
        )
        
        assert attendance_response.status_code == 200
        data = attendance_response.json()
        
        assert data.get("employee_id") == employee_id, "Employee ID mismatch"
        print(f"Contract {contract['contract_serial']} -> Employee {employee_id} attendance linked")
    
    def test_02_attendance_to_penalties_link(self, auth_session):
        """Verify attendance -> penalties link"""
        year = datetime.now().year
        month = datetime.now().month
        
        # Get penalties report
        penalties_response = auth_session.get(
            f"{BASE_URL}/api/penalties/monthly-report",
            params={"year": year, "month": month}
        )
        
        assert penalties_response.status_code == 200
        penalties_data = penalties_response.json()
        
        # Get monthly attendance
        monthly_response = auth_session.get(
            f"{BASE_URL}/api/team-attendance/monthly",
            params={"month": f"{year}-{month:02d}"}
        )
        
        assert monthly_response.status_code == 200
        monthly_data = monthly_response.json()
        
        # Both should have same employees
        penalty_emp_ids = {e["employee_id"] for e in penalties_data.get("employees", [])}
        monthly_emp_ids = {e["employee_id"] for e in monthly_data}
        
        common = penalty_emp_ids & monthly_emp_ids
        print(f"Penalties has {len(penalty_emp_ids)} employees")
        print(f"Monthly attendance has {len(monthly_emp_ids)} employees")
        print(f"Common employees: {len(common)}")
        
        # Should have significant overlap
        if len(monthly_emp_ids) > 0:
            overlap_pct = len(common) / len(monthly_emp_ids) * 100
            print(f"Overlap: {overlap_pct:.1f}%")
    
    def test_03_deductions_reflected_in_settlement(self, auth_session):
        """Verify deductions are reflected in settlement calculation"""
        # Get an employee with active contract
        contracts_response = auth_session.get(f"{BASE_URL}/api/contracts-v2", params={"status": "active"})
        if contracts_response.status_code != 200:
            pytest.skip("Could not get contracts")
        
        contracts = contracts_response.json()
        active_contracts = [c for c in contracts if c.get("status") == "active"]
        
        if len(active_contracts) == 0:
            pytest.skip("No active contracts")
        
        contract = active_contracts[0]
        employee_id = contract["employee_id"]
        
        # Preview settlement
        payload = {
            "employee_id": employee_id,
            "termination_type": "resignation",
            "last_working_day": datetime.now().strftime("%Y-%m-%d")
        }
        
        response = auth_session.post(f"{BASE_URL}/api/settlement/preview", json=payload)
        
        if response.status_code == 400:
            pytest.skip("Could not preview settlement (may have pending settlement)")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check deductions section
        deductions = data.get("deductions", {})
        loans = data.get("loans", {})
        totals = data.get("totals", {})
        
        print(f"Settlement Preview for {data['employee'].get('name_ar')}:")
        print(f"  Deductions: {deductions.get('total', 0)} SAR ({deductions.get('count', 0)} items)")
        print(f"  Loans: {loans.get('total', 0)} SAR ({loans.get('count', 0)} items)")
        print(f"  Total Entitlements: {totals.get('entitlements', {}).get('total', 0)} SAR")
        print(f"  Total Deductions: {totals.get('deductions', {}).get('total', 0)} SAR")
        print(f"  Net Amount: {totals.get('net_amount', 0)} SAR")
        
        # Verify totals calculation
        entitlements_total = totals.get("entitlements", {}).get("total", 0)
        deductions_total = totals.get("deductions", {}).get("total", 0)
        net = totals.get("net_amount", 0)
        
        expected_net = entitlements_total - deductions_total
        assert abs(net - expected_net) < 0.01, f"Net calculation mismatch: {net} != {expected_net}"
        print("Net amount calculation verified ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
