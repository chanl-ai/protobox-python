"""Google Sheets integration implementation."""

import logging
from typing import Any, Optional
import httpx

from ..integrations.base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class GoogleSheetsIntegration(GoogleOAuth2Integration):
    """Google Sheets OAuth2 integration."""
    
    integration_type = IntegrationType.GOOGLE_SHEETS
    display_name = "Google Sheets"
    description = "Connect Google Sheets to read, write, and analyze spreadsheet data"
    category = "productivity"
    capabilities = [
        IntegrationCapability.READ_DATA,
        IntegrationCapability.WRITE_DATA,
        IntegrationCapability.CREATE_SPREADSHEET,
        IntegrationCapability.UPDATE_SPREADSHEET
    ]
    
    # OAuth2 scopes specific to Sheets
    oauth_scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file"  # To create new spreadsheets
    ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Google Sheets integration."""
        return {
            "type": "object",
            "properties": {
                "spreadsheet_defaults": {
                    "type": "object",
                    "title": "Spreadsheet Defaults",
                    "properties": {
                        "default_folder": {
                            "type": "string",
                            "title": "Default Folder",
                            "description": "Default Drive folder for new spreadsheets",
                            "examples": ["My Drive", "Spreadsheets", "Reports"]
                        },
                        "template_spreadsheet_id": {
                            "type": "string",
                            "title": "Template Spreadsheet",
                            "description": "Spreadsheet ID to use as template for new sheets",
                            "pattern": "^[a-zA-Z0-9-_]+$"
                        },
                        "default_locale": {
                            "type": "string",
                            "title": "Default Locale",
                            "description": "Default locale for number and date formatting",
                            "enum": ["en_US", "en_GB", "de_DE", "fr_FR", "es_ES", "it_IT", "pt_BR", "ja_JP", "zh_CN"],
                            "default": "en_US"
                        },
                        "default_timezone": {
                            "type": "string",
                            "title": "Default Timezone",
                            "description": "Default timezone for date/time values",
                            "default": "America/New_York"
                        }
                    }
                },
                "data_handling": {
                    "type": "object",
                    "title": "Data Handling",
                    "properties": {
                        "value_input_option": {
                            "type": "string",
                            "title": "Value Input Option",
                            "description": "How to interpret input data",
                            "enum": ["RAW", "USER_ENTERED"],
                            "default": "USER_ENTERED"
                        },
                        "value_render_option": {
                            "type": "string",
                            "title": "Value Render Option",
                            "description": "How to return formatted values",
                            "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                            "default": "FORMATTED_VALUE"
                        },
                        "date_time_render_option": {
                            "type": "string",
                            "title": "Date/Time Render Option",
                            "description": "How to represent date/time values",
                            "enum": ["SERIAL_NUMBER", "FORMATTED_STRING"],
                            "default": "FORMATTED_STRING"
                        },
                        "include_values_in_response": {
                            "type": "boolean",
                            "title": "Include Values in Response",
                            "description": "Return updated values after write operations",
                            "default": True
                        }
                    }
                },
                "batch_operations": {
                    "type": "object",
                    "title": "Batch Operations",
                    "properties": {
                        "batch_size": {
                            "type": "integer",
                            "title": "Batch Size",
                            "description": "Number of rows to process in a single batch",
                            "minimum": 100,
                            "maximum": 10000,
                            "default": 1000
                        },
                        "enable_batch_updates": {
                            "type": "boolean",
                            "title": "Enable Batch Updates",
                            "description": "Group multiple updates into single API calls",
                            "default": True
                        },
                        "batch_delay_ms": {
                            "type": "integer",
                            "title": "Batch Delay (ms)",
                            "description": "Delay between batch operations in milliseconds",
                            "minimum": 0,
                            "maximum": 5000,
                            "default": 100
                        }
                    }
                },
                "formulas_and_formatting": {
                    "type": "object",
                    "title": "Formulas & Formatting",
                    "properties": {
                        "preserve_formulas": {
                            "type": "boolean",
                            "title": "Preserve Formulas",
                            "description": "Keep formulas when copying data",
                            "default": True
                        },
                        "auto_resize_columns": {
                            "type": "boolean",
                            "title": "Auto-resize Columns",
                            "description": "Automatically adjust column widths",
                            "default": True
                        },
                        "default_number_format": {
                            "type": "string",
                            "title": "Default Number Format",
                            "description": "Default format for numeric values",
                            "enum": ["NUMBER", "CURRENCY", "PERCENT", "SCIENTIFIC", "ACCOUNTING"],
                            "default": "NUMBER"
                        },
                        "apply_conditional_formatting": {
                            "type": "boolean",
                            "title": "Apply Conditional Formatting",
                            "description": "Apply conditional formatting rules",
                            "default": False
                        }
                    }
                },
                "import_export": {
                    "type": "object",
                    "title": "Import/Export Settings",
                    "properties": {
                        "csv_delimiter": {
                            "type": "string",
                            "title": "CSV Delimiter",
                            "description": "Delimiter for CSV import/export",
                            "enum": [",", ";", "\t", "|"],
                            "default": ","
                        },
                        "skip_empty_rows": {
                            "type": "boolean",
                            "title": "Skip Empty Rows",
                            "description": "Skip empty rows during import",
                            "default": True
                        },
                        "skip_empty_columns": {
                            "type": "boolean",
                            "title": "Skip Empty Columns",
                            "description": "Skip empty columns during import",
                            "default": False
                        },
                        "header_row": {
                            "type": "boolean",
                            "title": "Has Header Row",
                            "description": "First row contains column headers",
                            "default": True
                        }
                    }
                },
                "permissions": {
                    "type": "object",
                    "title": "Permissions",
                    "properties": {
                        "default_share_permission": {
                            "type": "string",
                            "title": "Default Share Permission",
                            "description": "Default permission for shared spreadsheets",
                            "enum": ["reader", "commenter", "writer"],
                            "default": "reader"
                        },
                        "allow_public_sharing": {
                            "type": "boolean",
                            "title": "Allow Public Sharing",
                            "description": "Allow sharing spreadsheets publicly",
                            "default": False
                        },
                        "notify_on_share": {
                            "type": "boolean",
                            "title": "Notify on Share",
                            "description": "Send notifications when sharing",
                            "default": True
                        }
                    }
                }
            },
            "required": []
        }
    
    async def test_connection_health(self, access_token: str) -> IntegrationHealth:
        """Test Sheets connection by creating a test spreadsheet."""
        try:
            async with httpx.AsyncClient() as client:
                # Try to create a test spreadsheet
                response = await client.post(
                    "https://sheets.googleapis.com/v4/spreadsheets",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "properties": {
                            "title": "ProtoBox Connection Test"
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    spreadsheet_id = data.get("spreadsheetId")
                    
                    # Delete the test spreadsheet
                    if spreadsheet_id:
                        await client.delete(
                            f"https://www.googleapis.com/drive/v3/files/{spreadsheet_id}",
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "test_result": "Successfully created and deleted test spreadsheet",
                            "spreadsheet_url": data.get("spreadsheetUrl")
                        }
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Failed to create test spreadsheet: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        except Exception as e:
            return IntegrationHealth(
                is_healthy=False,
                error_message=str(e),
                details={"error_type": type(e).__name__}
            )