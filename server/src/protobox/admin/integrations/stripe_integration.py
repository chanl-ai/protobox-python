"""Stripe API key + webhook integration."""

import hashlib
import hmac
from typing import Any

from loguru import logger

from ..models.integration import IntegrationType
from .base_classes import ApiKeyIntegration, IntegrationHealth, IntegrationCapability


class StripeIntegration(ApiKeyIntegration):
    """Stripe API key and webhook integration implementation."""

    integration_type = IntegrationType.STRIPE
    display_name = "Stripe"
    description = "Process payments, manage subscriptions, and track revenue for SaaS and e-commerce"
    
    # Capabilities for marketing and finance teams
    capabilities = [
        IntegrationCapability.PROCESS_PAYMENT,
        IntegrationCapability.CREATE_INVOICE,
        IntegrationCapability.TRACK_ORDER,
        IntegrationCapability.ANALYZE_DATA,
    ]
    
    # API key configuration
    api_key_name = "STRIPE_API_KEY"
    api_key_header = "Authorization"
    api_key_prefix = "Bearer"
    
    # Webhook configuration
    supports_webhooks = True
    webhook_secret_key = "STRIPE_WEBHOOK_SECRET"

    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Stripe connection by fetching account details."""
        try:
            import httpx
            
            api_key = credentials.get("api_key")
            if not api_key:
                return IntegrationHealth(
                    is_healthy=False,
                    error_message="Missing API key",
                    details={"error": "no_api_key"}
                )
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.stripe.com/v1/account",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return IntegrationHealth(
                        is_healthy=True,
                        error_message=f"Connected to Stripe account: {data.get('business_profile', {}).get('name', data.get('email', 'Unknown'))}",
                        details={
                            "account_id": data.get("id"),
                            "country": data.get("country"),
                            "currency": data.get("default_currency"),
                            "charges_enabled": data.get("charges_enabled"),
                            "payouts_enabled": data.get("payouts_enabled")
                        }
                    )
                elif response.status_code == 401:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message="Invalid API key",
                        details={"error": "invalid_api_key", "status": 401}
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Stripe API error: {response.status_code}",
                        details={"status": response.status_code, "error": response.text}
                    )
                    
        except Exception as e:
            logger.error(f"Error testing Stripe connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Connection test failed: {str(e)}",
                details={"error": str(e)}
            )

    def verify_webhook_signature(
        self, 
        payload: bytes, 
        signature: str, 
        webhook_secret: str
    ) -> bool:
        """Verify Stripe webhook signature."""
        try:
            # Stripe signature format: t=timestamp,v1=signature
            elements = signature.split(",")
            timestamp = None
            expected_sig = None
            
            for element in elements:
                key, value = element.split("=")
                if key == "t":
                    timestamp = value
                elif key == "v1":
                    expected_sig = value
            
            if not timestamp or not expected_sig:
                return False
            
            # Construct signed payload
            signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
            
            # Compute expected signature
            computed_sig = hmac.new(
                webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(computed_sig, expected_sig)
            
        except Exception as e:
            logger.error(f"Error verifying Stripe webhook signature: {e}")
            return False

    def get_capabilities(self) -> list[str]:
        """Get Stripe integration capabilities."""
        return [
            "create_payment",
            "create_subscription",
            "create_customer",
            "create_invoice",
            "process_refund",
            "list_transactions",
            "webhook_events",
            "create_payment_link",
            "manage_products"
        ]

    def get_action_templates(self) -> list[str]:
        """Get available action template IDs for Stripe."""
        return [
            "stripe_create_payment_intent",
            "stripe_create_customer",
            "stripe_create_subscription",
            "stripe_list_transactions",
            "stripe_webhook_handler"
        ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Stripe integration."""
        return {
            "type": "object",
            "properties": {
                "webhook_endpoint": {
                    "type": "string",
                    "title": "Webhook Endpoint URL",
                    "description": "Your webhook endpoint URL for Stripe events",
                    "format": "uri",
                    "readOnly": True,
                    "default": "${BASE_URL}/webhooks/stripe"
                },
                "webhook_events": {
                    "type": "array",
                    "title": "Webhook Events",
                    "description": "Events to listen for via webhooks",
                    "items": {
                        "type": "string",
                        "enum": [
                            "payment_intent.succeeded",
                            "payment_intent.failed",
                            "customer.subscription.created",
                            "customer.subscription.updated",
                            "customer.subscription.deleted",
                            "invoice.paid",
                            "invoice.payment_failed",
                            "checkout.session.completed",
                            "charge.refunded"
                        ]
                    },
                    "default": ["payment_intent.succeeded", "customer.subscription.created", "invoice.paid"]
                },
                "test_mode": {
                    "type": "boolean",
                    "title": "Test Mode",
                    "description": "Use Stripe test mode (test API keys)",
                    "default": True
                },
                "currency": {
                    "type": "string",
                    "title": "Default Currency",
                    "description": "Default currency for payments",
                    "enum": ["usd", "eur", "gbp", "cad", "aud", "jpy"],
                    "default": "usd"
                },
                "statement_descriptor": {
                    "type": "string",
                    "title": "Statement Descriptor",
                    "description": "Text that appears on customer's credit card statement",
                    "maxLength": 22,
                    "pattern": "^[a-zA-Z0-9 .-]*$"
                },
                "auto_tax": {
                    "type": "boolean",
                    "title": "Automatic Tax Calculation",
                    "description": "Enable Stripe Tax for automatic tax calculation",
                    "default": False
                },
                "billing_portal": {
                    "type": "boolean",
                    "title": "Customer Billing Portal",
                    "description": "Enable customer self-service billing portal",
                    "default": True
                }
            },
            "required": []
        }
    
    def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Get MCP tools for Stripe integration."""
        return [
            {
                "name": "stripe_create_payment",
                "description": "Create a payment intent for one-time payments",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "integer", "description": "Amount in cents"},
                        "currency": {"type": "string", "default": "usd"},
                        "customer_email": {"type": "string", "format": "email"},
                        "description": {"type": "string"},
                        "metadata": {"type": "object"}
                    },
                    "required": ["amount", "currency"]
                }
            },
            {
                "name": "stripe_create_subscription",
                "description": "Create a recurring subscription for a customer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "customer_email": {"type": "string", "format": "email"},
                        "price_id": {"type": "string", "description": "Stripe price ID"},
                        "trial_days": {"type": "integer", "minimum": 0},
                        "coupon": {"type": "string"}
                    },
                    "required": ["customer_email", "price_id"]
                }
            },
            {
                "name": "stripe_create_checkout",
                "description": "Create a Stripe Checkout session",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "price_id": {"type": "string"},
                        "quantity": {"type": "integer", "minimum": 1},
                        "success_url": {"type": "string", "format": "uri"},
                        "cancel_url": {"type": "string", "format": "uri"},
                        "mode": {"type": "string", "enum": ["payment", "subscription"]}
                    },
                    "required": ["price_id", "success_url", "cancel_url"]
                }
            },
            {
                "name": "stripe_list_customers",
                "description": "List customers with optional filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        "created_after": {"type": "string", "format": "date-time"}
                    }
                }
            },
            {
                "name": "stripe_revenue_report",
                "description": "Get revenue metrics and analytics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "date_from": {"type": "string", "format": "date"},
                        "date_to": {"type": "string", "format": "date"},
                        "metrics": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["mrr", "arr", "churn", "ltv"]}
                        }
                    },
                    "required": ["date_from", "date_to"]
                }
            }
        ]