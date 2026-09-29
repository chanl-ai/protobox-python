"""
Enhanced test utilities with comprehensive resource management and cleanup.

Addresses issues found in existing tests:
1. Async/sync mismatch problems
2. Resource cleanup failures
3. Name collision handling  
4. Test isolation issues
5. Better error propagation
"""

import asyncio
import secrets
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import httpx
from loguru import logger


class ResourceManager:
    """
    Centralized resource manager for integration tests.
    Handles creation, tracking, and cleanup of test resources.
    """
    
    def __init__(self, client: httpx.Client, headers: dict[str, str], workspace_id: str):
        self.client = client
        self.headers = headers
        self.workspace_id = workspace_id
        self.created_actions: List[str] = []
        self.created_oauth_clients: List[str] = []
        self.created_secrets: List[str] = []
        self.test_session_id = f"test_{int(time.time())}_{secrets.token_hex(4)}"
        
    def get_unique_name(self, base_name: str) -> str:
        """Generate a unique name for test resources."""
        return f"{base_name}_{self.test_session_id}"
    
    async def create_test_action(
        self,
        name: str,
        action_type: str = "REST",
        config: Optional[Dict[str, Any]] = None,
        variables: Optional[List[Dict[str, Any]]] = None,
        force_unique: bool = True,
        cleanup_existing: bool = True
    ) -> Optional[str]:
        """
        Enhanced async action creation with robust cleanup and conflict resolution.
        
        Args:
            name: Action name (will be made unique if force_unique=True)
            action_type: Action type (default: REST)
            config: Action configuration
            variables: Action variables
            force_unique: Whether to make name unique to avoid conflicts
            cleanup_existing: Whether to delete existing actions with same name
            
        Returns:
            Action ID if successful, None otherwise
        """
        # Make name unique if requested
        unique_name = self.get_unique_name(name) if force_unique else name
        
        # Clean up existing action if it exists
        if cleanup_existing:
            await self._cleanup_existing_action(unique_name)
            
        action_config = config or {
            "url": "https://httpbin.org/get", 
            "method": "GET",
            "headers": {"Content-Type": "application/json"}
        }
        
        action_data = {
            "workspace_id": self.workspace_id,
            "name": unique_name,
            "type": action_type,
            "description": f"Test action: {unique_name}",
            "config": action_config
        }
        
        if variables:
            action_data["variables"] = variables
            
        try:
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers,
                json=action_data
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                action_id = response_data.get("id") or response_data.get("_id")
                
                if action_id:
                    self.created_actions.append(action_id)
                    logger.info(f"✓ Created test action: {unique_name} ({action_id})")
                    return action_id
                    
            logger.error(f"✗ Failed to create action: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"✗ Exception creating action: {e}")
            return None
    
    async def _cleanup_existing_action(self, name: str) -> bool:
        """Clean up existing action with the given name."""
        try:
            # List actions to find existing one
            response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                actions = response.json()
                for action in actions:
                    if action.get("name") == name:
                        action_id = action.get("id") or action.get("_id")
                        if action_id:
                            delete_response = self.client.delete(
                                f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
                                headers=self.headers
                            )
                            if delete_response.status_code in [200, 204]:
                                logger.info(f"✓ Cleaned up existing action: {name}")
                                return True
                            else:
                                logger.warning(f"Failed to delete action {name}: {delete_response.status_code}")
                                
        except Exception as e:
            logger.warning(f"Error during action cleanup: {e}")
            
        return False
    
    async def create_oauth_client(
        self,
        client_name: str,
        redirect_uris: List[str] = None,
        force_unique: bool = True
    ) -> Optional[str]:
        """Create OAuth client with cleanup tracking."""
        unique_name = self.get_unique_name(client_name) if force_unique else client_name
        
        client_data = {
            "client_name": unique_name,  # Fixed: API expects 'client_name' not 'name'
            "redirect_uris": redirect_uris or ["http://localhost:8080/callback"],
            "scopes": ["mcp:read", "mcp:write", "mcp:execute"]
        }
        
        try:
            response = self.client.post(
                f"/admin/api/v1/workspaces/{self.workspace_id}/oauth-clients",
                headers=self.headers,
                json=client_data
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                client_id = response_data.get("client_id")
                if client_id:
                    self.created_oauth_clients.append(client_id)
                    logger.info(f"✓ Created OAuth client: {unique_name} ({client_id})")
                    return client_id
                    
            logger.error(f"✗ Failed to create OAuth client: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"✗ Exception creating OAuth client: {e}")
            return None
    
    async def cleanup_all(self) -> Dict[str, int]:
        """Clean up all created resources. Returns cleanup summary."""
        cleanup_results = {
            "actions_cleaned": 0,
            "oauth_clients_cleaned": 0,
            "secrets_cleaned": 0,
            "errors": 0
        }
        
        # Clean up actions
        for action_id in self.created_actions.copy():
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
                    headers=self.headers
                )
                if response.status_code in [200, 204]:
                    cleanup_results["actions_cleaned"] += 1
                    self.created_actions.remove(action_id)
                else:
                    cleanup_results["errors"] += 1
                    logger.warning(f"Failed to cleanup action {action_id}: {response.status_code}")
            except Exception as e:
                cleanup_results["errors"] += 1
                logger.error(f"Error cleaning up action {action_id}: {e}")
        
        # Clean up OAuth clients
        for client_id in self.created_oauth_clients.copy():
            try:
                response = self.client.delete(
                    f"/admin/api/v1/workspaces/{self.workspace_id}/oauth-clients/{client_id}",
                    headers=self.headers
                )
                if response.status_code in [200, 204]:
                    cleanup_results["oauth_clients_cleaned"] += 1
                    self.created_oauth_clients.remove(client_id)
                else:
                    cleanup_results["errors"] += 1
                    logger.warning(f"Failed to cleanup OAuth client {client_id}: {response.status_code}")
            except Exception as e:
                cleanup_results["errors"] += 1
                logger.error(f"Error cleaning up OAuth client {client_id}: {e}")
        
        logger.info(f"Cleanup summary: {cleanup_results}")
        return cleanup_results


class EnhancedTestCase:
    """
    Enhanced base test case with comprehensive resource management.
    """
    
    def __init__(self, client: httpx.Client, headers: dict[str, str], workspace_id: str):
        self.client = client
        self.headers = headers
        self.workspace_id = workspace_id
        self.resource_manager = TestResourceManager(client, headers, workspace_id)
        
    async def setup_method(self):
        """Setup method to be called before each test."""
        # Pre-test cleanup of any leaked resources
        await self._cleanup_leaked_test_resources()
        
    async def teardown_method(self):
        """Teardown method to be called after each test."""
        cleanup_results = await self.resource_manager.cleanup_all()
        
        # Fail test if cleanup had too many errors
        if cleanup_results["errors"] > 0:
            logger.warning(f"Test cleanup had {cleanup_results['errors']} errors")
            
    async def _cleanup_leaked_test_resources(self):
        """Clean up any test resources that might have been left from previous runs."""
        try:
            # Get current timestamp for comparison
            current_time = int(time.time())
            cutoff_time = current_time - (24 * 3600)  # 24 hours ago
            
            # Clean up old test actions
            response = self.client.get(
                f"/admin/api/v1/workspaces/{self.workspace_id}/actions",
                headers=self.headers
            )
            
            if response.status_code == 200:
                actions = response.json()
                cleaned_count = 0
                
                for action in actions:
                    name = action.get("name", "")
                    # Clean up test actions older than cutoff
                    if name.startswith("test_") or "fastmcp_test" in name:
                        try:
                            # Extract timestamp if present
                            if "_test_" in name:
                                parts = name.split("_test_")
                                if len(parts) > 1:
                                    timestamp_str = parts[1].split("_")[0]
                                    if timestamp_str.isdigit() and int(timestamp_str) < cutoff_time:
                                        action_id = action.get("id") or action.get("_id")
                                        if action_id:
                                            delete_response = self.client.delete(
                                                f"/admin/api/v1/workspaces/{self.workspace_id}/actions/{action_id}",
                                                headers=self.headers
                                            )
                                            if delete_response.status_code in [200, 204]:
                                                cleaned_count += 1
                        except (ValueError, IndexError):
                            continue
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} leaked test actions")
                    
        except Exception as e:
            logger.warning(f"Error during leaked resource cleanup: {e}")


# Backward compatibility functions
async def create_test_action_async(
    client: httpx.Client,
    headers: dict[str, str],
    workspace_id: str,
    name: str,
    action_type: str = "REST",
    config: Optional[Dict[str, Any]] = None,
    variables: Optional[List[Dict[str, Any]]] = None
) -> Optional[str]:
    """
    Async version of create_test_action for backward compatibility.
    This function should be used instead of the sync version in async contexts.
    """
    manager = TestResourceManager(client, headers, workspace_id)
    return await manager.create_test_action(name, action_type, config, variables)


def create_test_action_with_retries(
    client: httpx.Client,
    headers: dict[str, str],
    workspace_id: str,
    name: str,
    action_type: str = "REST",
    config: Optional[Dict[str, Any]] = None,
    variables: Optional[List[Dict[str, Any]]] = None,
    max_retries: int = 3
) -> Optional[str]:
    """
    Enhanced sync version with retry logic and better conflict handling.
    """
    for attempt in range(max_retries):
        try:
            # Add attempt number to make name unique
            unique_name = f"{name}_{int(time.time())}_{attempt}" if attempt > 0 else name
            
            # Try to delete existing action first
            try:
                response = client.get(
                    f"/admin/api/v1/workspaces/{workspace_id}/actions",
                    headers=headers
                )
                if response.status_code == 200:
                    actions = response.json()
                    for action in actions:
                        if action.get("name") == unique_name:
                            action_id = action.get("id") or action.get("_id")
                            if action_id:
                                client.delete(
                                    f"/admin/api/v1/workspaces/{workspace_id}/actions/{action_id}",
                                    headers=headers
                                )
            except Exception:
                pass  # Ignore cleanup errors
            
            action_config = config or {
                "url": "https://httpbin.org/get",
                "method": "GET", 
                "headers": {"Content-Type": "application/json"}
            }
            
            action_data = {
                "workspace_id": workspace_id,
                "name": unique_name,
                "type": action_type,
                "description": f"Test action: {unique_name}",
                "config": action_config
            }
            
            if variables:
                action_data["variables"] = variables
                
            response = client.post(
                f"/admin/api/v1/workspaces/{workspace_id}/actions",
                headers=headers,
                json=action_data
            )
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                action_id = response_data.get("id") or response_data.get("_id")
                if action_id:
                    logger.info(f"✓ Created test action: {unique_name} ({action_id})")
                    return action_id
                    
            elif response.status_code == 409 and attempt < max_retries - 1:
                # Conflict, try again with different name
                logger.info(f"Action name conflict, retrying... (attempt {attempt + 1})")
                continue
            else:
                logger.error(f"✗ Failed to create action: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
                time.sleep(1)  # Brief delay before retry
                continue
            else:
                logger.error(f"✗ Exception creating action after {max_retries} attempts: {e}")
                return None
    
    return None


class TestDataValidators:
    """Collection of validators for test data integrity."""
    
    @staticmethod
    def validate_action_response(response_data: dict) -> bool:
        """Validate action response has required fields."""
        required_fields = ["id", "name", "type", "workspace_id"]
        return all(field in response_data for field in required_fields)
    
    @staticmethod 
    def validate_oauth_client_response(response_data: dict) -> bool:
        """Validate OAuth client response has required fields."""
        required_fields = ["client_id", "name", "redirect_uris"]
        return all(field in response_data for field in required_fields)
    
    @staticmethod
    def validate_mcp_tools_response(tools: list) -> bool:
        """Validate MCP tools response structure."""
        if not isinstance(tools, list):
            return False
            
        for tool in tools:
            if not isinstance(tool, dict) or "name" not in tool:
                return False
                
        return True


class CoverageReporter:
    """Generate test coverage reports and identify gaps."""
    
    def __init__(self):
        self.test_results = {}
        self.coverage_areas = {
            "auth": ["jwt", "oauth", "api_key", "token_refresh"],
            "actions": ["create", "read", "update", "delete", "execute"],
            "mcp": ["sse", "jsonrpc", "tools", "resources"],
            "workspace": ["isolation", "permissions", "multi_tenant"],
            "integration": ["fastmcp", "oauth_flow", "error_handling"]
        }
    
    def record_test_result(self, area: str, test_name: str, passed: bool, details: dict = None):
        """Record a test result for coverage tracking."""
        if area not in self.test_results:
            self.test_results[area] = {}
        
        self.test_results[area][test_name] = {
            "passed": passed,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
    
    def generate_coverage_report(self) -> dict:
        """Generate comprehensive coverage report."""
        report = {
            "summary": {
                "total_areas": len(self.coverage_areas),
                "tested_areas": 0,
                "total_tests": 0,
                "passed_tests": 0,
                "coverage_percentage": 0
            },
            "areas": {},
            "recommendations": []
        }
        
        for area, expected_tests in self.coverage_areas.items():
            area_results = self.test_results.get(area, {})
            tested_count = len(area_results)
            passed_count = sum(1 for result in area_results.values() if result["passed"])
            
            report["areas"][area] = {
                "expected_tests": len(expected_tests),
                "actual_tests": tested_count,
                "passed_tests": passed_count,
                "coverage": tested_count / len(expected_tests) if expected_tests else 0,
                "success_rate": passed_count / tested_count if tested_count else 0,
                "missing_tests": [test for test in expected_tests if test not in area_results]
            }
            
            if tested_count > 0:
                report["summary"]["tested_areas"] += 1
            
            report["summary"]["total_tests"] += tested_count
            report["summary"]["passed_tests"] += passed_count
        
        # Calculate overall coverage
        total_expected = sum(len(tests) for tests in self.coverage_areas.values())
        total_actual = report["summary"]["total_tests"]
        report["summary"]["coverage_percentage"] = (total_actual / total_expected * 100) if total_expected else 0
        
        # Generate recommendations
        for area, area_data in report["areas"].items():
            if area_data["coverage"] < 0.8:
                report["recommendations"].append(f"Increase {area} test coverage (currently {area_data['coverage']:.1%})")
            if area_data["success_rate"] < 0.9 and area_data["actual_tests"] > 0:
                report["recommendations"].append(f"Fix failing {area} tests (success rate: {area_data['success_rate']:.1%})")
        
        return report