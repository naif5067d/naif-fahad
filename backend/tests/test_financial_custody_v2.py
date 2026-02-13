"""
Test Financial Custody (60 Code) System - Rebuilt Version
Tests the complete custody lifecycle: create → receive → add expenses → audit → approve → execute
Uses Bearer token authentication
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


def get_auth_header(user_id):
    """Switch to user and get auth header"""
    resp = requests.post(f"{BASE_URL}/api/auth/switch/{user_id}")
    if resp.status_code == 200:
        token = resp.json().get("token")
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture(scope="module")
def users():
    """Get all users"""
    response = requests.get(f"{BASE_URL}/api/auth/users")
    assert response.status_code == 200, f"Failed to get users: {response.text}"
    users_list = response.json()
    return {u['role']: u for u in users_list}


@pytest.fixture(scope="module")
def sultan_headers(users):
    """Get Sultan auth headers"""
    return get_auth_header(users['sultan']['id'])


@pytest.fixture(scope="module")
def naif_headers(users):
    """Get Naif auth headers"""
    return get_auth_header(users['naif']['id'])


@pytest.fixture(scope="module")
def salah_headers(users):
    """Get Salah auth headers"""
    return get_auth_header(users['salah']['id'])


@pytest.fixture(scope="module")
def mohammed_headers(users):
    """Get Mohammed auth headers"""
    return get_auth_header(users['mohammed']['id'])


@pytest.fixture(scope="module")
def stas_headers(users):
    """Get STAS auth headers"""
    return get_auth_header(users['stas']['id'])


@pytest.fixture(scope="module")
def employee_headers(users):
    """Get Employee auth headers"""
    emp = next((u for u in users.values() if u['role'] == 'employee'), None)
    if not emp:
        pytest.skip("No employee user found")
    return get_auth_header(emp['id'])


class TestFinancialCustodyCreation:
    """Test custody creation permissions"""
    
    def test_sultan_can_create_custody(self, sultan_headers):
        """Sultan can create financial custody"""
        response = requests.post(f"{BASE_URL}/api/financial-custody", 
            headers=sultan_headers,
            json={
                "title": "TEST_Monthly Expenses",
                "title_ar": "المصروفات الشهرية - اختبار",
                "total_amount": 5000
            })
        assert response.status_code == 200, f"Sultan failed to create custody: {response.text}"
        data = response.json()
        assert data["status"] == "created"
        assert data["total_amount"] == 5000
        assert data["remaining"] == 5000
        assert "custody_number" in data
        print(f"✓ Sultan created custody #{data['custody_number']} with 5000 SAR")
    
    def test_naif_can_create_custody(self, naif_headers):
        """Naif can create financial custody"""
        response = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=naif_headers,
            json={
                "title": "TEST_Office Supplies",
                "title_ar": "مستلزمات المكتب - اختبار",
                "total_amount": 2000
            })
        assert response.status_code == 200, f"Naif failed to create custody: {response.text}"
        data = response.json()
        assert data["status"] == "created"
        print(f"✓ Naif created custody #{data['custody_number']}")
    
    def test_mohammed_can_create_custody(self, mohammed_headers):
        """Mohammed (CEO) can create financial custody"""
        response = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=mohammed_headers,
            json={
                "title": "TEST_CEO Special Project",
                "title_ar": "مشروع خاص - اختبار",
                "total_amount": 10000
            })
        assert response.status_code == 200, f"Mohammed failed to create custody: {response.text}"
        data = response.json()
        print(f"✓ Mohammed created custody #{data['custody_number']}")
    
    def test_salah_cannot_create_custody(self, salah_headers):
        """Salah (Finance) cannot create financial custody"""
        response = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=salah_headers,
            json={
                "title": "TEST_Salah Attempt",
                "total_amount": 1000
            })
        assert response.status_code == 403, f"Salah should be denied: {response.text}"
        print("✓ Salah correctly denied from creating custody")
    
    def test_employee_cannot_create_custody(self, employee_headers):
        """Employee cannot create financial custody"""
        response = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=employee_headers,
            json={
                "title": "TEST_Employee Attempt",
                "total_amount": 500
            })
        assert response.status_code == 403, f"Employee should be denied: {response.text}"
        print("✓ Employee correctly denied from creating custody")


class TestFinancialCustodyReceive:
    """Test custody receive functionality"""
    
    def test_receive_sets_status_to_active(self, sultan_headers):
        """Receiving custody sets status to active"""
        # Create custody
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Receive Test", "total_amount": 3000})
        assert create_resp.status_code == 200
        custody = create_resp.json()
        
        # Receive it
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        assert response.status_code == 200, f"Failed to receive custody: {response.text}"
        data = response.json()
        assert data["status"] == "active"
        print(f"✓ Custody received - status is now 'active'")
        
        # Verify can't receive again
        response2 = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        assert response2.status_code == 400
        print("✓ Already received custody correctly rejected")


class TestFinancialCustodyExpenses:
    """Test expense management"""
    
    def test_sultan_can_add_expense_and_remaining_decreases(self, sultan_headers):
        """Sultan can add expense - remaining decreases correctly"""
        # Create and receive custody
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Expense Test", "total_amount": 10000})
        custody = create_resp.json()
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        
        # Add expense
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=sultan_headers,
            json={"code": 1, "description": "Office supplies purchase", "amount": 500})
        assert response.status_code == 200, f"Failed to add expense: {response.text}"
        data = response.json()
        assert data["total_spent"] == 500
        assert data["remaining"] == 9500  # 10000 - 500
        print(f"✓ Expense added - spent: {data['total_spent']}, remaining: {data['remaining']}")
        
        # Add another expense
        response2 = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=sultan_headers,
            json={"code": 2, "description": "Transportation costs", "amount": 300})
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["total_spent"] == 800  # 500 + 300
        assert data2["remaining"] == 9200  # 10000 - 800
        print(f"✓ Multiple expenses accumulated - spent: {data2['total_spent']}, remaining: {data2['remaining']}")
        
        # Test excessive expense
        response3 = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=sultan_headers,
            json={"code": 3, "description": "Excessive expense", "amount": 99999})
        assert response3.status_code == 400
        print("✓ Excessive expense correctly rejected")
    
    def test_salah_cannot_add_expense(self, sultan_headers, salah_headers):
        """Salah cannot add expenses"""
        # Create active custody
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Salah Expense Test", "total_amount": 5000})
        custody = create_resp.json()
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        
        # Salah tries to add expense
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=salah_headers,
            json={"code": 1, "description": "Salah attempt", "amount": 100})
        assert response.status_code == 403
        print("✓ Salah correctly denied from adding expense")


class TestFinancialCustodyAuditWorkflow:
    """Test audit workflow"""
    
    def test_submit_for_audit_and_approval_flow(self, sultan_headers, salah_headers):
        """Test full audit flow: submit → audit approve"""
        # Create, receive, add expense
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Audit Test", "total_amount": 5000})
        custody = create_resp.json()
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=sultan_headers,
            json={"code": 1, "description": "Test expense", "amount": 1000})
        
        # Submit for audit
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit",
            headers=sultan_headers)
        assert response.status_code == 200, f"Failed to submit for audit: {response.text}"
        data = response.json()
        assert data["status"] == "pending_audit"
        print(f"✓ Submitted for audit - status: {data['status']}")
        
        # Salah approves audit
        response2 = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit",
            headers=salah_headers,
            json={"action": "approve", "note": "Audited and approved"})
        assert response2.status_code == 200, f"Salah failed to approve: {response2.text}"
        data2 = response2.json()
        assert data2["status"] == "pending_approval"
        print(f"✓ Salah approved audit - status: {data2['status']}")
    
    def test_cannot_submit_empty_custody(self, sultan_headers):
        """Cannot submit custody with no expenses"""
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Empty Custody", "total_amount": 1000})
        custody = create_resp.json()
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit",
            headers=sultan_headers)
        assert response.status_code == 400
        print("✓ Empty custody correctly rejected from audit submission")
    
    def test_salah_can_reject_audit(self, sultan_headers, salah_headers):
        """Salah can reject audit - returns to active"""
        # Create custody ready for audit
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Audit Rejection", "total_amount": 2000})
        custody = create_resp.json()
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/receive",
            headers=sultan_headers)
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/expense",
            headers=sultan_headers,
            json={"code": 1, "description": "Test", "amount": 500})
        requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/submit-audit",
            headers=sultan_headers)
        
        # Salah rejects
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody['id']}/audit",
            headers=salah_headers,
            json={"action": "reject", "note": "Needs corrections"})
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        print("✓ Salah rejected audit - custody returned to active status")


class TestFinancialCustodyApprovalAndExecution:
    """Test CEO approval and STAS execution"""
    
    def test_full_workflow_to_execution(self, sultan_headers, salah_headers, mohammed_headers, stas_headers):
        """Test complete workflow: create → receive → expense → audit → approve → execute"""
        # Create custody
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Full Workflow", "total_amount": 5000})
        custody = create_resp.json()
        custody_id = custody['id']
        
        # Receive
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/receive",
            headers=sultan_headers)
        
        # Add expense (partial spend to test carry forward)
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/expense",
            headers=sultan_headers,
            json={"code": 1, "description": "Partial expense", "amount": 3000})
        
        # Submit for audit
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/submit-audit",
            headers=sultan_headers)
        
        # Salah audits
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/audit",
            headers=salah_headers,
            json={"action": "approve"})
        
        # Mohammed approves
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/approve",
            headers=mohammed_headers,
            json={"action": "approve", "note": "Approved by CEO"})
        assert response.status_code == 200
        assert response.json()["status"] == "pending_stas"
        print(f"✓ Mohammed approved custody - status: pending_stas")
        
        # STAS executes
        response2 = requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/execute",
            headers=stas_headers)
        assert response2.status_code == 200, f"STAS failed to execute: {response2.text}"
        data = response2.json()
        assert data["status"] == "executed"
        # Should have carried_to since remaining (2000) > 0
        assert data["carried_to"] is not None
        print(f"✓ STAS executed custody - remaining 2000 SAR carried to new custody")
        
        # Verify the new custody was created with carried amount
        new_custody_resp = requests.get(f"{BASE_URL}/api/financial-custody/{data['carried_to']}",
            headers=stas_headers)
        new_custody = new_custody_resp.json()
        assert new_custody["carried_amount"] == 2000
        assert new_custody["remaining"] == 2000
        print(f"✓ New custody created with carried amount: {new_custody['carried_amount']} SAR")
    
    def test_sultan_cannot_approve_or_execute(self, sultan_headers, salah_headers, mohammed_headers):
        """Sultan cannot perform CEO approval or STAS execution"""
        # Create custody ready for approval
        create_resp = requests.post(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers,
            json={"title": "TEST_Sultan Approval Test", "total_amount": 1000})
        custody = create_resp.json()
        custody_id = custody['id']
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/receive",
            headers=sultan_headers)
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/expense",
            headers=sultan_headers,
            json={"code": 1, "description": "Test", "amount": 500})
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/submit-audit",
            headers=sultan_headers)
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/audit",
            headers=salah_headers,
            json={"action": "approve"})
        
        # Sultan tries to approve
        response = requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/approve",
            headers=sultan_headers,
            json={"action": "approve"})
        assert response.status_code == 403
        print("✓ Sultan correctly denied from CEO approval")
        
        # Mohammed approves to get to pending_stas
        requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/approve",
            headers=mohammed_headers,
            json={"action": "approve"})
        
        # Sultan tries to execute
        response2 = requests.post(f"{BASE_URL}/api/financial-custody/{custody_id}/execute",
            headers=sultan_headers)
        assert response2.status_code == 403
        print("✓ Sultan correctly denied from executing custody")


class TestFinanceCodeManagement:
    """Test finance code add/edit functionality"""
    
    def test_add_new_code_authorized_roles(self, sultan_headers, naif_headers, salah_headers, stas_headers):
        """Sultan/Naif/Salah/STAS can add new finance codes"""
        roles = [
            ("sultan", sultan_headers),
            ("naif", naif_headers),
            ("salah", salah_headers),
            ("stas", stas_headers)
        ]
        
        for role_name, headers in roles:
            unique_code = 100 + (uuid.uuid4().int % 900)
            response = requests.post(f"{BASE_URL}/api/finance/codes/add",
                headers=headers,
                json={
                    "code": unique_code,
                    "name": f"TEST_{role_name}_Code",
                    "name_ar": f"كود {role_name}",
                    "category": "other"
                })
            assert response.status_code == 200, f"{role_name} failed to add code: {response.text}"
            print(f"✓ {role_name} added new code: {unique_code}")
    
    def test_employee_cannot_add_code(self, employee_headers):
        """Employee cannot add finance codes"""
        response = requests.post(f"{BASE_URL}/api/finance/codes/add",
            headers=employee_headers,
            json={"code": 999, "name": "TEST_Employee Attempt"})
        assert response.status_code == 403
        print("✓ Employee correctly denied from adding code")
    
    def test_edit_code_authorized_roles(self, sultan_headers, naif_headers):
        """Sultan/Naif/Salah/STAS can edit finance codes"""
        # Create code
        unique_code = 200 + (uuid.uuid4().int % 100)
        create_resp = requests.post(f"{BASE_URL}/api/finance/codes/add",
            headers=sultan_headers,
            json={"code": unique_code, "name": "TEST_To Edit", "category": "other"})
        code_data = create_resp.json()
        
        # Edit with Naif
        response = requests.put(f"{BASE_URL}/api/finance/codes/{code_data['id']}",
            headers=naif_headers,
            json={"name": "TEST_Edited Name", "name_ar": "اسم معدّل"})
        assert response.status_code == 200, f"Failed to edit code: {response.text}"
        data = response.json()
        assert data["name"] == "TEST_Edited Name"
        print(f"✓ Code edited successfully - new name: {data['name']}")
    
    def test_duplicate_code_rejected(self, sultan_headers):
        """Adding duplicate code number is rejected"""
        unique_code = 300 + (uuid.uuid4().int % 50)
        # Create first code
        requests.post(f"{BASE_URL}/api/finance/codes/add",
            headers=sultan_headers,
            json={"code": unique_code, "name": "TEST_Original"})
        # Try duplicate
        response = requests.post(f"{BASE_URL}/api/finance/codes/add",
            headers=sultan_headers,
            json={"code": unique_code, "name": "TEST_Duplicate"})
        assert response.status_code == 400
        print("✓ Duplicate code correctly rejected")


class TestDashboardAndListEndpoints:
    """Test dashboard and list endpoints"""
    
    def test_get_next_holiday(self, sultan_headers):
        """Get next upcoming holiday"""
        response = requests.get(f"{BASE_URL}/api/dashboard/next-holiday",
            headers=sultan_headers)
        assert response.status_code == 200
        data = response.json()
        if data:
            print(f"✓ Next holiday: {data.get('name', data)}")
        else:
            print("✓ No upcoming holidays (null response)")
    
    def test_list_custodies(self, sultan_headers):
        """List all custodies"""
        response = requests.get(f"{BASE_URL}/api/financial-custody",
            headers=sultan_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} custodies")
    
    def test_list_finance_codes(self, sultan_headers):
        """List all finance codes"""
        response = requests.get(f"{BASE_URL}/api/finance/codes",
            headers=sultan_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} finance codes")
    
    def test_employee_cannot_list_custodies(self, employee_headers):
        """Employee cannot list custodies"""
        response = requests.get(f"{BASE_URL}/api/financial-custody",
            headers=employee_headers)
        assert response.status_code == 403
        print("✓ Employee correctly denied from listing custodies")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
