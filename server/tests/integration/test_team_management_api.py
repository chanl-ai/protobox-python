"""Integration tests for team management API endpoints."""


import httpx
import pytest


@pytest.mark.integration
class TestTeamManagementAPI:
    """Test suite for team management API endpoints."""

    @classmethod
    def setup_class(cls):
        """Set up test class with HTTP client and authentication."""
        cls.client = httpx.Client(base_url="http://localhost:8090", timeout=10.0)
        cls.skip_tests = False
        cls.skip_reason = None

        # Try to get test tokens
        try:
            # Get admin token (owner)
            admin_response = cls.client.post(
                "/admin/api/v1/auth/exchange",
                json={"firebase_token": "test-admin-user"}
            )

            # Get member token
            member_response = cls.client.post(
                "/admin/api/v1/auth/exchange",
                json={"firebase_token": "test-member-user"}
            )

            if admin_response.status_code == 200 and member_response.status_code == 200:
                cls.admin_token = admin_response.json()["access_token"]
                cls.member_token = member_response.json()["access_token"]
                cls.admin_headers = {"Authorization": f"Bearer {cls.admin_token}"}
                cls.member_headers = {"Authorization": f"Bearer {cls.member_token}"}

                # Create a test workspace for team operations
                workspace_response = cls.client.post(
                    "/admin/api/v1/workspaces",
                    headers=cls.admin_headers,
                    json={
                        "name": "Test Team Workspace",
                        "description": "Workspace for team management testing"
                    }
                )

                if workspace_response.status_code == 201:
                    cls.test_workspace_id = workspace_response.json()["id"]
                else:
                    cls.skip_tests = True
                    cls.skip_reason = "Failed to create test workspace"

            else:
                cls.skip_tests = True
                cls.skip_reason = "Test mode not enabled or auth failed"

        except Exception as e:
            cls.skip_tests = True
            cls.skip_reason = f"Server not running or setup failed: {e}"

    def setup_method(self):
        """Set up each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)

    def test_list_team_members_empty(self):
        """Test listing team members for a workspace with only owner."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members",
            headers=self.admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least the owner
        assert "members" in data
        assert "total" in data
        assert "pending_invites" in data
        assert data["total"] >= 1
        assert data["pending_invites"] == 0

        # Owner should be in the list
        owner_found = False
        for member in data["members"]:
            if member["role"] == "owner":
                owner_found = True
                assert "user_id" in member
                assert "email" in member
                assert "display_name" in member
                assert "joined_at" in member
                break

        assert owner_found, "Owner not found in member list"

    def test_invite_team_member_success(self):
        """Test successfully inviting a team member."""
        invite_data = {
            "email": "newmember@example.com",
            "role": "member",
            "send_email": True
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.admin_headers,
            json=invite_data
        )

        assert response.status_code == 201
        data = response.json()

        assert "invitation_id" in data
        assert data["email"] == "newmember@example.com"
        assert data["role"] == "member"
        assert "expires_at" in data
        assert "invite_link" in data

        # Store invitation ID for later tests
        self.invitation_id = data["invitation_id"]

    def test_invite_duplicate_member_conflict(self):
        """Test inviting already invited email returns conflict."""
        invite_data = {
            "email": "newmember@example.com",  # Same as previous test
            "role": "admin",
            "send_email": False
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.admin_headers,
            json=invite_data
        )

        assert response.status_code == 409
        assert "pending invitation" in response.json()["detail"]

    def test_list_pending_invitations(self):
        """Test listing pending invitations."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/invitations",
            headers=self.admin_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "invitations" in data
        assert len(data["invitations"]) >= 1

        # Find our invitation
        invitation_found = False
        for invitation in data["invitations"]:
            if invitation["email"] == "newmember@example.com":
                invitation_found = True
                assert invitation["role"] == "member"
                assert invitation["status"] == "pending"
                assert "invited_by" in invitation
                assert "invited_at" in invitation
                assert "expires_at" in invitation
                break

        assert invitation_found, "Our invitation not found in list"

    def test_member_cannot_invite(self):
        """Test that members cannot invite other members."""
        invite_data = {
            "email": "anothermember@example.com",
            "role": "member",
            "send_email": False
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.member_headers,
            json=invite_data
        )

        assert response.status_code == 403
        assert "permission" in response.json()["detail"]

    def test_invalid_workspace_id_format(self):
        """Test invalid workspace ID format returns 400."""
        response = self.client.get(
            "/admin/api/v1/workspaces/invalid-id/members",
            headers=self.admin_headers
        )

        assert response.status_code == 400
        assert "Invalid workspace ID" in response.json()["detail"]

    def test_nonexistent_workspace_access_denied(self):
        """Test accessing non-existent workspace returns 403."""
        fake_workspace_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent

        response = self.client.get(
            f"/admin/api/v1/workspaces/{fake_workspace_id}/members",
            headers=self.admin_headers
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    def test_cancel_invitation_success(self):
        """Test canceling a pending invitation."""
        # First get the invitation ID from the list
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/invitations",
            headers=self.admin_headers
        )

        assert response.status_code == 200
        invitations = response.json()["invitations"]

        invitation_id = None
        for invitation in invitations:
            if invitation["email"] == "newmember@example.com":
                invitation_id = invitation["invitation_id"]
                break

        assert invitation_id is not None, "No invitation found to cancel"

        # Cancel the invitation
        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/invitations/{invitation_id}",
            headers=self.admin_headers
        )

        assert response.status_code == 204

    def test_cancel_nonexistent_invitation(self):
        """Test canceling non-existent invitation returns 404."""
        fake_invitation_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format

        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/invitations/{fake_invitation_id}",
            headers=self.admin_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_member_role_management_permissions(self):
        """Test role management permission validation."""
        # Try to update a non-existent member role
        fake_user_id = "fake-user-123"

        response = self.client.patch(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/{fake_user_id}/role",
            headers=self.admin_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_remove_nonexistent_member(self):
        """Test removing non-existent member returns 404."""
        fake_user_id = "fake-user-123"

        response = self.client.delete(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/{fake_user_id}",
            headers=self.admin_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_unauthorized_access_no_token(self):
        """Test that endpoints require authentication."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members"
        )

        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

    def test_invalid_role_in_invitation(self):
        """Test inviting with invalid role returns validation error."""
        invite_data = {
            "email": "test@example.com",
            "role": "invalid_role",
            "send_email": False
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.admin_headers,
            json=invite_data
        )

        assert response.status_code == 422  # Validation error

    def test_invite_as_owner_forbidden(self):
        """Test that inviting someone as owner is forbidden."""
        invite_data = {
            "email": "owner@example.com",
            "role": "owner",
            "send_email": False
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.admin_headers,
            json=invite_data
        )

        assert response.status_code == 422  # Should be validation error

    def test_list_members_pagination(self):
        """Test member list pagination parameters."""
        response = self.client.get(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members",
            headers=self.admin_headers,
            params={"skip": 0, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert len(data["members"]) <= 10

    def test_invalid_email_format_in_invitation(self):
        """Test inviting with invalid email format."""
        invite_data = {
            "email": "not-an-email",
            "role": "member",
            "send_email": False
        }

        response = self.client.post(
            f"/admin/api/v1/workspaces/{self.test_workspace_id}/members/invite",
            headers=self.admin_headers,
            json=invite_data
        )

        assert response.status_code == 422  # Validation error

    @classmethod
    def teardown_class(cls):
        """Clean up after all tests."""
        if hasattr(cls, 'client'):
            cls.client.close()
