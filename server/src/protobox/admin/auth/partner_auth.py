"""Partner authentication for B2B2C integration."""

import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request
from loguru import logger

from ..models.partner import Partner, PartnerAuthRequest


class PartnerAuth:
    """Partner authentication handler."""

    def __init__(self):
        # Demo partners for development
        self.demo_partners = {
            "demo_partner": {
                "id": "demo_partner",
                "name": "Demo Partner",
                "secret_key": "demo_secret_key_not_for_production",
                "allowed_endpoints": ["integrations", "actions", "tenants"],
                "is_active": True,
            },
            "try_protobox": {
                "id": "try_protobox",
                "name": "Try ProtoBox",
                "secret_key": "try_protobox_secret_key",
                "allowed_endpoints": ["integrations", "actions", "tenants"],
                "is_active": True,
            },
            "test_partner": {
                "id": "test_partner",
                "name": "Test Partner",
                "secret_key": "test_partner_secret_key",
                "allowed_endpoints": ["integrations", "actions", "tenants"],
                "is_active": True,
            },
        }

        # Demo workspace mappings for testing
        self.demo_workspace_mappings = {
            "demo_partner": {
                "demo_user_1": "670123456789abcdef123456",
                "demo_user_2": "670123456789abcdef123457",
            }
        }

    async def authenticate_request(
        self, request: Request, auth_request: PartnerAuthRequest
    ) -> Partner:
        """Authenticate a partner request."""
        try:
            partner_id = auth_request.partner_id

            # Get partner info (in production, this would be from database)
            partner_info = self.demo_partners.get(partner_id)
            if not partner_info:
                raise HTTPException(status_code=401, detail="Unknown partner")

            if not partner_info["is_active"]:
                raise HTTPException(status_code=401, detail="Partner inactive")

            # Get signature from headers
            signature = request.headers.get("X-Partner-Signature")
            if not signature:
                raise HTTPException(status_code=401, detail="Missing signature")

            # Verify signature
            expected_signature = self._generate_signature(auth_request, partner_info["secret_key"])
            if not hmac.compare_digest(signature, expected_signature):
                raise HTTPException(status_code=401, detail="Invalid signature")

            # Check timestamp (within 5 minutes)
            current_time = int(time.time() * 1000)
            if abs(current_time - auth_request.timestamp) > 300000:  # 5 minutes
                raise HTTPException(status_code=401, detail="Request timestamp expired")

            # Return partner object
            return Partner(
                id=partner_info["id"],
                name=partner_info["name"],
                partner_id=partner_info["id"],
                secret_key=partner_info["secret_key"],
                allowed_endpoints=partner_info["allowed_endpoints"],
                is_active=partner_info["is_active"],
                created_at=None,  # Not needed for demo
                updated_at=None,  # Not needed for demo
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Partner authentication error: {e}")
            raise HTTPException(status_code=500, detail="Authentication failed")

    def get_workspace_for_tenant(self, partner: Partner, tenant_id: str) -> str | None:
        """Get workspace ID for a partner tenant."""
        partner_mappings = self.demo_workspace_mappings.get(partner.partner_id, {})
        return partner_mappings.get(tenant_id)

    def _generate_signature(self, auth_request: PartnerAuthRequest, secret_key: str) -> str:
        """Generate HMAC signature for partner request."""
        # Create payload for signature
        payload = {
            "partner_id": auth_request.partner_id,
            "partner_user_id": auth_request.partner_user_id,
            "timestamp": auth_request.timestamp,
        }

        # Add data if present
        if auth_request.data:
            payload["data"] = auth_request.data

        # Create signature
        payload_string = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            secret_key.encode(), payload_string.encode(), hashlib.sha256
        ).hexdigest()



# Global instance
partner_auth = PartnerAuth()


def get_partner_auth() -> PartnerAuth:
    """Dependency to get partner auth instance."""
    return partner_auth
