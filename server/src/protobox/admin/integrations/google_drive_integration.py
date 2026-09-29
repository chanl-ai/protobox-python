"""Google Drive integration implementation."""

import logging
from typing import Any, Optional
import httpx

from ..integrations.base_classes import IntegrationCapability, IntegrationHealth
from .google_base import GoogleOAuth2Integration
from ..models.integration import IntegrationType

logger = logging.getLogger(__name__)


class GoogleDriveIntegration(GoogleOAuth2Integration):
    """Google Drive OAuth2 integration."""
    
    integration_type = IntegrationType.GOOGLE_DRIVE
    display_name = "Google Drive"
    description = "Connect Google Drive to manage files, folders, and share documents"
    category = "storage"
    capabilities = [
        IntegrationCapability.UPLOAD_FILE,
        IntegrationCapability.DOWNLOAD_FILE,
        IntegrationCapability.SEARCH_FILES,
        IntegrationCapability.SHARE_FILE
    ]
    
    # OAuth2 scopes specific to Drive
    oauth_scopes = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    ]
    
    def get_settings_schema(self) -> dict[str, Any]:
        """Get settings schema for Google Drive integration."""
        return {
            "type": "object",
            "properties": {
                "storage_settings": {
                    "type": "object",
                    "title": "Storage Settings",
                    "properties": {
                        "default_folder": {
                            "type": "string",
                            "title": "Default Folder",
                            "description": "Default folder for uploads (folder ID or path)",
                            "examples": ["My Drive", "Shared Drives/Team"]
                        },
                        "organize_by_date": {
                            "type": "boolean",
                            "title": "Organize by Date",
                            "description": "Automatically organize files in date-based folders",
                            "default": False
                        },
                        "folder_structure": {
                            "type": "string",
                            "title": "Folder Structure",
                            "description": "Template for automatic folder creation",
                            "enum": ["YYYY/MM/DD", "YYYY/MM", "YYYY", "none"],
                            "default": "none"
                        }
                    }
                },
                "sync_settings": {
                    "type": "object",
                    "title": "Sync Settings",
                    "properties": {
                        "folders_to_sync": {
                            "type": "array",
                            "title": "Folders to Sync",
                            "description": "Specific folders to sync",
                            "items": {
                                "type": "string"
                            },
                            "default": ["My Drive"]
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "title": "Exclude Patterns",
                            "description": "File patterns to exclude from sync (glob patterns)",
                            "items": {
                                "type": "string"
                            },
                            "examples": ["*.tmp", "~*", ".DS_Store"]
                        },
                        "sync_shared_drives": {
                            "type": "boolean",
                            "title": "Sync Shared Drives",
                            "description": "Include shared drives in sync",
                            "default": True
                        },
                        "sync_trash": {
                            "type": "boolean",
                            "title": "Sync Trash",
                            "description": "Include trashed files in sync",
                            "default": False
                        }
                    }
                },
                "sharing_defaults": {
                    "type": "object",
                    "title": "Sharing Defaults",
                    "properties": {
                        "default_permission": {
                            "type": "string",
                            "title": "Default Permission",
                            "description": "Default permission level for shared files",
                            "enum": ["reader", "commenter", "writer"],
                            "default": "reader"
                        },
                        "link_sharing": {
                            "type": "string",
                            "title": "Link Sharing",
                            "description": "Default link sharing setting",
                            "enum": ["restricted", "anyone_with_link", "public"],
                            "default": "restricted"
                        },
                        "notify_on_share": {
                            "type": "boolean",
                            "title": "Notify on Share",
                            "description": "Send email notifications when sharing files",
                            "default": True
                        },
                        "allow_download": {
                            "type": "boolean",
                            "title": "Allow Download",
                            "description": "Allow viewers and commenters to download files",
                            "default": True
                        }
                    }
                },
                "file_handling": {
                    "type": "object",
                    "title": "File Handling",
                    "properties": {
                        "convert_uploads": {
                            "type": "boolean",
                            "title": "Convert Uploads",
                            "description": "Convert uploaded files to Google formats",
                            "default": False
                        },
                        "ocr_enabled": {
                            "type": "boolean",
                            "title": "Enable OCR",
                            "description": "Extract text from images and PDFs",
                            "default": True
                        },
                        "duplicate_handling": {
                            "type": "string",
                            "title": "Duplicate Handling",
                            "description": "How to handle duplicate file names",
                            "enum": ["rename", "replace", "skip", "version"],
                            "default": "rename"
                        },
                        "max_file_size_mb": {
                            "type": "integer",
                            "title": "Max File Size (MB)",
                            "description": "Maximum file size for uploads in MB",
                            "minimum": 1,
                            "maximum": 5120,  # 5GB
                            "default": 100
                        }
                    }
                },
                "search_settings": {
                    "type": "object",
                    "title": "Search Settings",
                    "properties": {
                        "include_file_content": {
                            "type": "boolean",
                            "title": "Search File Content",
                            "description": "Search within file content, not just names",
                            "default": True
                        },
                        "search_trash": {
                            "type": "boolean",
                            "title": "Search Trash",
                            "description": "Include trashed files in search results",
                            "default": False
                        },
                        "max_results": {
                            "type": "integer",
                            "title": "Max Search Results",
                            "description": "Maximum number of search results",
                            "minimum": 10,
                            "maximum": 1000,
                            "default": 100
                        }
                    }
                },
                "quota_alerts": {
                    "type": "object",
                    "title": "Quota Alerts",
                    "properties": {
                        "enable_alerts": {
                            "type": "boolean",
                            "title": "Enable Quota Alerts",
                            "description": "Send alerts when storage quota is low",
                            "default": True
                        },
                        "alert_threshold_percent": {
                            "type": "integer",
                            "title": "Alert Threshold (%)",
                            "description": "Alert when storage usage exceeds this percentage",
                            "minimum": 50,
                            "maximum": 99,
                            "default": 90
                        }
                    }
                }
            },
            "required": []
        }
    
    async def test_connection_health(self, access_token: str) -> IntegrationHealth:
        """Test Drive connection by fetching storage quota."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/drive/v3/about?fields=user,storageQuota",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    quota = data.get("storageQuota", {})
                    return IntegrationHealth(
                        is_healthy=True,
                        details={
                            "user_email": data.get("user", {}).get("emailAddress"),
                            "storage_used": quota.get("usage"),
                            "storage_limit": quota.get("limit"),
                            "in_drive": quota.get("usageInDrive")
                        }
                    )
                else:
                    return IntegrationHealth(
                        is_healthy=False,
                        error_message=f"Failed to fetch Drive info: {response.status_code}",
                        details={"status_code": response.status_code}
                    )
        except Exception as e:
            return IntegrationHealth(
                is_healthy=False,
                error_message=str(e),
                details={"error_type": type(e).__name__}
            )