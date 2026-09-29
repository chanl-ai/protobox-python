"""GitHub OAuth2 provider implementation."""

import logging
from typing import Any

from ...models.integration import IntegrationType
from ..base import BaseOAuth2Provider

logger = logging.getLogger(__name__)


class GitHubOAuth2Provider(BaseOAuth2Provider):
    """GitHub OAuth2 provider for repository and project management."""

    @property
    def integration_type(self) -> IntegrationType:
        """Return the integration type."""
        return IntegrationType.GITHUB

    @property
    def display_name(self) -> str:
        """Return the display name."""
        return "GitHub"

    @property
    def supported_features(self) -> list[str]:
        """Return supported features."""
        return [
            "repository_access",
            "issue_management",
            "pull_requests",
            "workflow_triggers",
            "code_scanning",
            "gists",
            "webhooks",
            "project_boards",
        ]

    def get_provider_params(self) -> dict[str, str]:
        """Get GitHub-specific authorization parameters."""
        return {
            "allow_signup": "false",  # Don't allow signup during OAuth
        }

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get authenticated user information."""
        try:
            response = await self.http_client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to get user info: {response.text}")
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {}

    async def list_repositories(
        self,
        access_token: str,
        visibility: str = "all",
        sort: str = "updated",
    ) -> list[dict]:
        """List user's repositories."""
        try:
            response = await self.http_client.get(
                "https://api.github.com/user/repos",
                params={
                    "visibility": visibility,
                    "sort": sort,
                    "per_page": 100,
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Failed to list repositories: {response.text}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            return []

    async def create_issue(
        self,
        access_token: str,
        owner: str,
        repo: str,
        issue_data: dict,
    ) -> dict | None:
        """Create an issue in a repository."""
        try:
            response = await self.http_client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                },
                json=issue_data,
            )
            
            if response.status_code == 201:
                return response.json()
            
            logger.error(f"Failed to create issue: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return None

    async def create_pull_request(
        self,
        access_token: str,
        owner: str,
        repo: str,
        pr_data: dict,
    ) -> dict | None:
        """Create a pull request."""
        try:
            response = await self.http_client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                },
                json=pr_data,
            )
            
            if response.status_code == 201:
                return response.json()
            
            logger.error(f"Failed to create PR: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return None

    async def trigger_workflow(
        self,
        access_token: str,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: dict | None = None,
    ) -> bool:
        """Trigger a GitHub Actions workflow."""
        try:
            payload = {"ref": ref}
            if inputs:
                payload["inputs"] = inputs
            
            response = await self.http_client.post(
                f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            
            return response.status_code == 204
            
        except Exception as e:
            logger.error(f"Error triggering workflow: {e}")
            return False

    async def create_webhook(
        self,
        access_token: str,
        owner: str,
        repo: str,
        webhook_config: dict,
    ) -> dict | None:
        """Create a webhook for repository events."""
        try:
            response = await self.http_client.post(
                f"https://api.github.com/repos/{owner}/{repo}/hooks",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                },
                json=webhook_config,
            )
            
            if response.status_code == 201:
                return response.json()
            
            logger.error(f"Failed to create webhook: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            return None