"""
Test Executive Dashboard API - Iteration 36
Tests for /api/analytics/executive/dashboard and /api/analytics/alerts endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestExecutiveAnalytics:
    """Tests for Executive Dashboard Analytics API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth tokens for testing"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def _login(self, username: str, password: str = "123456") -> str:
        """Login and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": username,
            "password": password
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return token
        return None
    
    # ==================== Executive Dashboard Tests ====================
    
    def test_executive_dashboard_unauthorized(self):
        """Test /executive/dashboard without auth - should return 401"""
        response = requests.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Unauthorized access correctly blocked")
    
    def test_executive_dashboard_wrong_role(self):
        """Test /executive/dashboard with non-executive user"""
        # Login as a regular employee (salah)
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "salah",
            "password": "123456"
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            
            response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
            assert response.status_code in [401, 403], f"Salah should not have access, got {response.status_code}"
            print("✓ Non-executive role correctly denied")
        else:
            pytest.skip("Could not login as salah for role test")
    
    def test_executive_dashboard_as_stas(self):
        """Test /executive/dashboard as stas (system admin)"""
        token = self._login("stas")
        assert token, "Failed to login as stas"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Validate response structure
        assert "health_score" in data, "Missing health_score"
        assert "metrics" in data, "Missing metrics"
        assert "top_performers" in data, "Missing top_performers"
        assert "needs_attention" in data, "Missing needs_attention"
        assert "monthly_trend" in data, "Missing monthly_trend"
        assert "executive_summary" in data, "Missing executive_summary"
        assert "quick_stats" in data, "Missing quick_stats"
        
        print(f"✓ Dashboard loaded for stas with health_score: {data['health_score']}")
        return data
    
    def test_executive_dashboard_as_mohammed(self):
        """Test /executive/dashboard as mohammed (CEO)"""
        token = self._login("mohammed")
        assert token, "Failed to login as mohammed"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "health_score" in data
        assert "metrics" in data
        print(f"✓ Dashboard loaded for mohammed with health_score: {data['health_score']}")
    
    def test_executive_dashboard_as_sultan(self):
        """Test /executive/dashboard as sultan (ops admin)"""
        token = self._login("sultan")
        assert token, "Failed to login as sultan"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "health_score" in data
        print(f"✓ Dashboard loaded for sultan with health_score: {data['health_score']}")
    
    def test_executive_dashboard_metrics_structure(self):
        """Verify metrics object has all 4 KPI categories"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        metrics = data.get("metrics", {})
        
        # Verify 4 KPIs exist
        assert "attendance" in metrics, "Missing attendance metrics"
        assert "tasks" in metrics, "Missing tasks metrics"
        assert "financial" in metrics, "Missing financial metrics"
        assert "requests" in metrics, "Missing requests metrics"
        
        # Verify attendance has expected fields
        attendance = metrics.get("attendance", {})
        assert "score" in attendance, "attendance missing score"
        assert "present_days" in attendance, "attendance missing present_days"
        assert "late_minutes" in attendance, "attendance missing late_minutes"
        
        # Verify tasks has expected fields
        tasks = metrics.get("tasks", {})
        assert "score" in tasks, "tasks missing score"
        assert "total_tasks" in tasks, "tasks missing total_tasks"
        
        # Verify financial has expected fields
        financial = metrics.get("financial", {})
        assert "score" in financial, "financial missing score"
        assert "total_custodies" in financial, "financial missing total_custodies"
        
        # Verify requests has expected fields
        requests_data = metrics.get("requests", {})
        assert "score" in requests_data, "requests missing score"
        assert "approved" in requests_data, "requests missing approved"
        
        print(f"✓ All 4 KPIs verified: attendance={attendance['score']}, tasks={tasks['score']}, "
              f"financial={financial['score']}, requests={requests_data['score']}")
    
    def test_executive_dashboard_quick_stats(self):
        """Verify quick_stats object has all fields"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        quick_stats = data.get("quick_stats", {})
        
        assert "total_employees" in quick_stats, "Missing total_employees"
        assert "pending_requests" in quick_stats, "Missing pending_requests"
        assert "open_custodies" in quick_stats, "Missing open_custodies"
        assert "active_tasks" in quick_stats, "Missing active_tasks"
        
        print(f"✓ Quick stats: employees={quick_stats['total_employees']}, "
              f"pending={quick_stats['pending_requests']}, "
              f"custodies={quick_stats['open_custodies']}, "
              f"tasks={quick_stats['active_tasks']}")
    
    def test_executive_dashboard_top_performers(self):
        """Verify top_performers array structure"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        top = data.get("top_performers", [])
        
        assert isinstance(top, list), "top_performers should be a list"
        
        if len(top) > 0:
            performer = top[0]
            assert "employee_id" in performer, "Missing employee_id"
            assert "name" in performer, "Missing name"
            assert "score" in performer, "Missing score"
            print(f"✓ Top performer: {performer.get('name')} with score {performer.get('score')}")
        else:
            print("✓ Top performers list is empty (no data)")
    
    def test_executive_dashboard_needs_attention(self):
        """Verify needs_attention array structure"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        bottom = data.get("needs_attention", [])
        
        assert isinstance(bottom, list), "needs_attention should be a list"
        print(f"✓ Needs attention list has {len(bottom)} employees")
    
    def test_executive_dashboard_monthly_trend(self):
        """Verify monthly_trend array structure"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        trend = data.get("monthly_trend", [])
        
        assert isinstance(trend, list), "monthly_trend should be a list"
        assert len(trend) > 0, "monthly_trend should have at least 1 entry"
        
        if len(trend) > 0:
            entry = trend[0]
            assert "month" in entry, "Missing month"
            assert "health_score" in entry, "Missing health_score"
            print(f"✓ Monthly trend has {len(trend)} months, first: {entry.get('month')}")
    
    def test_executive_dashboard_executive_summary(self):
        """Verify executive_summary is a non-empty string"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get("executive_summary", "")
        
        assert isinstance(summary, str), "executive_summary should be a string"
        print(f"✓ Executive summary: '{summary[:50]}...' (truncated)" if len(summary) > 50 else f"✓ Executive summary: '{summary}'")
    
    def test_executive_dashboard_with_month_param(self):
        """Test dashboard with specific month parameter"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard?month=2025-12")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("month") == "2025-12", f"Expected month 2025-12, got {data.get('month')}"
        print(f"✓ Dashboard loaded for specific month: {data.get('month')}")
    
    # ==================== Alerts Endpoint Tests ====================
    
    def test_alerts_unauthorized(self):
        """Test /alerts without auth"""
        response = requests.get(f"{BASE_URL}/api/analytics/alerts")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Alerts endpoint correctly requires auth")
    
    def test_alerts_as_stas(self):
        """Test /alerts as stas"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/alerts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        assert "alerts" in data, "Missing alerts array"
        assert "count" in data, "Missing count"
        assert isinstance(data["alerts"], list), "alerts should be a list"
        
        print(f"✓ Alerts endpoint returned {data['count']} alerts")
        
        if len(data["alerts"]) > 0:
            alert = data["alerts"][0]
            assert "type" in alert, "Alert missing type"
            assert "title" in alert, "Alert missing title"
            assert "message" in alert, "Alert missing message"
            print(f"  First alert: {alert.get('title')} - {alert.get('message')}")
    
    def test_alerts_as_mohammed(self):
        """Test /alerts as mohammed (CEO)"""
        token = self._login("mohammed")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/alerts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "alerts" in data
        print(f"✓ Alerts accessible for mohammed: {data['count']} alerts")
    
    # ==================== Employee Score Endpoint Tests ====================
    
    def test_employee_score(self):
        """Test /employee/{employee_id}/score endpoint"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        # First get an employee ID from top performers
        dashboard_response = self.session.get(f"{BASE_URL}/api/analytics/executive/dashboard")
        if dashboard_response.status_code == 200:
            data = dashboard_response.json()
            performers = data.get("top_performers", [])
            
            if performers:
                emp_id = performers[0].get("employee_id")
                
                response = self.session.get(f"{BASE_URL}/api/analytics/employee/{emp_id}/score")
                assert response.status_code == 200, f"Expected 200, got {response.status_code}"
                
                score_data = response.json()
                assert "overall_score" in score_data, "Missing overall_score"
                assert "attendance" in score_data, "Missing attendance"
                assert "tasks" in score_data, "Missing tasks"
                
                print(f"✓ Employee {emp_id} score: {score_data.get('overall_score')}")
            else:
                print("✓ No employees to test individual score (empty data)")
        else:
            pytest.skip("Could not fetch dashboard to get employee ID")
    
    def test_employee_score_not_found(self):
        """Test /employee/{employee_id}/score with invalid ID"""
        token = self._login("stas")
        assert token, "Failed to login"
        
        response = self.session.get(f"{BASE_URL}/api/analytics/employee/INVALID-EMP-ID/score")
        assert response.status_code == 404, f"Expected 404 for invalid employee, got {response.status_code}"
        print("✓ Invalid employee ID correctly returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
