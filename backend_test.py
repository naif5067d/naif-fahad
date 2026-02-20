import requests
import sys
from datetime import datetime
import json

class DarAlCodeAPITester:
    def __init__(self, base_url="https://hr-attendance-fix-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.tokens = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.critical_failures = []

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.status_code >= 500:
                    self.critical_failures.append(f"{name}: {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail')
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")

            try:
                return success, response.json() if response.text else {}
            except:
                return success, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed - Connection Error: {str(e)}")
            self.critical_failures.append(f"{name}: Connection failed")
            return False, {}

    def test_login(self, username, password):
        """Test login and store token"""
        success, response = self.run_test(
            f"Login as {username}",
            "POST",
            "/api/auth/login",
            200,
            data={"username": username, "password": password}
        )
        if success and 'token' in response:
            self.tokens[username] = response['token']
            print(f"   User: {response['user']['full_name']} ({response['user']['role']})")
            return True, response['user']
        return False, {}

    def test_dashboard_stats(self, username):
        """Test dashboard stats for user"""
        if username not in self.tokens:
            print(f"❌ No token for {username}")
            return False
        
        success, response = self.run_test(
            f"Dashboard stats for {username}",
            "GET",
            "/api/dashboard/stats",
            200,
            token=self.tokens[username]
        )
        if success:
            print(f"   Stats keys: {list(response.keys())}")
        return success

    def test_transactions_list(self, username):
        """Test transactions list"""
        if username not in self.tokens:
            return False
        
        success, response = self.run_test(
            f"Transactions list for {username}",
            "GET",
            "/api/transactions",
            200,
            token=self.tokens[username]
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} transactions")
        return success

    def test_leave_balance(self, username):
        """Test leave balance"""
        if username not in self.tokens:
            return False
        
        success, response = self.run_test(
            f"Leave balance for {username}",
            "GET",
            "/api/leave/balance",
            200,
            token=self.tokens[username]
        )
        if success:
            print(f"   Leave balance: {response}")
        return success

    def test_leave_request(self, username):
        """Test creating a leave request"""
        if username not in self.tokens:
            return False
        
        leave_data = {
            "leave_type": "annual",
            "start_date": "2024-12-20",
            "end_date": "2024-12-22",
            "reason": "Test leave request"
        }
        
        success, response = self.run_test(
            f"Create leave request for {username}",
            "POST",
            "/api/leave/request",
            200,
            data=leave_data,
            token=self.tokens[username]
        )
        if success and 'id' in response:
            print(f"   Created transaction: {response.get('ref_no')}")
            return response['id']
        return None

    def test_transaction_action(self, username, transaction_id, action):
        """Test approving/rejecting a transaction"""
        if username not in self.tokens or not transaction_id:
            return False
        
        success, response = self.run_test(
            f"{action.title()} transaction by {username}",
            "POST",
            f"/api/transactions/{transaction_id}/action",
            200,
            data={"action": action, "note": f"Test {action} by {username}"},
            token=self.tokens[username]
        )
        if success:
            print(f"   Result: {response.get('message')}")
        return success

    def test_stas_mirror(self, username, transaction_id):
        """Test STAS mirror view"""
        if username not in self.tokens or not transaction_id:
            return False
        
        success, response = self.run_test(
            f"STAS mirror for transaction {transaction_id}",
            "GET",
            f"/api/stas/mirror/{transaction_id}",
            200,
            token=self.tokens[username]
        )
        if success:
            all_pass = response.get('all_checks_pass', False)
            print(f"   Pre-checks pass: {all_pass}")
            checks = response.get('pre_checks', [])
            print(f"   Checks: {len(checks)} total")
        return success, response

    def test_stas_execute(self, username, transaction_id):
        """Test STAS transaction execution"""
        if username not in self.tokens or not transaction_id:
            return False
        
        success, response = self.run_test(
            f"STAS execute transaction {transaction_id}",
            "POST",
            f"/api/stas/execute/{transaction_id}",
            200,
            token=self.tokens[username]
        )
        if success:
            print(f"   Executed: {response.get('ref_no')} - Hash: {response.get('pdf_hash', 'None')[:12]}...")
        return success

    def test_finance_codes(self, username):
        """Test finance codes list"""
        if username not in self.tokens:
            return False
        
        success, response = self.run_test(
            f"Finance codes for {username}",
            "GET",
            "/api/finance/codes",
            200,
            token=self.tokens[username]
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} finance codes")
        return success

    def test_employees_list(self, username):
        """Test employees list"""
        if username not in self.tokens:
            return False
        
        success, response = self.run_test(
            f"Employees list for {username}",
            "GET",
            "/api/employees",
            200,
            token=self.tokens[username]
        )
        if success and isinstance(response, list):
            print(f"   Found {len(response)} employees")
        return success

    def test_attendance_today(self, username):
        """Test today's attendance"""
        if username not in self.tokens:
            return False
        
        success, response = self.run_test(
            f"Today attendance for {username}",
            "GET",
            "/api/attendance/today",
            200,
            token=self.tokens[username]
        )
        return success

def main():
    print("🚀 DAR AL CODE HR OS - API Testing Suite")
    print(f"Backend URL: https://hr-attendance-fix-2.preview.emergentagent.com")
    print("=" * 60)

    tester = DarAlCodeAPITester()
    
    # Test users with their roles
    test_users = [
        ("stas", "DarAlCode2026!"),
        ("mohammed", "DarAlCode2026!"),
        ("sultan", "DarAlCode2026!"),
        ("naif", "DarAlCode2026!"),
        ("salah", "DarAlCode2026!"),
        ("supervisor1", "DarAlCode2026!"),
        ("employee1", "DarAlCode2026!"),
        ("employee2", "DarAlCode2026!")
    ]

    print("\n📋 PHASE 1: Authentication Testing")
    print("-" * 40)
    
    # Test login for all users
    logged_in_users = {}
    for username, password in test_users:
        success, user_data = tester.test_login(username, password)
        if success:
            logged_in_users[username] = user_data

    if len(logged_in_users) < 4:
        print(f"\n⚠️  CRITICAL: Only {len(logged_in_users)}/{len(test_users)} users logged in successfully")
        tester.critical_failures.append("Authentication: Multiple users failed to login")

    print("\n📊 PHASE 2: Dashboard & Basic Features")
    print("-" * 40)

    # Test basic features for key users
    key_users = ['employee1', 'supervisor1', 'sultan', 'stas', 'mohammed']
    
    for username in key_users:
        if username in logged_in_users:
            tester.test_dashboard_stats(username)
            tester.test_transactions_list(username)
            
            # Role-specific tests
            if username in ['employee1', 'supervisor1']:
                tester.test_leave_balance(username)
                tester.test_attendance_today(username)
            
            if username in ['sultan', 'naif', 'salah', 'stas']:
                tester.test_finance_codes(username)
                tester.test_employees_list(username)

    print("\n🔄 PHASE 3: Workflow Testing (Leave Request)")
    print("-" * 40)
    
    # Create leave request as employee1
    tx_id = None
    if 'employee1' in logged_in_users:
        tx_id = tester.test_leave_request('employee1')

    # Test approval workflow
    if tx_id:
        # Supervisor approval
        if 'supervisor1' in logged_in_users:
            tester.test_transaction_action('supervisor1', tx_id, 'approve')
        
        # Ops approval (sultan)
        if 'sultan' in logged_in_users:
            tester.test_transaction_action('sultan', tx_id, 'approve')

        # STAS mirror and execution
        if 'stas' in logged_in_users:
            success, mirror_data = tester.test_stas_mirror('stas', tx_id)
            if success and mirror_data.get('all_checks_pass'):
                tester.test_stas_execute('stas', tx_id)

    print("\n📄 PHASE 4: Additional API Tests")
    print("-" * 40)
    
    # Test health endpoint
    tester.run_test("Health Check", "GET", "/api/health", 200)

    # Print final results
    print(f"\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.critical_failures:
        print(f"\n❌ CRITICAL FAILURES ({len(tester.critical_failures)}):")
        for failure in tester.critical_failures:
            print(f"   • {failure}")
    else:
        print(f"\n✅ No critical failures detected")

    print(f"\nLogged in users: {len(logged_in_users)}/{len(test_users)}")
    for username, user_data in logged_in_users.items():
        print(f"   • {username}: {user_data.get('full_name')} ({user_data.get('role')})")

    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())