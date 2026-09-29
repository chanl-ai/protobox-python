"""Google Calendar integration implementation."""

import logging
from typing import Any, Optional

from ..integrations.base_classes import ActionTemplate, IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class GoogleCalendarIntegration(GoogleOAuth2Integration):
    """Google Calendar OAuth2 integration."""
    
    integration_type = IntegrationType.GOOGLE_CALENDAR
    display_name = "Google Calendar"
    description = "Connect Google Calendar for scheduling and availability management"
    category = "productivity"
    capabilities = [
        IntegrationCapability.CREATE_EVENT,
        IntegrationCapability.CHECK_AVAILABILITY,
        IntegrationCapability.UPDATE_EVENT,
        IntegrationCapability.DELETE_EVENT
    ]
    
    # OAuth2 scopes specific to Calendar
    oauth_scopes = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly"
    ]
    
    def _deprecated_get_action_templates(self) -> list[ActionTemplate]:
        """Get Google Calendar action templates."""
        return [
            ActionTemplate(
                id="google_calendar_create_event",
                name="Create Calendar Event",
                description="Create a new event in Google Calendar",
                category="scheduling",
                capability=IntegrationCapability.CREATE_EVENT,
                required_integrations=[IntegrationType.GOOGLE_CALENDAR],
                optional_integrations=[],
                config_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Event title"},
                        "description": {"type": "string", "description": "Event description"},
                        "start": {"type": "string", "format": "date-time"},
                        "end": {"type": "string", "format": "date-time"},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"}
                        },
                        "location": {"type": "string"},
                        "reminders": {
                            "type": "object",
                            "properties": {
                                "useDefault": {"type": "boolean"},
                                "overrides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {"type": "string", "enum": ["email", "popup"]},
                                            "minutes": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "required": ["summary", "start", "end"]
                },
                default_config={
                    "reminders": {"useDefault": True}
                }
            ),
            ActionTemplate(
                id="google_calendar_check_availability",
                name="Check Calendar Availability",
                description="Check if a time slot is available",
                category="scheduling",
                capability=IntegrationCapability.CHECK_AVAILABILITY,
                required_integrations=[IntegrationType.GOOGLE_CALENDAR],
                optional_integrations=[],
                config_schema={
                    "type": "object",
                    "properties": {
                        "timeMin": {"type": "string", "format": "date-time"},
                        "timeMax": {"type": "string", "format": "date-time"},
                        "calendars": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Calendar IDs to check"
                        }
                    },
                    "required": ["timeMin", "timeMax"]
                },
                default_config={
                    "calendars": ["primary"]
                }
            ),
            ActionTemplate(
                id="google_calendar_list_events",
                name="List Calendar Events",
                description="List events from Google Calendar",
                category="scheduling",
                capability=IntegrationCapability.UPDATE_EVENT,  # Using as proxy for list
                required_integrations=[IntegrationType.GOOGLE_CALENDAR],
                optional_integrations=[],
                config_schema={
                    "type": "object",
                    "properties": {
                        "calendarId": {"type": "string", "default": "primary"},
                        "timeMin": {"type": "string", "format": "date-time"},
                        "timeMax": {"type": "string", "format": "date-time"},
                        "maxResults": {"type": "integer", "default": 10},
                        "orderBy": {"type": "string", "enum": ["startTime", "updated"]}
                    }
                },
                default_config={
                    "calendarId": "primary",
                    "maxResults": 10,
                    "orderBy": "startTime"
                }
            )
        ]
    
    async def test_connection(self, credentials: dict[str, Any]) -> IntegrationHealth:
        """Test Google Calendar connection."""
        # First check for access token
        if not credentials.get("access_token"):
            return IntegrationHealth(
                is_healthy=False,
                error_message="No access token found. Please reconnect Google Calendar."
            )
        
        # TODO: Make actual API call to verify token
        # For now, just check token exists
        try:
            # In production, would call:
            # GET https://www.googleapis.com/calendar/v3/users/me/calendarList
            # with Bearer token
            
            return IntegrationHealth(
                is_healthy=True,
                details={
                    "token_type": credentials.get("token_type", "Bearer"),
                    "scopes": credentials.get("scope", "").split() if credentials.get("scope") else [],
                    "calendar_access": True
                }
            )
        except Exception as e:
            logger.error(f"Failed to test Google Calendar connection: {e}")
            return IntegrationHealth(
                is_healthy=False,
                error_message=f"Failed to connect to Google Calendar: {str(e)}"
            )
    
    def get_oauth_url(self, redirect_uri: str, state: str) -> str:
        """Generate OAuth authorization URL."""
        from urllib.parse import urlencode
        
        from ..config import settings
        
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.oauth_scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        
        return f"{self.oauth_authorize_url}?{urlencode(params)}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        import httpx
        
        from ..config import settings
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.oauth_token_url,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to exchange code: {response.text}")
            
            return response.json()
    
    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token."""
        import httpx
        
        from ..config import settings
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.oauth_token_url,
                data={
                    "refresh_token": refresh_token,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "grant_type": "refresh_token"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to refresh token: {response.text}")
            
            return response.json()
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Google Calendar integration."""
        return {
            "type": "object",
            "properties": {
                "default_calendar": {
                    "type": "string",
                    "title": "Default Calendar",
                    "description": "Default calendar for creating events",
                    "default": "primary"
                },
                "default_reminder_minutes": {
                    "type": "integer",
                    "title": "Default Reminder",
                    "description": "Default reminder time in minutes before events",
                    "minimum": 0,
                    "maximum": 40320,  # 4 weeks
                    "default": 10
                },
                "working_hours": {
                    "type": "object",
                    "title": "Working Hours",
                    "properties": {
                        "start": {
                            "type": "string",
                            "title": "Start Time",
                            "description": "Daily working hours start (HH:MM format)",
                            "pattern": "^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
                            "default": "09:00"
                        },
                        "end": {
                            "type": "string",
                            "title": "End Time",
                            "description": "Daily working hours end (HH:MM format)",
                            "pattern": "^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
                            "default": "17:00"
                        },
                        "timezone": {
                            "type": "string",
                            "title": "Timezone",
                            "description": "Timezone for working hours",
                            "default": "America/New_York"
                        }
                    }
                },
                "event_defaults": {
                    "type": "object",
                    "title": "Event Defaults",
                    "properties": {
                        "duration_minutes": {
                            "type": "integer",
                            "title": "Default Duration",
                            "description": "Default event duration in minutes",
                            "minimum": 15,
                            "maximum": 480,
                            "default": 30
                        },
                        "visibility": {
                            "type": "string",
                            "title": "Default Visibility",
                            "enum": ["default", "public", "private", "confidential"],
                            "default": "default"
                        },
                        "show_as": {
                            "type": "string",
                            "title": "Show As",
                            "description": "Default availability status",
                            "enum": ["busy", "free"],
                            "default": "busy"
                        },
                        "color_id": {
                            "type": "string",
                            "title": "Event Color",
                            "description": "Default color for events (1-11)",
                            "enum": ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
                            "default": ""
                        }
                    }
                },
                "sync_settings": {
                    "type": "object",
                    "title": "Sync Settings",
                    "properties": {
                        "sync_period_days": {
                            "type": "integer",
                            "title": "Sync Period",
                            "description": "Number of days to sync (past and future)",
                            "minimum": 1,
                            "maximum": 365,
                            "default": 30
                        },
                        "auto_decline_conflicts": {
                            "type": "boolean",
                            "title": "Auto-decline Conflicts",
                            "description": "Automatically decline conflicting invitations",
                            "default": False
                        },
                        "include_declined": {
                            "type": "boolean",
                            "title": "Include Declined Events",
                            "description": "Include declined events in sync",
                            "default": False
                        }
                    }
                },
                "notification_settings": {
                    "type": "object",
                    "title": "Notifications",
                    "properties": {
                        "email_notifications": {
                            "type": "boolean",
                            "title": "Email Notifications",
                            "description": "Send email notifications for events",
                            "default": True
                        },
                        "popup_notifications": {
                            "type": "boolean",
                            "title": "Popup Notifications",
                            "description": "Show popup notifications for events",
                            "default": True
                        },
                        "notify_on_creation": {
                            "type": "boolean",
                            "title": "Notify on Creation",
                            "description": "Send notifications when events are created",
                            "default": False
                        },
                        "notify_on_change": {
                            "type": "boolean",
                            "title": "Notify on Change",
                            "description": "Send notifications when events are modified",
                            "default": True
                        },
                        "notify_on_cancellation": {
                            "type": "boolean",
                            "title": "Notify on Cancellation",
                            "description": "Send notifications when events are cancelled",
                            "default": True
                        }
                    }
                }
            },
            "required": []
        }

    async def fetch_user_calendars(self, access_token: str) -> dict[str, Any]:
        """Fetch user's calendar list from Google Calendar API."""
        import httpx
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch calendar list: {response.status_code} - {response.text}")
                    return {
                        "calendars": [],
                        "error": f"Failed to fetch calendars: {response.status_code}"
                    }
                
                data = response.json()
                calendars = []
                
                for item in data.get("items", []):
                    calendars.append({
                        "id": item.get("id"),
                        "summary": item.get("summary"),
                        "description": item.get("description", ""),
                        "primary": item.get("primary", False),
                        "access_role": item.get("accessRole"),
                        "color_id": item.get("colorId"),
                        "background_color": item.get("backgroundColor"),
                        "foreground_color": item.get("foregroundColor"),
                        "time_zone": item.get("timeZone"),
                        "selected": item.get("selected", True)  # Default to selected
                    })
                
                # Get user's timezone from settings or primary calendar
                timezone = None
                for cal in calendars:
                    if cal.get("primary"):
                        timezone = cal.get("time_zone")
                        break
                
                return {
                    "calendars": calendars,
                    "timezone": timezone,
                    "last_fetched": None  # Will be set by the service
                }
                
        except Exception as e:
            logger.error(f"Error fetching calendar data: {e}")
            return {
                "calendars": [],
                "error": f"Error fetching calendars: {str(e)}"
            }