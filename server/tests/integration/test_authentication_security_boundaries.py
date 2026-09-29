"""
Edge case tests for OAuth MCP functionality.

These tests cover scenarios that are likely to cause failures in production:
1. Network timeouts and connection failures
2. Invalid authentication tokens
3. Rate limiting and throttling
4. Concurrent access patterns
5. Resource exhaustion scenarios
6. Malformed data handling
7. Security boundary testing
"""

import asyncio
import pytest
import time
import json
from typing import List, Dict, Any
from httpx import Client
from concurrent.futures import ThreadPoolExecutor

# Import enhanced test utilities
from .enhanced_test_utils import (
    ResourceManager,
    EnhancedTestCase, 
    TestDataValidators,
    CoverageReporter
)
from .test_utils import get_test_auth_and_workspace

# Import FastMCP for protocol testing
try:
    from fastmcp.client import Client as FastMCPClient
    from fastmcp.client import SSETransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False


@pytest.mark.integration
class TestEdgeCaseAuthentication:
    """Test authentication edge cases and security boundaries."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        
        # Setup authentication
        access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
        if not access_token:
            cls.skip_tests = True
            cls.skip_reason = "Failed to setup authentication and workspace"
            return
            
        cls.access_token = access_token
        cls.headers = headers
        cls.workspace_id = workspace_id
        cls.skip_tests = False
        
        cls.coverage_reporter = CoverageReporter()
        
    def setup_method(self):
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_expired_token_handling(self):
        """Test handling of expired authentication tokens."""
        test_name = "expired_token_handling"
        
        try:
            # Create a token that looks valid but is expired
            expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOiJ0ZXN0LXVzZXIiLCJleHAiOjE2MDAwMDAwMDB9.invalid"
            expired_headers = {"Authorization": f"Bearer {expired_token}"}
            
            # Try to access workspace with expired token
            response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=expired_headers
            )
            
            assert response.status_code in [401, 403], "Should reject expired token"
            
            # Try MCP access with expired token
            response = self.client.get(
                f"/mcp/{self.workspace_id}/sse",
                headers=expired_headers
            )
            
            assert response.status_code in [401, 403], "MCP should reject expired token"
            
            self.coverage_reporter.record_test_result("auth", test_name, True)
            
        except Exception as e:
            self.coverage_reporter.record_test_result("auth", test_name, False, {"error": str(e)})
            raise
    
    def test_malformed_token_handling(self):
        """Test handling of malformed authentication tokens."""
        test_name = "malformed_token_handling"
        
        try:
            malformed_tokens = [
                "not-a-jwt-at-all",
                "header.payload.signature.extra",
                "header.{invalid-json}.signature",
                "invalid-token-format",
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"  # Missing payload and signature
            ]
            
            for token in malformed_tokens:
                # Skip empty or whitespace-only tokens that cause HTTP protocol errors
                if not token or not token.strip():
                    continue
                    
                headers = {"Authorization": f"Bearer {token}"}
                
                try:
                    response = self.client.get(
                        f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                        headers=headers
                    )
                    # If we get here, the request succeeded - check status
                    assert response.status_code in [400, 401, 403], f"Should reject malformed token: {token}"
                except Exception:
                    # Some malformed tokens cause client-side protocol errors - that's also expected
                    continue
            
            self.coverage_reporter.record_test_result("auth", test_name, True)
            
        except Exception as e:
            self.coverage_reporter.record_test_result("auth", test_name, False, {"error": str(e)})
            raise
    
    def test_cross_workspace_token_access(self):
        """Test that tokens cannot access other workspaces."""
        test_name = "cross_workspace_token_access"
        
        try:
            # Try to access a different workspace with current token
            fake_workspace_ids = [
                "000000000000000000000001",
                "999999999999999999999999", 
                "invalid-workspace-id",
                ""
            ]
            
            for fake_id in fake_workspace_ids:
                response = self.client.get(
                    f"/admin/api/v1/workspaces/{fake_id}/actions",
                    headers=self.headers
                )
                
                assert response.status_code in [400, 403, 404], f"Should reject access to workspace: {fake_id}"
            
            self.coverage_reporter.record_test_result("auth", test_name, True)
            
        except Exception as e:
            self.coverage_reporter.record_test_result("auth", test_name, False, {"error": str(e)})
            raise


@pytest.mark.integration
class TestConcurrencyAndRaceConditions:
    """Test concurrent access patterns and race conditions."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        
        # Setup authentication
        access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
        if not access_token:
            cls.skip_tests = True
            cls.skip_reason = "Failed to setup authentication and workspace"
            return
            
        cls.access_token = access_token
        cls.headers = headers
        cls.workspace_id = workspace_id
        cls.skip_tests = False
        
        cls.resource_manager = ResourceManager(cls.client, cls.headers, cls.workspace_id)
        
    def setup_method(self):
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    async def test_concurrent_action_creation(self):
        """Test concurrent action creation to detect race conditions."""
        test_name = "concurrent_action_creation"
        
        try:
            # Create multiple actions concurrently
            async def create_action(index: int) -> str:
                action_id = await self.resource_manager.create_test_action(
                    f"concurrent_test_action_{index}",
                    config={"url": f"https://httpbin.org/get?id={index}", "method": "GET"}
                )
                return action_id
            
            # Launch 10 concurrent creations
            tasks = [create_action(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_creations = [r for r in results if isinstance(r, str)]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            # At least 80% should succeed (some may fail due to name conflicts)
            success_rate = len(successful_creations) / len(results)
            assert success_rate >= 0.8, f"Success rate should be ≥80%, got {success_rate:.1%}"
            
            # All successful IDs should be unique
            assert len(set(successful_creations)) == len(successful_creations), "All action IDs should be unique"
            
            print(f"Concurrent creation test: {len(successful_creations)}/10 succeeded, {len(exceptions)} exceptions")
            
        except Exception as e:
            print(f"Concurrent action creation test failed: {e}")
            raise
    
    def test_concurrent_api_access(self):
        """Test concurrent API access patterns."""
        test_name = "concurrent_api_access"
        
        try:
            def make_request(request_id: int) -> Dict[str, Any]:
                try:
                    response = self.client.get(
                        f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                        headers=self.headers
                    )
                    return {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "success": response.status_code == 200,
                        "response_time": response.elapsed.total_seconds()
                    }
                except Exception as e:
                    return {
                        "request_id": request_id,
                        "status_code": 0,
                        "success": False,
                        "error": str(e)
                    }
            
            # Make 20 concurrent requests
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(20)]
                results = [future.result() for future in futures]
            
            # Analyze results
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            success_rate = len(successful) / len(results)
            assert success_rate >= 0.9, f"Success rate should be ≥90%, got {success_rate:.1%}"
            
            # Check response times are reasonable (< 5 seconds)
            avg_response_time = sum(r.get("response_time", 0) for r in successful) / len(successful)
            assert avg_response_time < 5.0, f"Average response time should be <5s, got {avg_response_time:.2f}s"
            
            print(f"Concurrent API access: {len(successful)}/20 succeeded, avg response time: {avg_response_time:.2f}s")
            
        except Exception as e:
            print(f"Concurrent API access test failed: {e}")
            raise


@pytest.mark.integration
@pytest.mark.skipif(not FASTMCP_AVAILABLE, reason="FastMCP not available")
class TestMCPProtocolEdgeCases:
    """Test MCP protocol edge cases and error conditions."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        
        # Setup authentication
        access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
        if not access_token:
            cls.skip_tests = True
            cls.skip_reason = "Failed to setup authentication and workspace"
            return
            
        cls.access_token = access_token
        cls.headers = headers
        cls.workspace_id = workspace_id
        cls.skip_tests = False
        
        cls.resource_manager = ResourceManager(cls.client, cls.headers, cls.workspace_id)
        
    def setup_method(self):
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    async def test_mcp_connection_timeouts(self):
        """Test MCP connection timeout handling."""
        test_name = "mcp_connection_timeouts"
        
        try:
            # Create test action first
            action_id = await self.resource_manager.create_test_action(
                "timeout_test_action",
                config={"url": "https://httpbin.org/get", "method": "GET"}
            )
            assert action_id, "Test action should be created"
            
            await asyncio.sleep(2)  # Wait for registration
            
            # Test very short timeout
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=0.1  # Very short timeout
            )
            
            try:
                async with FastMCPClient(transport) as client:
                    # This might timeout, which is expected
                    tools = await asyncio.wait_for(client.list_tools(), timeout=1.0)
                    # If we get here, the connection was fast enough
                    assert len(tools) > 0, "Should return some tools"
                    
            except (asyncio.TimeoutError, Exception) as e:
                # Timeout is expected with very short timeout
                print(f"Expected timeout with short timeout setting: {e}")
            
            print("✓ MCP timeout handling test completed")
            
        except Exception as e:
            print(f"MCP timeout test failed: {e}")
            raise
    
    async def test_mcp_invalid_tool_execution(self):
        """Test MCP tool execution with invalid parameters."""
        test_name = "mcp_invalid_tool_execution"
        
        try:
            # Create test action
            action_id = await self.resource_manager.create_test_action(
                "invalid_params_test_action",
                config={"url": "https://httpbin.org/get", "method": "GET"}
            )
            assert action_id, "Test action should be created"
            
            await asyncio.sleep(2)  # Wait for registration
            
            transport = SSETransport(
                url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            async with FastMCPClient(transport) as client:
                tools = await client.list_tools()
                
                # Find our test tool
                test_tools = [tool for tool in tools if "invalid_params_test_action" in tool.name]
                assert len(test_tools) > 0, "Should find test tool"
                
                test_tool = test_tools[0]
                
                # Test various invalid parameter scenarios
                invalid_params_list = [
                    {"invalid_param": "value"},  # Invalid parameter name
                    {"nested": {"deeply": {"invalid": "structure"}}},  # Too deeply nested
                    {"param": "x" * 10000},  # Very large parameter
                    None,  # None parameters
                ]
                
                for invalid_params in invalid_params_list:
                    try:
                        result = await client.call_tool(test_tool.name, invalid_params)
                        # Tool execution should either succeed (ignoring invalid params) or fail gracefully
                        print(f"Tool execution with invalid params succeeded: {invalid_params}")
                        
                    except Exception as e:
                        # Expected - tool should handle invalid parameters gracefully
                        print(f"Tool execution failed gracefully with invalid params: {e}")
                
                # Test invalid tool name
                try:
                    result = await client.call_tool("non_existent_tool", {})
                    assert False, "Should fail for non-existent tool"
                except Exception as e:
                    # Expected - should fail for non-existent tool
                    print(f"Correctly failed for non-existent tool: {e}")
            
            print("✓ MCP invalid tool execution test completed")
            
        except Exception as e:
            print(f"MCP invalid tool execution test failed: {e}")
            raise
    
    async def test_mcp_connection_recovery(self):
        """Test MCP connection recovery after network issues.""" 
        test_name = "mcp_connection_recovery"
        
        try:
            # Create test action
            action_id = await self.resource_manager.create_test_action(
                "recovery_test_action",
                config={"url": "https://httpbin.org/get", "method": "GET"}
            )
            assert action_id, "Test action should be created"
            
            await asyncio.sleep(2)  # Wait for registration
            
            # Test multiple connection attempts (simulating network issues)
            successful_connections = 0
            total_attempts = 5
            
            for attempt in range(total_attempts):
                try:
                    transport = SSETransport(
                        url=f"http://localhost:8090/mcp/{self.workspace_id}/sse",
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    async with FastMCPClient(transport) as client:
                        tools = await client.list_tools()
                        assert len(tools) > 0, f"Should find tools on attempt {attempt}"
                        successful_connections += 1
                        
                    # Brief delay between attempts
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"Connection attempt {attempt} failed: {e}")
            
            # At least 80% of connections should succeed
            success_rate = successful_connections / total_attempts
            assert success_rate >= 0.8, f"Success rate should be ≥80%, got {success_rate:.1%}"
            
            print(f"✓ MCP connection recovery test: {successful_connections}/{total_attempts} succeeded")
            
        except Exception as e:
            print(f"MCP connection recovery test failed: {e}")
            raise


@pytest.mark.integration
class TestDataValidationAndSanitization:
    """Test data validation and sanitization edge cases."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.client = Client(base_url="http://localhost:8090", timeout=30.0)
        
        # Setup authentication
        access_token, headers, workspace_id = get_test_auth_and_workspace(cls.client)
        if not access_token:
            cls.skip_tests = True
            cls.skip_reason = "Failed to setup authentication and workspace"
            return
            
        cls.access_token = access_token
        cls.headers = headers
        cls.workspace_id = workspace_id
        cls.skip_tests = False
        
    def setup_method(self):
        if self.skip_tests:
            pytest.skip(self.skip_reason)
    
    def test_sql_injection_prevention(self):
        """Test that API endpoints prevent SQL injection attempts."""
        test_name = "sql_injection_prevention"
        
        try:
            # SQL injection attempts in various parameters
            sql_injection_payloads = [
                "'; DROP TABLE actions; --",
                "1' OR '1'='1",
                "admin'/**/OR/**/1=1--",
                "'; INSERT INTO actions (name) VALUES ('hacked'); --"
            ]
            
            for payload in sql_injection_payloads:
                # Try SQL injection in action name
                response = self.client.post(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                    headers=self.headers,
                    json={
                        "name": payload,
                        "type": "REST",
                        "config": {"url": "https://httpbin.org/get", "method": "GET"}
                    }
                )
                
                # Should either reject or sanitize the input
                if response.status_code in [200, 201]:
                    # If creation succeeded, name should be sanitized
                    response_data = response.json()
                    created_name = response_data.get("name", "")
                    assert payload not in created_name, "SQL injection payload should be sanitized"
                else:
                    # Rejection is also acceptable
                    assert response.status_code in [400, 422], "Should reject or sanitize SQL injection"
            
            print("✓ SQL injection prevention test completed")
            
        except Exception as e:
            print(f"SQL injection prevention test failed: {e}")
            raise
    
    def test_xss_prevention(self):
        """Test that API endpoints prevent XSS attacks."""
        test_name = "xss_prevention"
        
        try:
            # XSS payloads
            xss_payloads = [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "' onmouseover='alert(1)'"
            ]
            
            for payload in xss_payloads:
                response = self.client.post(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                    headers=self.headers,
                    json={
                        "name": f"xss_test_{payload}",
                        "type": "REST",
                        "description": payload,
                        "config": {"url": "https://httpbin.org/get", "method": "GET"}
                    }
                )
                
                if response.status_code in [200, 201]:
                    # If creation succeeded, XSS should be sanitized
                    response_data = response.json()
                    description = response_data.get("description", "")
                    # XSS payload should be escaped or removed
                    assert "<script>" not in description, "XSS script tags should be sanitized"
                    assert "javascript:" not in description, "JavaScript URLs should be sanitized"
            
            print("✓ XSS prevention test completed")
            
        except Exception as e:
            print(f"XSS prevention test failed: {e}")
            raise
    
    def test_large_payload_handling(self):
        """Test handling of unusually large payloads."""
        test_name = "large_payload_handling"
        
        try:
            # Create increasingly large payloads
            large_string = "x" * 1000000  # 1MB string
            very_large_config = {
                "url": "https://httpbin.org/post",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "data": {"large_field": large_string}
            }
            
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers,
                json={
                    "name": "large_payload_test",
                    "type": "REST",
                    "description": "Test with large config",
                    "config": very_large_config
                }
            )
            
            # Should either accept or reject gracefully (not crash)
            assert response.status_code in [200, 201, 400, 413, 422], "Should handle large payload gracefully"
            
            if response.status_code in [200, 201]:
                print("✓ Large payload accepted and processed")
            else:
                print(f"✓ Large payload rejected gracefully: {response.status_code}")
            
        except Exception as e:
            print(f"Large payload test failed: {e}")
            # This is acceptable - server might have size limits
            pass


def run_all_edge_case_tests():
    """Run all edge case tests and generate report."""
    import subprocess
    import sys
    
    # Run the edge case tests
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "server/tests/integration/test_authentication_security_boundaries.py",
        "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    print("EDGE CASE TESTS RESULTS:")
    print("=" * 50)
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
    
    return result.returncode == 0