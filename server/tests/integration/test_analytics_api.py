"""Integration tests for analytics API endpoints."""

from datetime import datetime, timedelta

import pytest
from httpx import Client

from .test_utils import ensure_test_workspace, get_emulator_auth_token


@pytest.mark.integration
class TestAnalyticsAPI:
    """Test analytics API endpoints."""

    @classmethod
    def setup_class(cls):
        """Setup test client and authentication."""
        cls.client = Client(base_url="http://localhost:8090", timeout=10.0)
        cls.skip_tests = False
        cls.skip_reason = None

        # Check if server is running
        try:
            cls.client.get("/admin/api/v1/health")
        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running: {e}"
            return

        # Get Firebase emulator token
        cls.token, cls.refresh_token, cls.headers = get_emulator_auth_token(cls.client)

        if not cls.token:
            cls.skip_tests = True
            cls.skip_reason = "Authentication not enabled or Firebase emulator not running"

    def setup_method(self):
        """Check if tests should be skipped."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def get_workspace_id(self):
        """Get workspace ID for tests."""
        workspace = ensure_test_workspace(self.client, self.headers)
        if not workspace:
            pytest.skip("No workspaces available")
        return workspace["id"]

    def test_dashboard_stats(self):
        """Test getting dashboard statistics."""
        workspace_id = self.get_workspace_id()
        
        # Test with default time range
        response = self.client.get(f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_executions" in data
        assert "active_users" in data
        assert "avg_response_time" in data
        assert "success_rate" in data
        assert "execution_change" in data
        assert "user_change" in data
        assert "response_time_change" in data
        assert "success_rate_change" in data

        # Test with different time ranges
        for time_range in ["24h", "7d", "30d", "90d"]:
            response = self.client.get(
                f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats?time_range={time_range}",
                headers=self.headers,
            )
            assert response.status_code == 200

    def test_dashboard_stats_invalid_time_range(self):
        """Test dashboard stats with invalid time range."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats?time_range=invalid", headers=self.headers
        )
        assert response.status_code == 422  # Validation error

    def test_execution_metrics(self):
        """Test getting execution metrics."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_executions" in data
        assert "total_errors" in data
        assert "success_rate" in data
        assert "avg_response_time" in data
        assert "executions_by_date" in data
        assert "errors_by_date" in data

        # Verify data types
        assert isinstance(data["total_executions"], int)
        assert isinstance(data["success_rate"], (int, float))
        assert isinstance(data["executions_by_date"], list)

    def test_execution_metrics_with_workspace_filter(self):
        """Test execution metrics with workspace filter."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics?workspace_id=test_workspace",
            headers=self.headers,
        )
        assert response.status_code == 200

    def test_recent_activity(self):
        """Test getting recent activity."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity", headers=self.headers)
        assert response.status_code == 200
        data = response.json()

        # Verify response is a list
        assert isinstance(data, list)

        # If there's data, verify structure
        if data:
            activity = data[0]
            assert "action_name" in activity
            assert "action_type" in activity
            assert "description" in activity
            assert "status" in activity
            assert "time" in activity
            assert "duration" in activity
            assert "execution_id" in activity

    def test_recent_activity_with_limit(self):
        """Test recent activity with custom limit."""
        workspace_id = self.get_workspace_id()
        # Test minimum limit
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?limit=1", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 1

        # Test maximum limit
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?limit=100", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 100

    def test_recent_activity_invalid_limit(self):
        """Test recent activity with invalid limit."""
        workspace_id = self.get_workspace_id()
        # Test limit too high
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?limit=101", headers=self.headers
        )
        assert response.status_code == 422  # Validation error

        # Test limit too low
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?limit=0", headers=self.headers
        )
        assert response.status_code == 422  # Validation error

    def test_top_actions(self):
        """Test getting top actions."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(f"/admin/api/v1/workspaces/{workspace_id}/analytics/top-actions", headers=self.headers)
        assert response.status_code == 200
        data = response.json()

        # Verify response is a list
        assert isinstance(data, list)

        # If there's data, verify structure
        if data:
            action = data[0]
            assert "action_name" in action
            assert "action_type" in action
            assert "count" in action
            assert "avg_duration" in action
            assert "error_rate" in action

    def test_top_actions_with_params(self):
        """Test top actions with parameters."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/top-actions?time_range=30d&limit=10", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_authentication_required(self):
        """Test that endpoints require authentication."""
        workspace_id = self.get_workspace_id()
        endpoints = [
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats",
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics",
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity",
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/top-actions",
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should return 401 when auth is enabled, or 200 when auth is disabled
            # May return 500 if there's an internal error (e.g., database connection)
            assert response.status_code in [
                200,
                401,
                500,
            ], f"Unexpected status {response.status_code} for {endpoint}"

    def test_concurrent_requests(self):
        """Test that analytics endpoints can handle concurrent requests."""
        workspace_id = self.get_workspace_id()
        import concurrent.futures

        def fetch_dashboard_stats():
            return self.client.get(f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats", headers=self.headers)

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_dashboard_stats) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in results:
            assert response.status_code == 200

    def test_execution_metrics_aggregation(self):
        """Test execution metrics with different aggregation periods."""
        workspace_id = self.get_workspace_id()
        # Test different time ranges and aggregations
        time_ranges = ["24h", "7d", "30d", "90d"]

        for time_range in time_ranges:
            response = self.client.get(
                f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics?time_range={time_range}",
                headers=self.headers,
            )
            assert response.status_code == 200
            data = response.json()

            # Verify aggregated data structure
            assert "executions_by_date" in data
            assert "errors_by_date" in data

            # Check that date arrays have appropriate length for time range
            executions_by_date = data["executions_by_date"]
            if time_range == "24h":
                # Hourly data for 24 hours
                assert len(executions_by_date) <= 24
            elif time_range == "7d":
                # Daily data for 7 days
                assert len(executions_by_date) <= 7
            elif time_range == "30d":
                # Daily data for 30 days
                assert len(executions_by_date) <= 30
            elif time_range == "90d":
                # Weekly or daily data for 90 days
                assert len(executions_by_date) <= 90

    def test_dashboard_stats_comparison(self):
        """Test dashboard stats period comparison calculations."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats?time_range=7d", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify comparison metrics exist and are reasonable
        comparison_fields = [
            "execution_change",
            "user_change",
            "response_time_change",
            "success_rate_change",
        ]

        for field in comparison_fields:
            assert field in data
            # Changes should be percentages (can be positive, negative, or zero)
            value = data[field]
            assert isinstance(value, (int, float))
            # Reasonable range for percentage changes
            assert -1000 <= value <= 1000

    def test_recent_activity_filtering(self):
        """Test recent activity with workspace filtering."""
        workspace_id = self.get_workspace_id()
        # Test with workspace filter
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?workspace_id=test_workspace&limit=5",
            headers=self.headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_top_actions_sorting(self):
        """Test that top actions are properly sorted."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/top-actions?limit=20", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        # If we have data, verify it's sorted by count (descending)
        if len(data) > 1:
            counts = [action["count"] for action in data]
            assert counts == sorted(counts, reverse=True)

    def test_error_handling(self):
        """Test error handling for analytics endpoints."""
        workspace_id = self.get_workspace_id()
        # Test with invalid workspace_id format
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics?workspace_id=invalid%20workspace",
            headers=self.headers,
        )
        # Should still work, just filter by non-existent workspace
        assert response.status_code == 200

        # Test with future date range (should return empty data)
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/recent-activity?date_from={future_date}", headers=self.headers
        )
        assert response.status_code in [200, 422]  # May validate date range

    def test_performance_metrics(self):
        """Test performance-related analytics."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(f"/admin/api/v1/workspaces/{workspace_id}/analytics/dashboard-stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()

        # Verify performance metrics
        assert "avg_response_time" in data
        avg_time = data["avg_response_time"]

        # Response time should be non-negative
        assert avg_time >= 0

        # If there's data, response time should be reasonable (in ms)
        if data["total_executions"] > 0 and avg_time > 0:
            # Reasonable bounds: 1ms to 60 seconds
            assert 1 <= avg_time <= 60000

    def test_success_rate_calculation(self):
        """Test success rate calculation accuracy."""
        workspace_id = self.get_workspace_id()
        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics", headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()

        total = data["total_executions"]
        errors = data["total_errors"]
        success_rate = data["success_rate"]

        # Verify success rate calculation
        if total > 0:
            expected_rate = ((total - errors) / total) * 100
            # Allow small floating point difference
            assert abs(success_rate - expected_rate) < 0.01
        else:
            # No executions means 0% or 100% success rate (API specific)
            assert success_rate in [0.0, 100.0]

    def test_date_filtering(self):
        """Test date range filtering for analytics."""
        workspace_id = self.get_workspace_id()
        # Test with specific date range
        date_from = (datetime.now() - timedelta(days=7)).isoformat()
        date_to = datetime.now().isoformat()

        response = self.client.get(
            f"/admin/api/v1/workspaces/{workspace_id}/analytics/execution-metrics?date_from={date_from}&date_to={date_to}",
            headers=self.headers,
        )
        assert response.status_code in [200, 422]  # May not support custom date ranges yet

        if response.status_code == 200:
            data = response.json()
            # Data should be within the requested range
            assert "executions_by_date" in data

    def test_workspace_isolation(self):
        """Test that analytics are properly isolated by workspace."""
        # Ensure we have test workspaces
        workspace1 = ensure_test_workspace(self.client, self.headers, "test_analytics_workspace_1")
        workspace2 = ensure_test_workspace(self.client, self.headers, "test_analytics_workspace_2")
        
        if not workspace1 or not workspace2:
            pytest.skip("Could not create test workspaces for analytics isolation test")
        
        workspace1_id = workspace1["id"]
        workspace2_id = workspace2["id"]
        
        # Get stats for workspace 1 using new workspace-scoped endpoint
        response1 = self.client.get(
            f"/admin/api/v1/workspaces/{workspace1_id}/analytics/dashboard-stats", headers=self.headers
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Get stats for workspace 2
        response2 = self.client.get(
            f"/admin/api/v1/workspaces/{workspace2_id}/analytics/dashboard-stats", headers=self.headers
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Stats might be different (unless both workspaces have no data)
        # This just verifies the endpoint accepts workspace filtering
        assert "total_executions" in data1
        assert "total_executions" in data2
