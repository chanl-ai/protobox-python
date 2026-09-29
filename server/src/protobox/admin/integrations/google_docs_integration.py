"""Google Docs integration implementation."""

import logging
from typing import Any, Optional
import httpx

from ..integrations.base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class GoogleDocsIntegration(GoogleOAuth2Integration):
    """Google Docs OAuth2 integration."""
    
    integration_type = IntegrationType.GOOGLE_DOCS
    display_name = "Google Docs"
    description = "Connect Google Docs to create, read, and update documents"
    category = "productivity"
    capabilities = [
        IntegrationCapability.CREATE_DOCUMENT,
        IntegrationCapability.READ_DOCUMENT,
        IntegrationCapability.UPDATE_DOCUMENT,
        IntegrationCapability.EXPORT_DOCUMENT
    ]
    
    # OAuth2 scopes specific to Docs
    oauth_scopes = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file"  # To create new documents
    ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Google Docs integration."""
        return {
            "type": "object",
            "properties": {
                "document_defaults": {
                    "type": "object",
                    "title": "Document Defaults",
                    "properties": {
                        "default_folder": {
                            "type": "string",
                            "title": "Default Folder",
                            "description": "Default Drive folder for new documents",
                            "examples": ["My Drive", "Documents", "Projects"]
                        },
                        "template_document_id": {
                            "type": "string",
                            "title": "Template Document",
                            "description": "Document ID to use as template for new docs",
                            "pattern": "^[a-zA-Z0-9-_]+$"
                        },
                        "default_page_size": {
                            "type": "string",
                            "title": "Default Page Size",
                            "description": "Default page size for new documents",
                            "enum": ["LETTER", "A4", "LEGAL", "TABLOID"],
                            "default": "LETTER"
                        },
                        "default_orientation": {
                            "type": "string",
                            "title": "Default Orientation",
                            "description": "Default page orientation",
                            "enum": ["PORTRAIT", "LANDSCAPE"],
                            "default": "PORTRAIT"
                        }
                    }
                },
                "formatting": {
                    "type": "object",
                    "title": "Formatting Options",
                    "properties": {
                        "default_font": {
                            "type": "string",
                            "title": "Default Font",
                            "description": "Default font family for documents",
                            "enum": ["Arial", "Times New Roman", "Calibri", "Georgia", "Verdana", "Roboto"],
                            "default": "Arial"
                        },
                        "default_font_size": {
                            "type": "integer",
                            "title": "Default Font Size",
                            "description": "Default font size in points",
                            "minimum": 8,
                            "maximum": 72,
                            "default": 11
                        },
                        "default_line_spacing": {
                            "type": "number",
                            "title": "Default Line Spacing",
                            "description": "Default line spacing multiplier",
                            "enum": [1.0, 1.15, 1.5, 2.0],
                            "default": 1.15
                        },
                        "use_styles": {
                            "type": "boolean",
                            "title": "Use Styles",
                            "description": "Apply document styles for headings and paragraphs",
                            "default": True
                        }
                    }
                },
                "collaboration": {
                    "type": "object",
                    "title": "Collaboration Settings",
                    "properties": {
                        "enable_suggestions": {
                            "type": "boolean",
                            "title": "Enable Suggestions",
                            "description": "Use suggestion mode for edits",
                            "default": False
                        },
                        "enable_comments": {
                            "type": "boolean",
                            "title": "Enable Comments",
                            "description": "Allow adding comments to documents",
                            "default": True
                        },
                        "track_changes": {
                            "type": "boolean",
                            "title": "Track Changes",
                            "description": "Track document revision history",
                            "default": True
                        },
                        "auto_save": {
                            "type": "boolean",
                            "title": "Auto Save",
                            "description": "Automatically save changes",
                            "default": True
                        }
                    }
                },
                "export_settings": {
                    "type": "object",
                    "title": "Export Settings",
                    "properties": {
                        "default_export_format": {
                            "type": "string",
                            "title": "Default Export Format",
                            "description": "Default format for document exports",
                            "enum": ["PDF", "DOCX", "ODT", "RTF", "TXT", "HTML", "EPUB"],
                            "default": "PDF"
                        },
                        "include_comments_in_export": {
                            "type": "boolean",
                            "title": "Include Comments",
                            "description": "Include comments in exported documents",
                            "default": False
                        },
                        "include_suggestions_in_export": {
                            "type": "boolean",
                            "title": "Include Suggestions",
                            "description": "Include suggestions in exported documents",
                            "default": False
                        }
                    }
                },
                "automation": {
                    "type": "object",
                    "title": "Automation Settings",
                    "properties": {
                        "enable_mail_merge": {
                            "type": "boolean",
                            "title": "Enable Mail Merge",
                            "description": "Enable mail merge functionality",
                            "default": False
                        },
                        "enable_template_variables": {
                            "type": "boolean",
                            "title": "Enable Template Variables",
                            "description": "Support template variables like {{name}}",
                            "default": True
                        },
                        "auto_generate_toc": {
                            "type": "boolean",
                            "title": "Auto-generate TOC",
                            "description": "Automatically generate table of contents",
                            "default": False
                        },
                        "auto_number_headings": {
                            "type": "boolean",
                            "title": "Auto-number Headings",
                            "description": "Automatically number document headings",
                            "default": False
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
                            "description": "Default permission for shared documents",
                            "enum": ["reader", "commenter", "writer"],
                            "default": "reader"
                        },
                        "allow_copy": {
                            "type": "boolean",
                            "title": "Allow Copy",
                            "description": "Allow viewers to make copies",
                            "default": True
                        },
                        "allow_download": {
                            "type": "boolean",
                            "title": "Allow Download",
                            "description": "Allow viewers to download documents",
                            "default": True
                        },
                        "allow_print": {
                            "type": "boolean",
                            "title": "Allow Print",
                            "description": "Allow viewers to print documents",
                            "default": True
                        }
                    }
                }
            },
            "required": []
        }
    
    async def test_connection_health(self, access_token: str) -> IntegrationHealth:
        """Test Docs connection by creating a test document."""
        try:
            async with httpx.AsyncClient() as client:
                # Try to create a test document
                response = await client.post(
                    "https://docs.googleapis.com/v1/documents",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "title": "ProtoBox Connection Test Document"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    document_id = data.get("documentId")
                    
                    # Delete the test document
                    if document_id:
                        await client.delete(
                            f"https://www.googleapis.com/drive/v3/files/{document_id}",
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                    
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "test_result": "Successfully created and deleted test document",
                            "document_id": document_id
                        }
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Failed to create test document: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        except Exception as e:
            return IntegrationHealth(
                is_healthy=False,
                error_message=str(e),
                details={"error_type": type(e).__name__}
            )