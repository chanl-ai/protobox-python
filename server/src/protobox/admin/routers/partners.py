"""Partner API routes for B2B2C integration."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ..auth.partner_auth import get_partner_auth
from ..models.partner import PartnerAuthRequest, TenantCreate, TenantResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["partners"])

# Service instances will be injected by the main router
integration_service = None
action_service = None


def get_cors_headers(origin: str = "*") -> dict:
    """Get CORS headers for partner API responses."""
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Partner-Signature, Authorization",
        "Access-Control-Max-Age": "86400",
    }


@router.post("/integrations")
async def list_partner_integrations(
    request: Request, auth_request: PartnerAuthRequest, auth=Depends(get_partner_auth)
):
    """List integrations for a partner tenant."""
    try:
        # Authenticate partner
        partner = await auth.authenticate_request(request, auth_request)

        # Check endpoint access
        if "integrations" not in partner.allowed_endpoints:
            raise HTTPException(status_code=403, detail="Endpoint not allowed")

        # Get workspace for tenant
        workspace_id = auth.get_workspace_for_tenant(partner, auth_request.partner_user_id)
        if not workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"No workspace found for tenant: {auth_request.partner_user_id}",
            )

        # Get integrations
        if not integration_service:
            raise HTTPException(status_code=500, detail="Integration service not initialized")
        integrations = await integration_service.get_workspace_integrations(workspace_id)

        # Convert to dict for JSON response
        integrations_data = [integration.model_dump(mode="json") for integration in integrations]

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=integrations_data, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing partner integrations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/integrations/{integration_id}/disconnect")
async def disconnect_partner_integration(
    integration_id: str,
    request: Request,
    auth_request: PartnerAuthRequest,
    auth=Depends(get_partner_auth),
):
    """Disconnect an integration for a partner tenant."""
    try:
        # Authenticate partner
        partner = await auth.authenticate_request(request, auth_request)

        # Check endpoint access
        if "integrations" not in partner.allowed_endpoints:
            raise HTTPException(status_code=403, detail="Endpoint not allowed")

        # Get workspace for tenant
        workspace_id = auth.get_workspace_for_tenant(partner, auth_request.partner_user_id)
        if not workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"No workspace found for tenant: {auth_request.partner_user_id}",
            )

        # Update integration status to disconnected
        if not integration_service:
            raise HTTPException(status_code=500, detail="Integration service not initialized")

        # For now, just return success since disconnect isn't implemented
        # In production, this would update the integration status

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(
            content={"success": True, "integration_id": integration_id},
            headers=get_cors_headers(origin),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting partner integration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/actions")
async def list_partner_actions(
    request: Request, auth_request: PartnerAuthRequest, auth=Depends(get_partner_auth)
):
    """List actions for a partner tenant."""
    try:
        # Authenticate partner
        partner = await auth.authenticate_request(request, auth_request)

        # Check endpoint access
        if "actions" not in partner.allowed_endpoints:
            raise HTTPException(status_code=403, detail="Endpoint not allowed")

        # Get workspace for tenant
        workspace_id = auth.get_workspace_for_tenant(partner, auth_request.partner_user_id)
        if not workspace_id:
            raise HTTPException(
                status_code=404,
                detail=f"No workspace found for tenant: {auth_request.partner_user_id}",
            )

        # Get actions
        if not action_service:
            raise HTTPException(status_code=500, detail="Action service not initialized")
        actions = await action_service.list_actions(workspace_id)

        # Convert to dict for JSON response
        actions_data = [action.model_dump(mode="json") for action in actions]

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=actions_data, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing partner actions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/tenants")
async def create_or_get_tenant(
    request: Request, auth_request: PartnerAuthRequest, auth=Depends(get_partner_auth)
):
    """Create or get a tenant workspace for a partner."""
    try:
        # Authenticate partner
        partner = await auth.authenticate_request(request, auth_request)

        # Check endpoint access
        if "tenants" not in partner.allowed_endpoints:
            raise HTTPException(status_code=403, detail="Endpoint not allowed")

        # Extract tenant data
        tenant_data = TenantCreate(**(auth_request.data or {}))

        # Check if tenant already has a workspace
        workspace_id = auth.get_workspace_for_tenant(partner, tenant_data.tenant_id)

        if workspace_id:
            # Return existing workspace
            return JSONResponse(
                content=TenantResponse(
                    workspace_id=workspace_id, tenant_id=tenant_data.tenant_id, status="active"
                ).dict(),
                headers=get_cors_headers(request.headers.get("Origin", "*")),
            )

        # In production, create new workspace here
        # For now, return error
        raise HTTPException(
            status_code=404, detail="Tenant not found. In production, would create new workspace."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/getting tenant: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/validate")
async def validate_partner_access(
    request: Request, partner_id: str = Query(None), user_id: str = Query(None)
):
    """Validate partner and user access (lightweight endpoint for iframe)."""
    try:
        # For now, simple validation - in production would check against database
        if not partner_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing partner_id or user_id")

        # Check if it's a demo partner
        demo_partners = ["demo_partner", "try_protobox", "test_partner", "test_partner_dev"]
        is_demo = partner_id in demo_partners

        result = {
            "valid": True,
            "partner_id": partner_id,
            "user_id": user_id,
            "is_demo": is_demo,
            "mode": "demo" if is_demo else "production",
        }

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=result, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating partner access: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/available")
async def get_available_integrations(
    request: Request, partner_id: str = Query(None), user_id: str = Query(None)
):
    """Get available integrations for a partner (public endpoint)."""
    try:
        if not partner_id:
            raise HTTPException(status_code=400, detail="Missing partner_id")

        # Get all available integration types
        available_integrations = [
            {
                "id": "google_calendar",
                "integration_type": "google_calendar",
                "display_name": "Google Calendar",
                "description": "Schedule meetings and manage events",
                "category": "calendar",
                "is_connected": False,
                "status": "available",
                "permissions": ["calendar.read", "calendar.write"],
            },
            {
                "id": "hubspot",
                "integration_type": "hubspot",
                "display_name": "HubSpot",
                "description": "CRM and marketing automation",
                "category": "crm",
                "is_connected": False,
                "status": "available",
                "permissions": ["contacts.read", "contacts.write", "deals.read"],
            },
            {
                "id": "slack",
                "integration_type": "slack",
                "display_name": "Slack",
                "description": "Team communication and notifications",
                "category": "communication",
                "is_connected": False,
                "status": "available",
                "permissions": ["messages.write", "channels.read"],
            },
            {
                "id": "salesforce",
                "integration_type": "salesforce",
                "display_name": "Salesforce",
                "description": "Customer relationship management",
                "category": "crm",
                "is_connected": False,
                "status": "available",
                "permissions": ["contacts.read", "contacts.write", "opportunities.read"],
            },
            {
                "id": "stripe",
                "integration_type": "stripe",
                "display_name": "Stripe",
                "description": "Payment processing and subscriptions",
                "category": "payments",
                "is_connected": False,
                "status": "available",
                "permissions": ["payments.read", "subscriptions.manage"],
            },
            {
                "id": "shopify",
                "integration_type": "shopify",
                "display_name": "Shopify",
                "description": "E-commerce platform integration",
                "category": "ecommerce",
                "is_connected": False,
                "status": "available",
                "permissions": ["products.read", "orders.read", "customers.read"],
            },
        ]

        # Partner-specific filtering could be applied here
        # For demo partners, limit to certain integrations
        demo_partners = ["demo_partner", "try_protobox", "test_partner"]
        if partner_id in demo_partners:
            # Demo partners get limited integrations
            available_integrations = [
                i
                for i in available_integrations
                if i["integration_type"] in ["google_calendar", "slack", "stripe"]
            ]

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=available_integrations, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available integrations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/{integration_type}/connect")
async def start_integration_oauth(
    integration_type: str,
    request: Request,
    partner_id: str = Query(None),
    user_id: str = Query(None),
):
    """Start OAuth flow for connecting an integration."""
    try:
        if not partner_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing partner_id or user_id")

        # For demo mode, return a demo OAuth URL
        demo_partners = ["demo_partner", "try_protobox", "test_partner", "test_partner_dev"]
        if partner_id in demo_partners:
            # Return demo OAuth URL
            result = {
                "authorization_url": f"/integrations/demo-oauth?integration={integration_type}",
                "state": "demo_state_12345",
            }
        else:
            # In production, would generate real OAuth URL
            # For now, return error
            raise HTTPException(status_code=501, detail="Production OAuth not implemented yet")

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=result, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/{integration_type}/disconnect")
async def disconnect_integration_get(
    integration_type: str,
    request: Request,
    partner_id: str = Query(None),
    user_id: str = Query(None),
):
    """Disconnect an integration (GET version for iframe)."""
    try:
        if not partner_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing partner_id or user_id")

        # For demo/sandbox, just return success
        result = {
            "success": True,
            "integration_type": integration_type,
            "message": "Integration disconnected",
        }

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=result, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting integration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/integrations/{integration_id}/status")
async def get_integration_status(
    integration_id: str, request: Request, partner_id: str = Query(None), user_id: str = Query(None)
):
    """Get status of a specific integration."""
    try:
        if not partner_id or not user_id:
            raise HTTPException(status_code=400, detail="Missing partner_id or user_id")

        # Mock status response
        result = {
            "id": integration_id,
            "integration_type": integration_id,  # In real implementation, would look this up
            "is_connected": False,
            "status": "disconnected",
            "last_sync": None,
        }

        # Return with CORS headers
        origin = request.headers.get("Origin", "*")
        return JSONResponse(content=result, headers=get_cors_headers(origin))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.options("/{path:path}")
async def handle_options(request: Request):
    """Handle CORS preflight requests."""
    origin = request.headers.get("Origin", "*")
    return JSONResponse(content={}, headers=get_cors_headers(origin))
