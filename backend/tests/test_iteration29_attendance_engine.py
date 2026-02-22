"""
Iteration 29 - Attendance Engine Testing
Tests for:
1. Day Resolver (day_resolver.py, day_resolver_v2.py)
2. Daily Processing API (/api/attendance-engine/process-daily)
3. My Finances Summary API (/api/attendance-engine/my-finances/summary)
4. Scheduler Jobs
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hr-smart-system.preview.emergentagent.com')

@pytest.fixture
def session():
    """Create requests session"""
    return requests.Session()

@pytest.fixture
def admin_auth(session):
    """Authenticate as STAS admin"""
    # Get users to find STAS id
    users_resp = session.get(f"{BASE_URL}/api/auth/users")
    assert users_resp.status_code == 200
    
    stas_user = next((u for u in users_resp.json() if u['username'] == 'stas'), None)
    assert stas_user is not None, "STAS user not found"
    
    # Switch to STAS user - get JWT token
    switch_resp = session.post(f"{BASE_URL}/api/auth/switch/{stas_user['id']}")
    assert switch_resp.status_code == 200
    
    token = switch_resp.json().get('token')
    assert token is not None, "No token returned"
    
    # Set Authorization header
    session.headers.update({'Authorization': f'Bearer {token}'})
    
    return session

@pytest.fixture
def employee_auth(session):
    """Authenticate as employee"""
    # Get users to find employee
    users_resp = session.get(f"{BASE_URL}/api/auth/users")
    assert users_resp.status_code == 200
    
    emp_user = next((u for u in users_resp.json() if u['username'] == 'emp2c291a9b'), None)
    assert emp_user is not None, "Employee user not found"
    
    # Switch to employee - get JWT token
    switch_resp = session.post(f"{BASE_URL}/api/auth/switch/{emp_user['id']}")
    assert switch_resp.status_code == 200
    
    token = switch_resp.json().get('token')
    assert token is not None, "No token returned"
    
    # Set Authorization header
    session.headers.update({'Authorization': f'Bearer {token}'})
    
    return session


class TestHealthCheck:
    """Health check tests"""
    
    def test_api_health(self, session):
        """Test API is healthy"""
        resp = session.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'ok'
        print(f"✓ API Health OK: version {data['version']}")


class TestDayResolver:
    """Day Resolver API Tests"""
    
    def test_resolve_day_for_employee(self, admin_auth):
        """Test resolving a day for a specific employee"""
        # Get an employee
        emp_resp = admin_auth.get(f"{BASE_URL}/api/employees")
        assert emp_resp.status_code == 200
        employees = emp_resp.json()
        assert len(employees) > 0
        
        # Find non-admin employee
        employee = next((e for e in employees if e.get('id') not in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']), None)
        
        if employee is None:
            pytest.skip("No non-admin employee found")
        
        # Resolve today
        today = datetime.now().strftime("%Y-%m-%d")
        resolve_resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/resolve-day",
            json={"employee_id": employee['id'], "date": today}
        )
        
        assert resolve_resp.status_code == 200
        data = resolve_resp.json()
        
        # Check response structure
        assert 'final_status' in data or 'error' in data
        
        if not data.get('error'):
            assert 'status_ar' in data
            assert 'decision_source' in data
            assert 'trace_log' in data  # V2 includes trace
            print(f"✓ Resolve Day: {employee['id']} -> {data.get('final_status')} ({data.get('decision_source')})")
        else:
            print(f"! Resolve Day Error: {data.get('message')}")
    
    def test_resolve_day_returns_trace_log(self, admin_auth):
        """Test that resolve day returns trace evidence"""
        emp_resp = admin_auth.get(f"{BASE_URL}/api/employees")
        employees = emp_resp.json()
        employee = next((e for e in employees if e.get('id') not in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']), None)
        
        if employee is None:
            pytest.skip("No non-admin employee found")
        
        today = datetime.now().strftime("%Y-%m-%d")
        resolve_resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/resolve-day",
            json={"employee_id": employee['id'], "date": today}
        )
        
        data = resolve_resp.json()
        
        if not data.get('error'):
            assert 'trace_log' in data, "trace_log should be in response"
            assert 'trace_summary' in data, "trace_summary should be in response"
            
            trace_log = data['trace_log']
            assert isinstance(trace_log, list), "trace_log should be a list"
            assert len(trace_log) > 0, "trace_log should not be empty"
            
            # Check trace log structure
            for step in trace_log:
                assert 'step' in step
                assert 'checked' in step
                assert 'found' in step
            
            print(f"✓ Trace Log has {len(trace_log)} steps")
            print(f"✓ Summary: {data['trace_summary'].get('conclusion_ar', 'N/A')}")


class TestProcessDaily:
    """Process Daily API Tests"""
    
    def test_process_daily_endpoint(self, admin_auth):
        """Test /api/attendance-engine/process-daily endpoint"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/process-daily",
            json={"date": today}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert data.get('success') == True
        assert 'processed' in data
        assert 'skipped' in data
        assert 'message_ar' in data
        
        print(f"✓ Process Daily: {data['processed']} processed, {data['skipped']} skipped")
        print(f"  Message: {data['message_ar']}")
    
    def test_process_daily_excludes_admin_users(self, admin_auth):
        """Test that admin users are excluded from daily processing"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/process-daily",
            json={"date": today}
        )
        
        data = resp.json()
        results = data.get('results', [])
        
        # Check that STAS, MOHAMMED, NAIF are not in results
        processed_ids = [r['employee_id'] for r in results]
        excluded_ids = ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-004', 'EMP-NAIF']
        
        for excluded in excluded_ids:
            assert excluded not in processed_ids, f"{excluded} should be excluded"
        
        print(f"✓ Excluded admin users confirmed")


class TestMyFinances:
    """My Finances API Tests"""
    
    def test_my_finances_summary_endpoint(self, employee_auth):
        """Test /api/attendance-engine/my-finances/summary endpoint"""
        resp = employee_auth.get(f"{BASE_URL}/api/attendance-engine/my-finances/summary")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Check response structure
        assert 'employee_id' in data
        assert 'current_month' in data
        assert 'current_year' in data
        assert 'monthly_deductions' in data
        assert 'yearly_deductions' in data
        assert 'warnings_count' in data
        assert 'absence_summary' in data
        
        # Check monthly_deductions structure
        assert 'total' in data['monthly_deductions']
        assert 'count' in data['monthly_deductions']
        
        # Check absence_summary structure
        assert 'total_absent_days' in data['absence_summary']
        assert 'max_consecutive' in data['absence_summary']
        
        print(f"✓ My Finances Summary:")
        print(f"  - Employee: {data['employee_id']}")
        print(f"  - Monthly Deductions: {data['monthly_deductions']['total']} ({data['monthly_deductions']['count']} deductions)")
        print(f"  - Yearly Deductions: {data['yearly_deductions']['total']} ({data['yearly_deductions']['count']} deductions)")
        print(f"  - Warnings: {data['warnings_count']}")
        print(f"  - Absent Days: {data['absence_summary']['total_absent_days']}")
    
    def test_my_finances_deductions_endpoint(self, employee_auth):
        """Test /api/attendance-engine/my-finances/deductions endpoint"""
        resp = employee_auth.get(f"{BASE_URL}/api/attendance-engine/my-finances/deductions")
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"✓ My Finances Deductions: {len(data)} deductions")
    
    def test_my_finances_warnings_endpoint(self, employee_auth):
        """Test /api/attendance-engine/my-finances/warnings endpoint"""
        resp = employee_auth.get(f"{BASE_URL}/api/attendance-engine/my-finances/warnings")
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"✓ My Finances Warnings: {len(data)} warnings")


class TestDailyStatus:
    """Daily Status API Tests"""
    
    def test_get_daily_status(self, admin_auth):
        """Test getting daily status for an employee"""
        # Get an employee
        emp_resp = admin_auth.get(f"{BASE_URL}/api/employees")
        employees = emp_resp.json()
        employee = next((e for e in employees if e.get('id') not in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']), None)
        
        if employee is None:
            pytest.skip("No non-admin employee found")
        
        today = datetime.now().strftime("%Y-%m-%d")
        resp = admin_auth.get(f"{BASE_URL}/api/attendance-engine/daily-status/{employee['id']}/{today}")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Should have a status
        assert 'final_status' in data or 'error' in data
        print(f"✓ Daily Status: {employee['id']} -> {data.get('final_status', data.get('message', 'Unknown'))}")
    
    def test_get_daily_status_range(self, admin_auth):
        """Test getting daily status range for an employee"""
        # Get an employee
        emp_resp = admin_auth.get(f"{BASE_URL}/api/employees")
        employees = emp_resp.json()
        employee = next((e for e in employees if e.get('id') not in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']), None)
        
        if employee is None:
            pytest.skip("No non-admin employee found")
        
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        resp = admin_auth.get(
            f"{BASE_URL}/api/attendance-engine/daily-status-range/{employee['id']}",
            params={"start_date": start_date, "end_date": end_date}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"✓ Daily Status Range: {len(data)} records for {start_date} to {end_date}")


class TestTeamAttendance:
    """Team Attendance API Tests"""
    
    def test_team_attendance_day(self, admin_auth):
        """Test getting team attendance for a day"""
        today = datetime.now().strftime("%Y-%m-%d")
        resp = admin_auth.get(f"{BASE_URL}/api/attendance-engine/team-attendance/{today}")
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"✓ Team Attendance Day: {len(data)} records")


class TestMonthlyHours:
    """Monthly Hours API Tests"""
    
    def test_get_monthly_hours(self, admin_auth):
        """Test getting monthly hours for an employee"""
        # Get an employee
        emp_resp = admin_auth.get(f"{BASE_URL}/api/employees")
        employees = emp_resp.json()
        employee = next((e for e in employees if e.get('id') not in ['EMP-STAS', 'EMP-MOHAMMED', 'EMP-NAIF']), None)
        
        if employee is None:
            pytest.skip("No non-admin employee found")
        
        current_month = datetime.now().strftime("%Y-%m")
        resp = admin_auth.get(f"{BASE_URL}/api/attendance-engine/monthly-hours/{employee['id']}/{current_month}")
        
        assert resp.status_code == 200
        data = resp.json()
        
        # Check response structure
        assert 'employee_id' in data or 'actual_hours' in data
        
        if 'actual_hours' in data:
            print(f"✓ Monthly Hours: {data.get('actual_hours', 0)} / {data.get('required_hours', 0)} hours")
            print(f"  - Deficit: {data.get('deficit_hours', 0)} hours")
        else:
            print(f"✓ Monthly Hours calculated")


class TestSchedulerJobs:
    """Test scheduler-related Jobs API"""
    
    def test_jobs_daily_endpoint(self, admin_auth):
        """Test jobs/daily endpoint"""
        resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/jobs/daily",
            json={}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        print(f"✓ Jobs Daily: {data}")
    
    def test_jobs_logs_endpoint(self, admin_auth):
        """Test jobs/logs endpoint"""
        resp = admin_auth.get(f"{BASE_URL}/api/attendance-engine/jobs/logs")
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert isinstance(data, list)
        print(f"✓ Jobs Logs: {len(data)} logs")


class TestResolveBulk:
    """Test bulk resolve API"""
    
    def test_resolve_bulk(self, admin_auth):
        """Test resolving day for all employees"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        resp = admin_auth.post(
            f"{BASE_URL}/api/attendance-engine/resolve-bulk",
            json={"date": today}
        )
        
        assert resp.status_code == 200
        data = resp.json()
        
        assert 'processed' in data
        assert 'results' in data
        
        print(f"✓ Resolve Bulk: {data['processed']} employees processed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
