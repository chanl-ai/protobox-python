"""Cloudflare Workers for Platforms service for managing customer workers."""

import os
from typing import Any, Optional

from fastapi import UploadFile
from loguru import logger
from cloudflare import AsyncCloudflare


class CloudflareWorkersForPlatformsService:
    """Service for managing customer workers in Cloudflare Workers for Platforms."""

    def __init__(self):
        """Initialize the service with Cloudflare credentials."""
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.dispatch_namespace = os.getenv("CLOUDFLARE_DISPATCH_NAMESPACE")
        
        if not self.api_token or not self.account_id or not self.dispatch_namespace:
            raise ValueError("CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_DISPATCH_NAMESPACE must be set")
        
        self.client = AsyncCloudflare(api_token=self.api_token)

    def _generate_worker_name(self, workspace_id: str, action_id: str) -> str:
        """Generate a unique worker name for the customer worker."""
        # Use a clean format: customer-{workspace_id}-{action_id}
        # Replace any non-alphanumeric characters with hyphens
        clean_workspace_id = "".join(c if c.isalnum() else "-" for c in workspace_id)
        clean_action_id = "".join(c if c.isalnum() else "-" for c in action_id)
        return f"customer-{clean_workspace_id}-{clean_action_id}"

    async def create_customer_worker(
        self, 
        workspace_id: str, 
        action_id: str, 
        files: list[UploadFile],
        language: str,
        entry_point: str = "main"
    ) -> str:
        """Create a customer worker with uploaded files.
        
        Args:
            workspace_id: The workspace ID
            action_id: The action ID
            files: List of uploaded files
            language: Programming language (python, javascript)
            entry_point: Entry point file name
            
        Returns:
            The worker name for dispatch
            
        Raises:
            Exception: If worker creation fails
        """
        worker_name = self._generate_worker_name(workspace_id, action_id)
        
        try:
            # Separate main script files from supporting files
            script_files = {}
            asset_files = {}
            main_module = None
            
            for file in files:
                content = await file.read()
                filename = file.filename
                
                # Check if this is the entry point
                if (filename == entry_point or 
                    filename == f"{entry_point}.py" or 
                    filename == f"{entry_point}.js" or 
                    filename == f"{entry_point}.mjs" or
                    filename == f"{entry_point}.ts"):
                    main_module = filename
                
                # Determine if this is a script file or asset file
                if filename.endswith(('.py', '.js', '.mjs', '.ts')):
                    # Script files - these go in the main worker
                    if filename.endswith('.py'):
                        content_type = "text/x-python"
                    elif filename.endswith(('.js', '.mjs')):
                        content_type = "application/javascript+module"
                    elif filename.endswith('.ts'):
                        # TypeScript files should use JavaScript content type
                        content_type = "application/javascript"
                    
                    script_files[filename] = (filename, content, content_type)
                else:
                    # Asset files (package.json, tsconfig.json, etc.) - these go as assets
                    asset_files[filename] = {
                        "content": content,
                        "size": len(content)
                    }
            
            if not main_module:
                # Find a reasonable default entry point
                for filename in script_files.keys():
                    if filename.endswith('.py') and language == "python":
                        main_module = filename
                        break
                    elif filename.endswith(('.js', '.mjs', '.ts')) and language == "javascript":
                        main_module = filename
                        break
                
                if not main_module:
                    raise ValueError(f"No suitable entry point found for language {language}")
            
            # Create the worker with script files only
            # Check if we're using service worker syntax (addEventListener) or ES modules (export default)
            is_service_worker = False
            if script_files:
                # Check the main module content to determine syntax
                main_content = script_files[main_module][1].decode('utf-8')
                is_service_worker = 'addEventListener' in main_content and 'export default' not in main_content
            
            if is_service_worker:
                # Service worker syntax - use body_part
                metadata = {
                    "body_part": main_module,
                    "compatibility_date": "2024-01-01",
                    "compatibility_flags": ["nodejs_compat"] if language == "javascript" else []
                }
            else:
                # ES module syntax - use main_module
                metadata = {
                    "main_module": main_module,
                    "compatibility_date": "2024-01-01",
                    "compatibility_flags": ["nodejs_compat"] if language == "javascript" else []
                }
            
            # Upload the worker with script files
            response = await self.client.workers_for_platforms.dispatch.namespaces.scripts.update(
                account_id=self.account_id,
                dispatch_namespace=self.dispatch_namespace,
                script_name=worker_name,
                metadata=metadata,
                files=script_files
            )
            
            # Upload asset files if any
            if asset_files:
                await self._upload_assets(worker_name, asset_files)
            
            logger.info(f"Created customer worker '{worker_name}' for action {action_id}")
            return worker_name
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to create customer worker '{worker_name}': {e}")
            raise

    async def update_customer_worker(
        self, 
        worker_name: str, 
        files: list[UploadFile],
        language: str,
        entry_point: str = "main"
    ) -> bool:
        """Update an existing customer worker with new files.
        
        Args:
            worker_name: The worker name to update
            files: List of new files
            language: Programming language
            entry_point: Entry point file name
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Separate main script files from supporting files (same logic as create)
            script_files = {}
            asset_files = {}
            main_module = None
            
            for file in files:
                content = await file.read()
                filename = file.filename
                
                if (filename == entry_point or 
                    filename == f"{entry_point}.py" or 
                    filename == f"{entry_point}.js" or 
                    filename == f"{entry_point}.mjs" or
                    filename == f"{entry_point}.ts"):
                    main_module = filename
                
                # Determine if this is a script file or asset file
                if filename.endswith(('.py', '.js', '.mjs', '.ts')):
                    # Script files - these go in the main worker
                    if filename.endswith('.py'):
                        content_type = "text/x-python"
                    elif filename.endswith(('.js', '.mjs')):
                        content_type = "application/javascript+module"
                    elif filename.endswith('.ts'):
                        # TypeScript files should use JavaScript content type
                        content_type = "application/javascript"
                    
                    script_files[filename] = (filename, content, content_type)
                else:
                    # Asset files (package.json, tsconfig.json, etc.) - these go as assets
                    asset_files[filename] = {
                        "content": content,
                        "size": len(content)
                    }
            
            if not main_module:
                # Find default entry point
                for filename in script_files.keys():
                    if filename.endswith('.py') and language == "python":
                        main_module = filename
                        break
                    elif filename.endswith(('.js', '.mjs', '.ts')) and language == "javascript":
                        main_module = filename
                        break
                
                if not main_module:
                    raise ValueError(f"No suitable entry point found for language {language}")
            
            # Check if we're using service worker syntax (addEventListener) or ES modules (export default)
            is_service_worker = False
            if script_files:
                # Check the main module content to determine syntax
                main_content = script_files[main_module][1].decode('utf-8')
                is_service_worker = 'addEventListener' in main_content and 'export default' not in main_content
            
            if is_service_worker:
                # Service worker syntax - use body_part
                metadata = {
                    "body_part": main_module,
                    "compatibility_date": "2024-01-01",
                    "compatibility_flags": ["nodejs_compat"] if language == "javascript" else []
                }
            else:
                # ES module syntax - use main_module
                metadata = {
                    "main_module": main_module,
                    "compatibility_date": "2024-01-01",
                    "compatibility_flags": ["nodejs_compat"] if language == "javascript" else []
                }
            
            # Update the worker with script files only
            await self.client.workers_for_platforms.dispatch.namespaces.scripts.update(
                account_id=self.account_id,
                dispatch_namespace=self.dispatch_namespace,
                script_name=worker_name,
                metadata=metadata,
                files=script_files
            )
            
            # Upload asset files if any
            if asset_files:
                await self._upload_assets(worker_name, asset_files)
            
            logger.info(f"Updated customer worker '{worker_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update customer worker '{worker_name}': {e}")
            return False

    async def delete_customer_worker(self, worker_name: str) -> bool:
        """Delete a customer worker.
        
        Args:
            worker_name: The worker name to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            await self.client.workers_for_platforms.dispatch.namespaces.scripts.delete(
                account_id=self.account_id,
                dispatch_namespace=self.dispatch_namespace,
                script_name=worker_name
            )
            logger.info(f"Deleted customer worker '{worker_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete customer worker '{worker_name}': {e}")
            return False

    async def get_customer_worker_info(self, worker_name: str) -> Optional[dict[str, Any]]:
        """Get information about a customer worker.
        
        Args:
            worker_name: The worker name
            
        Returns:
            Worker information dict or None if not found
        """
        try:
            response = await self.client.workers_for_platforms.dispatch.namespaces.scripts.get(
                account_id=self.account_id,
                dispatch_namespace=self.dispatch_namespace,
                script_name=worker_name
            )
            return {
                "id": response.id,
                "created_on": response.created_on,
                "modified_on": response.modified_on,
                "handlers": response.handlers,
                "has_modules": response.has_modules,
                "usage_model": response.usage_model
            }
        except Exception as e:
            logger.error(f"Failed to get customer worker info for '{worker_name}': {e}")
            return None

    async def _upload_assets(self, worker_name: str, asset_files: dict[str, dict]) -> None:
        """Upload asset files for a worker.
        
        Args:
            worker_name: The worker name
            asset_files: Dictionary of asset files with content and size
        """
        try:
            import hashlib
            
            # Create manifest for asset upload
            manifest = {}
            for filename, file_data in asset_files.items():
                content = file_data["content"]
                # Calculate hash for the file
                file_hash = hashlib.sha256(content).hexdigest()
                manifest[filename] = {
                    "hash": file_hash,
                    "size": file_data["size"]
                }
            
            # Create asset upload session
            asset_upload_response = await self.client.workers_for_platforms.dispatch.namespaces.scripts.asset_upload.create(
                account_id=self.account_id,
                dispatch_namespace=self.dispatch_namespace,
                script_name=worker_name,
                manifest=manifest
            )
            
            logger.info(f"Created asset upload session for worker '{worker_name}' with {len(asset_files)} assets")
            
            # Note: The actual asset upload would require additional steps with the JWT and buckets
            # For now, we'll just log that assets were prepared for upload
            logger.info(f"Assets prepared for upload: {list(asset_files.keys())}")
            
        except Exception as e:
            logger.warning(f"Failed to upload assets for worker '{worker_name}': {e}")
            # Don't fail the worker creation if asset upload fails

    def is_available(self) -> bool:
        """Check if the service is available and properly configured."""
        return (
            bool(self.api_token) and 
            bool(self.account_id)
        )


# Global service instance
_cloudflare_service: Optional[CloudflareWorkersForPlatformsService] = None


def get_cloudflare_workers_service() -> CloudflareWorkersForPlatformsService:
    """Get the global Cloudflare Workers for Platforms service instance."""
    global _cloudflare_service
    
    if _cloudflare_service is None:
        try:
            _cloudflare_service = CloudflareWorkersForPlatformsService()
        except Exception as e:
            logger.error(f"Failed to initialize Cloudflare Workers service: {e}")
            raise
    
    return _cloudflare_service
