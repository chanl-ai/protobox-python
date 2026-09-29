"""GitHub OAuth2 integration for project management and issue tracking."""

from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import OAuth2Integration, IntegrationHealth, IntegrationCapability


class GitHubIntegration(OAuth2Integration):
    """GitHub OAuth2 integration implementation for project management."""

    integration_type = IntegrationType.GITHUB
    display_name = "GitHub"
    description = "Track issues, manage pull requests, and coordinate development projects"
    
    # OAuth2 configuration
    oauth_authorize_url = "https://github.com/login/oauth/authorize"
    oauth_token_url = "https://github.com/login/oauth/access_token"
    oauth_scopes = [
        "repo",           # Full control of private repositories
        "public_repo",    # Access to public repositories
        "write:org",      # Manage organization projects
        "read:user",      # Read user profile data
        "project",        # Manage projects (classic)
        "write:discussion",  # Create team discussions
        "workflow",       # Update GitHub Action workflows
    ]
    
    # Capabilities for project management
    capabilities = [
        IntegrationCapability.CREATE_PROJECT,
        IntegrationCapability.UPDATE_TASK,
        IntegrationCapability.TRACK_ACTIVITY,
        IntegrationCapability.SEND_MESSAGE,  # Via issues/PRs
    ]
    
    # Additional OAuth parameters
    extra_auth_params = {
        "allow_signup": "false"  # Don't allow new GitHub signups during OAuth
    }

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test GitHub connection by fetching authenticated user."""
        try:
            import httpx
            
            access_token = credentials.get("access_token")
            if not access_token:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing access token",
                    details={"error": "no_token"}
                )
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected as {data.get('login', 'Unknown')}",
                        details={
                            "user": data.get("login"),
                            "name": data.get("name"),
                            "email": data.get("email"),
                            "public_repos": data.get("public_repos"),
                            "private_repos": data.get("total_private_repos", 0),
                            "plan": data.get("plan", {}).get("name", "free")
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid or expired token",
                        details={"error": "invalid_token", "status": 401}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"GitHub API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing GitHub connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def get_capabilities(self) -> list[str]:
        """Get GitHub integration capabilities."""
        return [
            "create_issue",
            "update_issue",
            "create_pull_request",
            "review_pull_request",
            "create_project",
            "manage_milestones",
            "create_release",
            "manage_workflows",
            "track_commits",
            "manage_branches",
            "webhook_events"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for GitHub integration."""
        return {
            "type": "object",
            "properties": {
                "default_repo": {
                    "type": "string",
                    "title": "Default Repository",
                    "description": "Default repository for operations (owner/repo format)",
                    "pattern": "^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$",
                    "examples": ["octocat/hello-world"]
                },
                "organization": {
                    "type": "string",
                    "title": "Organization",
                    "description": "GitHub organization name (if applicable)",
                    "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-]*$"
                },
                "auto_assign": {
                    "type": "array",
                    "title": "Auto-Assign Users",
                    "description": "Automatically assign these users to new issues",
                    "items": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9][a-zA-Z0-9-]*$"
                    }
                },
                "labels": {
                    "type": "object",
                    "title": "Label Mapping",
                    "description": "Map ProtoBox categories to GitHub labels",
                    "properties": {
                        "bug": {"type": "string", "default": "bug"},
                        "feature": {"type": "string", "default": "enhancement"},
                        "task": {"type": "string", "default": "task"},
                        "urgent": {"type": "string", "default": "priority:high"}
                    }
                },
                "project_board": {
                    "type": "string",
                    "title": "Project Board",
                    "description": "Default project board for issue tracking",
                    "examples": ["Development", "Sprint Planning"]
                },
                "webhook_events": {
                    "type": "array",
                    "title": "Webhook Events",
                    "description": "GitHub events to listen for",
                    "items": {
                        "type": "string",
                        "enum": [
                            "issues",
                            "pull_request",
                            "push",
                            "release",
                            "milestone",
                            "project",
                            "deployment",
                            "workflow_run"
                        ]
                    },
                    "default": ["issues", "pull_request", "push"]
                },
                "branch_protection": {
                    "type": "boolean",
                    "title": "Enable Branch Protection",
                    "description": "Automatically set up branch protection rules",
                    "default": False
                }
            },
            "required": []
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for GitHub integration."""
        return [
            {
                "name": "github_create_issue",
                "description": "Create a new issue for task tracking",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue description"},
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "assignees": {"type": "array", "items": {"type": "string"}},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "milestone": {"type": "integer", "description": "Milestone number"}
                    },
                    "required": ["title", "body"]
                }
            },
            {
                "name": "github_update_issue",
                "description": "Update an existing issue status or details",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "issue_number": {"type": "integer"},
                        "state": {"type": "string", "enum": ["open", "closed"]},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "assignees": {"type": "array", "items": {"type": "string"}},
                        "labels": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["issue_number"]
                }
            },
            {
                "name": "github_create_pr",
                "description": "Create a pull request for code review",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "head": {"type": "string", "description": "Branch with changes"},
                        "base": {"type": "string", "description": "Target branch", "default": "main"},
                        "draft": {"type": "boolean", "default": False},
                        "reviewers": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["title", "head", "base"]
                }
            },
            {
                "name": "github_list_issues",
                "description": "List and search repository issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"]},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "assignee": {"type": "string"},
                        "milestone": {"type": "integer"},
                        "sort": {"type": "string", "enum": ["created", "updated", "comments"]},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100}
                    }
                }
            },
            {
                "name": "github_create_milestone",
                "description": "Create a project milestone for sprint planning",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "due_on": {"type": "string", "format": "date-time"},
                        "state": {"type": "string", "enum": ["open", "closed"]}
                    },
                    "required": ["title"]
                }
            },
            {
                "name": "github_project_metrics",
                "description": "Get project metrics and burndown data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
                        "milestone": {"type": "integer"},
                        "date_from": {"type": "string", "format": "date"},
                        "date_to": {"type": "string", "format": "date"},
                        "metrics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["velocity", "burndown", "cycle_time", "pr_stats"]
                            }
                        }
                    }
                }
            }
        ]