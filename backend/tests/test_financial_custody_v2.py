"""
Test Financial Custody (60 Code) System - Rebuilt Version
Tests the complete custody lifecycle: create → receive → add expenses → audit → approve → execute
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthSetup:
    """Test authentication and get user tokens"""
    
    @pytest.fixture(scope="class")
    def users(self):
        """Get all users"""
        response = requests.get(f"{BASE_URL}/api/auth/users")
        assert response.status_code == 200
        users = response.json()
        return {u['role']: u for u in users}
    
    @pytest.fixture(scope="class")
    def sultan_session(self, users):
        """Get Sultan session"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/switch/{users['sultan']['id']}")
        assert resp.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def naif_session(self, users):
        """Get Naif session"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/switch/{users['naif']['id']}")
        assert resp.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def salah_session(self, users):
        """Get Salah session"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/switch/{users['salah']['id']}")
        assert resp.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def mohammed_session(self, users):
        """Get Mohammed session"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/switch/{users['mohammed']['id']}")
        assert resp.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def stas_session(self, users):
        """Get STAS session"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/switch/{users['stas']['id']}")
        assert resp.status_code == 200
        return session
    
    @pytest.fixture(scope="class")
    def employee_session(self, users):
        """Get Employee session"""
        session = requests.Session()
        emp = next((u for u in users.values() if u['role'] == 'employee'), None)
        if not emp:
            pytest.skip("No employee user found")
        resp = session.post(f"{BASE_URL}/api/auth/switch/{emp['id']}")
        assert resp.status_code == 200
        return session


class TestFinancialCustodyCreation(TestAuthSetup):
    """Test custody creation permissions"""
    
    def test_sultan_can_create_custody(self, sultan_session):
        """Sultan can create financial custody"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Monthly Expenses",
            "title_ar": "المصروفات الشهرية - اختبار",
            "total_amount": 5000
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        assert data["total_amount"] == 5000
        assert data["remaining"] == 5000
        assert "custody_number" in data
        print(f"✓ Sultan created custody #{data['custody_number']} with 5000 SAR")
        return data["id"]
    
    def test_naif_can_create_custody(self, naif_session):
        """Naif can create financial custody"""
        response = naif_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Office Supplies",
            "title_ar": "مستلزمات المكتب - اختبار",
            "total_amount": 2000
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"
        print(f"✓ Naif created custody #{data['custody_number']}")
    
    def test_mohammed_can_create_custody(self, mohammed_session):
        """Mohammed (CEO) can create financial custody"""
        response = mohammed_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_CEO Special Project",
            "title_ar": "مشروع خاص - اختبار",
            "total_amount": 10000
        })
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Mohammed created custody #{data['custody_number']}")
    
    def test_salah_cannot_create_custody(self, salah_session):
        """Salah (Finance) cannot create financial custody"""
        response = salah_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Salah Attempt",
            "total_amount": 1000
        })
        assert response.status_code == 403
        print("✓ Salah correctly denied from creating custody")
    
    def test_employee_cannot_create_custody(self, employee_session):
        """Employee cannot create financial custody"""
        response = employee_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Employee Attempt",
            "total_amount": 500
        })
        assert response.status_code == 403
        print("✓ Employee correctly denied from creating custody")


class TestFinancialCustodyReceive(TestAuthSetup):
    """Test custody receive functionality"""
    
    @pytest.fixture(scope="class")
    def test_custody(self, sultan_session):
        """Create a test custody for receive tests"""
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Receive Test Custody",
            "total_amount": 3000
        })
        return resp.json()
    
    def test_receive_sets_status_to_active(self, sultan_session, test_custody):
        """Receiving custody sets status to active"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{test_custody['id']}/receive")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        print(f"✓ Custody received - status is now 'active'")
    
    def test_cannot_receive_already_received(self, sultan_session, test_custody):
        """Cannot receive an already received custody"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{test_custody['id']}/receive")
        assert response.status_code == 400
        print("✓ Already received custody correctly rejected")


class TestFinancialCustodyExpenses(TestAuthSetup):
    """Test expense management"""
    
    @pytest.fixture(scope="class")
    def active_custody(self, sultan_session):
        """Create and receive a custody for expense tests"""
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Expense Test Custody",
            "total_amount": 10000
        })
        custody = resp.json()
        # Receive it
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        return custody
    
    def test_sultan_can_add_expense(self, sultan_session, active_custody):
        """Sultan can add expense - remaining decreases correctly"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{active_custody['id']}/expense", json={
            "code": 1,
            "description": "Office supplies purchase",
            "amount": 500
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total_spent"] == 500
        assert data["remaining"] == 9500  # 10000 - 500
        print(f"✓ Expense added - spent: {data['total_spent']}, remaining: {data['remaining']}")
    
    def test_add_multiple_expenses_accumulate(self, sultan_session, active_custody):
        """Multiple expenses accumulate correctly"""
        # Add another expense
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{active_custody['id']}/expense", json={
            "code": 2,
            "description": "Transportation costs",
            "amount": 300
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total_spent"] == 800  # 500 + 300
        assert data["remaining"] == 9200  # 10000 - 800
        print(f"✓ Multiple expenses accumulated - spent: {data['total_spent']}, remaining: {data['remaining']}")
    
    def test_expense_cannot_exceed_remaining(self, sultan_session, active_custody):
        """Cannot add expense exceeding remaining balance"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{active_custody['id']}/expense", json={
            "code": 3,
            "description": "Excessive expense",
            "amount": 99999
        })
        assert response.status_code == 400
        assert "exceeds" in response.json()["detail"].lower()
        print("✓ Excessive expense correctly rejected")
    
    def test_salah_cannot_add_expense(self, salah_session, active_custody):
        """Salah cannot add expenses"""
        response = salah_session.post(f"{BASE_URL}/api/financial-custody/{active_custody['id']}/expense", json={
            "code": 1,
            "description": "Salah attempt",
            "amount": 100
        })
        assert response.status_code == 403
        print("✓ Salah correctly denied from adding expense")


class TestFinancialCustodyAudit(TestAuthSetup):
    """Test audit workflow"""
    
    @pytest.fixture(scope="class")
    def custody_for_audit(self, sultan_session):
        """Create custody with expenses ready for audit"""
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Audit Test Custody",
            "total_amount": 5000
        })
        custody = resp.json()
        # Receive
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        # Add expense
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Test expense", "amount": 1000
        })
        return custody
    
    def test_submit_for_audit(self, sultan_session, custody_for_audit):
        """Sultan sends custody for audit"""
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody_for_audit['id']}/submit-audit")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_audit"
        print(f"✓ Submitted for audit - status: {data['status']}")
    
    def test_cannot_submit_empty_custody(self, sultan_session):
        """Cannot submit custody with no expenses"""
        # Create new custody with no expenses
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Empty Custody",
            "total_amount": 1000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        assert response.status_code == 400
        print("✓ Empty custody correctly rejected from audit submission")
    
    def test_salah_can_approve_audit(self, salah_session, custody_for_audit):
        """Salah (Finance) can approve audit"""
        response = salah_session.post(f"{BASE_URL}/api/financial-custody/{custody_for_audit['id']}/audit", json={
            "action": "approve",
            "note": "Audited and approved"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"
        print(f"✓ Salah approved audit - status: {data['status']}")
    
    def test_salah_can_reject_audit(self, salah_session, sultan_session):
        """Salah can reject audit - returns to active"""
        # Create another custody for rejection test
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Audit Rejection Test",
            "total_amount": 2000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Test", "amount": 500
        })
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        
        # Salah rejects
        response = salah_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit", json={
            "action": "reject",
            "note": "Needs corrections"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        print("✓ Salah rejected audit - custody returned to active status")


class TestFinancialCustodyApproval(TestAuthSetup):
    """Test CEO approval workflow"""
    
    @pytest.fixture(scope="class")
    def custody_for_approval(self, sultan_session, salah_session):
        """Create custody ready for CEO approval"""
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Approval Test Custody",
            "total_amount": 8000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Test expense", "amount": 2000
        })
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        salah_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit", json={"action": "approve"})
        return custody
    
    def test_mohammed_can_approve(self, mohammed_session, custody_for_approval):
        """Mohammed (CEO) can approve custody"""
        response = mohammed_session.post(f"{BASE_URL}/api/financial-custody/{custody_for_approval['id']}/approve", json={
            "action": "approve",
            "note": "Approved by CEO"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_stas"
        print(f"✓ Mohammed approved custody - status: {data['status']}")
    
    def test_sultan_cannot_approve(self, sultan_session, salah_session):
        """Sultan cannot perform CEO approval"""
        # Create custody ready for approval
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Sultan Approval Test",
            "total_amount": 1000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Test", "amount": 500
        })
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        salah_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit", json={"action": "approve"})
        
        # Sultan tries to approve
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/approve", json={
            "action": "approve"
        })
        assert response.status_code == 403
        print("✓ Sultan correctly denied from CEO approval")


class TestFinancialCustodyExecution(TestAuthSetup):
    """Test STAS execution and carry-forward"""
    
    @pytest.fixture(scope="class")
    def custody_for_execution(self, sultan_session, salah_session, mohammed_session):
        """Create custody ready for execution"""
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Execution Test Custody",
            "total_amount": 5000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Partial expense", "amount": 3000
        })
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        salah_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit", json={"action": "approve"})
        mohammed_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/approve", json={"action": "approve"})
        return custody
    
    def test_stas_can_execute_and_carry_remaining(self, stas_session, custody_for_execution):
        """STAS executes - remaining amount carries to next custody"""
        response = stas_session.post(f"{BASE_URL}/api/financial-custody/{custody_for_execution['id']}/execute")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "executed"
        # Should have carried_to since remaining (2000) > 0
        assert data["carried_to"] is not None
        print(f"✓ STAS executed custody - remaining 2000 SAR carried to new custody")
        
        # Verify the new custody was created with carried amount
        new_custody_resp = stas_session.get(f"{BASE_URL}/api/financial-custody/{data['carried_to']}")
        new_custody = new_custody_resp.json()
        assert new_custody["carried_amount"] == 2000
        assert new_custody["remaining"] == 2000
        print(f"✓ New custody created with carried amount: {new_custody['carried_amount']} SAR")
    
    def test_sultan_cannot_execute(self, sultan_session, salah_session, mohammed_session):
        """Sultan cannot execute custody"""
        # Create custody ready for execution
        resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Sultan Execute Test",
            "total_amount": 1000
        })
        custody = resp.json()
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive")
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense", json={
            "code": 1, "description": "Test", "amount": 500
        })
        sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit")
        salah_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit", json={"action": "approve"})
        mohammed_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/approve", json={"action": "approve"})
        
        # Sultan tries to execute
        response = sultan_session.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/execute")
        assert response.status_code == 403
        print("✓ Sultan correctly denied from executing custody")


class TestFinanceCodeManagement(TestAuthSetup):
    """Test finance code add/edit functionality"""
    
    def test_add_new_code_sultan(self, sultan_session):
        """Sultan can add new finance code"""
        unique_code = 900 + (uuid.uuid4().int % 100)
        response = sultan_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_New Code",
            "name_ar": "كود جديد - اختبار",
            "category": "other"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == unique_code
        print(f"✓ Sultan added new code: {unique_code}")
        return data
    
    def test_add_new_code_naif(self, naif_session):
        """Naif can add new finance code"""
        unique_code = 800 + (uuid.uuid4().int % 100)
        response = naif_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_Naif Code",
            "name_ar": "كود نايف",
            "category": "earnings"
        })
        assert response.status_code == 200
        print(f"✓ Naif added new code: {unique_code}")
    
    def test_add_new_code_salah(self, salah_session):
        """Salah can add new finance code"""
        unique_code = 700 + (uuid.uuid4().int % 100)
        response = salah_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_Salah Code",
            "category": "deductions"
        })
        assert response.status_code == 200
        print(f"✓ Salah added new code: {unique_code}")
    
    def test_add_new_code_stas(self, stas_session):
        """STAS can add new finance code"""
        unique_code = 600 + (uuid.uuid4().int % 100)
        response = stas_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_STAS Code",
            "category": "loans"
        })
        assert response.status_code == 200
        print(f"✓ STAS added new code: {unique_code}")
    
    def test_employee_cannot_add_code(self, employee_session):
        """Employee cannot add finance codes"""
        response = employee_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": 999,
            "name": "TEST_Employee Attempt"
        })
        assert response.status_code == 403
        print("✓ Employee correctly denied from adding code")
    
    def test_edit_code_sultan(self, sultan_session):
        """Sultan can edit finance code"""
        # First create a code
        unique_code = 500 + (uuid.uuid4().int % 100)
        create_resp = sultan_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_To Edit",
            "category": "other"
        })
        code_data = create_resp.json()
        
        # Edit it
        response = sultan_session.put(f"{BASE_URL}/api/finance/codes/{code_data['id']}", json={
            "name": "TEST_Edited Name",
            "name_ar": "اسم معدّل"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Edited Name"
        print(f"✓ Sultan edited code - new name: {data['name']}")
    
    def test_edit_code_naif(self, naif_session, sultan_session):
        """Naif can edit finance code"""
        # Create code with sultan
        unique_code = 400 + (uuid.uuid4().int % 100)
        create_resp = sultan_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_Naif Edit Test",
            "category": "other"
        })
        code_data = create_resp.json()
        
        # Naif edits it
        response = naif_session.put(f"{BASE_URL}/api/finance/codes/{code_data['id']}", json={
            "name": "TEST_Naif Edited"
        })
        assert response.status_code == 200
        print(f"✓ Naif edited code successfully")
    
    def test_duplicate_code_rejected(self, sultan_session):
        """Adding duplicate code number is rejected"""
        unique_code = 300 + (uuid.uuid4().int % 50)
        # Create first code
        sultan_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_Original"
        })
        # Try duplicate
        response = sultan_session.post(f"{BASE_URL}/api/finance/codes/add", json={
            "code": unique_code,
            "name": "TEST_Duplicate"
        })
        assert response.status_code == 400
        print("✓ Duplicate code correctly rejected")


class TestDashboardNextHoliday(TestAuthSetup):
    """Test next holiday endpoint"""
    
    def test_get_next_holiday(self, sultan_session):
        """Get next upcoming holiday"""
        response = sultan_session.get(f"{BASE_URL}/api/dashboard/next-holiday")
        assert response.status_code == 200
        # May be null if no upcoming holidays
        data = response.json()
        if data:
            assert "date" in data or "name" in data
            print(f"✓ Next holiday returned: {data}")
        else:
            print("✓ Next holiday endpoint returns null (no upcoming holidays)")


class TestListAndDetailEndpoints(TestAuthSetup):
    """Test listing and detail endpoints"""
    
    def test_list_custodies(self, sultan_session):
        """List all custodies"""
        response = sultan_session.get(f"{BASE_URL}/api/financial-custody")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} custodies")
    
    def test_get_custody_detail(self, sultan_session):
        """Get custody detail"""
        # Create a custody first
        create_resp = sultan_session.post(f"{BASE_URL}/api/financial-custody", json={
            "title": "TEST_Detail Test",
            "total_amount": 1000
        })
        custody = create_resp.json()
        
        response = sultan_session.get(f"{BASE_URL}/api/financial-custody/{custody['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == custody["id"]
        assert data["title"] == "TEST_Detail Test"
        print(f"✓ Got custody detail for #{data['custody_number']}")
    
    def test_list_finance_codes(self, sultan_session):
        """List all finance codes"""
        response = sultan_session.get(f"{BASE_URL}/api/finance/codes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} finance codes")
    
    def test_employee_cannot_list_custodies(self, employee_session):
        """Employee cannot list custodies"""
        response = employee_session.get(f"{BASE_URL}/api/financial-custody")
        assert response.status_code == 403
        print("✓ Employee correctly denied from listing custodies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
