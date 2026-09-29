"""Tigris Object Storage service for knowledge base file management."""

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

from protobox.admin.config import settings


class TigrisService:
    """Service for managing files in Tigris Object Storage."""

    def __init__(self):
        """Initialize TigrisService with graceful failure handling."""
        # Service state
        self.available = False
        self.error_message = None
        self.s3_client = None
        self.bucket_name = None
        
        try:
            # Validate required configuration
            access_key = settings.tigris_access_key
            secret_key = settings.tigris_secret_key
            endpoint = settings.tigris_endpoint
            bucket_name = settings.tigris_bucket_name
            
            logger.info(f"Tigris config check: access_key={'✓' if access_key else '✗'}, "
                       f"secret_key={'✓' if secret_key else '✗'}, "
                       f"endpoint={'✓' if endpoint else '✗'}, "
                       f"bucket={'✓' if bucket_name else '✗'}")
            
            # Check if any required configuration is missing
            missing_configs = []
            if not access_key:
                missing_configs.append("AWS_ACCESS_KEY_ID (Tigris access key)")
            if not secret_key:
                missing_configs.append("AWS_SECRET_ACCESS_KEY (Tigris secret key)")
            if not endpoint:
                missing_configs.append("AWS_ENDPOINT_URL_S3 (Tigris endpoint)")
            if not bucket_name:
                missing_configs.append("AWS_BUCKET_NAME (Tigris bucket name)")
                
            if missing_configs:
                error_msg = f"Missing required Tigris S3 configuration: {', '.join(missing_configs)}"
                self.error_message = error_msg
                logger.warning(f"Tigris service disabled: {error_msg}")
                return

            # Configure S3 client for Tigris
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.tigris_endpoint,
                aws_access_key_id=settings.tigris_access_key,
                aws_secret_access_key=settings.tigris_secret_key,
                config=Config(
                    region_name='auto',  # Tigris uses 'auto' region
                    retries={'max_attempts': 3, 'mode': 'standard'},
                    signature_version='s3v4'
                )
            )

            self.bucket_name = settings.tigris_bucket_name

            # Perform health checks during initialization
            self._validate_s3_connectivity()
            self._ensure_bucket_exists()
            self._validate_presigned_url_capability()
            
            self.available = True
            logger.info(f"TigrisService initialized successfully for bucket '{self.bucket_name}'")
            
        except Exception as e:
            self.error_message = str(e)
            logger.warning(f"Tigris service disabled due to initialization error: {e}")
            # Don't raise - allow server to start without Tigris

    def _check_availability(self):
        """Check if Tigris service is available, raise exception if not."""
        if not self.available:
            raise RuntimeError(f"Tigris service unavailable: {self.error_message or 'Service not initialized'}")

    def _validate_s3_connectivity(self):
        """Validate S3 connectivity with fail-fast behavior."""
        try:
            # Test connectivity by listing buckets
            response = self.s3_client.list_buckets()
            logger.info(f"S3 connectivity validated - found {len(response.get('Buckets', []))} buckets")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"S3 connectivity check failed ({error_code}): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"S3 connectivity check failed with unexpected error: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _validate_presigned_url_capability(self):
        """Validate presigned URL generation capability."""
        try:
            # Test presigned URL generation with a dummy key
            test_key = "health-check/test-presigned-url"
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': test_key},
                ExpiresIn=60,  # 1 minute
                HttpMethod='GET'
            )
            if not url or not url.startswith(('http://', 'https://')):
                raise RuntimeError("Generated presigned URL is invalid")
            logger.info("Presigned URL generation capability validated")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = f"Presigned URL generation test failed ({error_code}): {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Presigned URL generation test failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _ensure_bucket_exists(self):
        """Ensure the Tigris bucket exists with fail-fast behavior."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Tigris bucket '{self.bucket_name}' exists and is accessible")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                # Bucket doesn't exist, attempt to create it
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created Tigris bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    create_code = create_error.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = f"Failed to create Tigris bucket '{self.bucket_name}' ({create_code}): {create_error}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from create_error
            elif error_code == '403':
                error_msg = f"Access denied to Tigris bucket '{self.bucket_name}' (403 Forbidden). Check permissions."
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            else:
                error_msg = f"Bucket validation failed for '{self.bucket_name}' ({error_code}): {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during bucket validation: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        workspace_id: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        action_id: str | None = None,
        file_type: Literal["knowledge", "code"] = "knowledge",
    ) -> str:
        """
        Upload file to Tigris storage.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            workspace_id: Workspace identifier
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
            file_type: Type of file ("knowledge" or "code")
            
        Returns:
            File path/key in storage
        """
        self._check_availability()
        
        if file_type == "code":
            assert action_id, "Action ID is required for code files"
            file_key = f"workspaces/{workspace_id}/code/{action_id}/{filename}"
        elif file_type == "knowledge":
            # Generate unique file key
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            file_key = f"workspaces/{workspace_id}/knowledge/{file_id}{file_extension}"
        else:
            raise ValueError(f"Invalid file type: {file_type}")
    
        logger.info(f"Uploading file to Tigris: {file_key}")

        try:
            # Prepare upload parameters
            upload_params = {
                'Bucket': self.bucket_name,
                'Key': file_key,
                'Body': file_content
            }

            if content_type:
                upload_params['ContentType'] = content_type

            # Add metadata
            file_metadata = {
                'original-filename': filename,
                'upload-timestamp': datetime.now(UTC).isoformat(),
                'file-size': str(len(file_content))
            }

            if metadata:
                file_metadata.update(metadata)

            # S3 metadata keys must be lowercase and contain only alphanumeric characters, hyphens, and underscores
            sanitized_metadata = {}
            for key, value in file_metadata.items():
                sanitized_key = key.lower().replace('_', '-')
                sanitized_metadata[sanitized_key] = str(value)

            upload_params['Metadata'] = sanitized_metadata

            # Upload file
            self.s3_client.put_object(**upload_params)

            logger.info(f"Uploaded file to Tigris: {file_key} (size: {len(file_content)} bytes)")
            return file_key

        except ClientError as e:
            logger.error(f"Failed to upload file to Tigris: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading to Tigris: {e}")
            raise

    async def upload_code_file(
        self,
        file_content: bytes,
        filename: str,
        workspace_id: str,
        action_id: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None
    ) -> str:
        """
        Upload code file for a specific action to Tigris storage.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            workspace_id: Workspace identifier
            action_id: Action identifier
            content_type: MIME type of the file
            metadata: Additional metadata to store with the file
            
        Returns:
            File path/key in storage
        """
        # Add action-specific metadata
        action_metadata = {
            'action-id': action_id,
            'file-type': 'code-action'
        }
        if metadata:
            action_metadata.update(metadata)
            
        return await self.upload_file(
            file_content=file_content,
            filename=filename,
            workspace_id=workspace_id,
            content_type=content_type,
            metadata=action_metadata,
            file_type="code",
            action_id=action_id,
        )

    async def download_file(self, file_key: str) -> bytes:
        self._check_availability()
        """
        Download file from Tigris storage.
        
        Args:
            file_key: File key/path in storage
            
        Returns:
            File content as bytes
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            content = response['Body'].read()

            logger.info(f"Downloaded file from Tigris: {file_key} (size: {len(content)} bytes)")
            return content

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise FileNotFoundError(f"File not found in Tigris: {file_key}")
            logger.error(f"Failed to download file from Tigris: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading from Tigris: {e}")
            raise

    async def delete_file(self, file_key: str) -> bool:
        self._check_availability()
        """
        Delete file from Tigris storage.
        
        Args:
            file_key: File key/path in storage
            
        Returns:
            True if successful, False if file not found
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            logger.info(f"Deleted file from Tigris: {file_key}")
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.warning(f"File not found in Tigris: {file_key}")
                return False
            logger.error(f"Failed to delete file from Tigris: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error deleting from Tigris: {e}")
            raise

    async def get_file_metadata(self, file_key: str) -> dict[str, Any] | None:
        """
        Get file metadata from Tigris storage.
        
        Args:
            file_key: File key/path in storage
            
        Returns:
            Metadata dictionary or None if file not found
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)

            metadata = {
                'file_size': response.get('ContentLength', 0),
                'content_type': response.get('ContentType', ''),
                'last_modified': response.get('LastModified', '').isoformat() if response.get('LastModified') else '',
                'etag': response.get('ETag', '').strip('"')
            }

            # Add custom metadata
            if 'Metadata' in response:
                metadata.update(response['Metadata'])

            return metadata

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['NoSuchKey', '404']:
                return None
            logger.error(f"Failed to get file metadata from Tigris: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting metadata from Tigris: {e}")
            raise

    async def list_files(self, prefix: str = "", max_files: int = 1000) -> list[dict[str, Any]]:
        """
        List files in Tigris storage with optional prefix filter.
        
        Args:
            prefix: File key prefix to filter by
            max_files: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            list_params = {
                'Bucket': self.bucket_name,
                'MaxKeys': max_files
            }

            if prefix:
                list_params['Prefix'] = prefix

            response = self.s3_client.list_objects_v2(**list_params)

            files = []
            for obj in response.get('Contents', []):
                file_info = {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"')
                }
                files.append(file_info)

            logger.info(f"Listed {len(files)} files from Tigris with prefix '{prefix}'")
            return files

        except ClientError as e:
            logger.error(f"Failed to list files from Tigris: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing files from Tigris: {e}")
            raise

    async def list_code_files(self, workspace_id: str, action_id: str) -> list[dict[str, Any]]:
        """
        List code files for a workspace, optionally filtered by action.
        
        Args:
            workspace_id: Workspace identifier
            action_id: Optional action identifier to filter by
            
        Returns:
            List of code file information dictionaries
        """
        prefix = f"workspaces/{workspace_id}/code/{action_id}/"
        files = await self.list_files(prefix=prefix)
        logger.warning(f"Listed code files from Tigris: {files}")

        # Add additional metadata for code files
        for file_info in files:
            try:
                metadata = await self.get_file_metadata(file_info['key'])
                if metadata:
                    file_info.update({
                        'original_filename': metadata.get('original-filename', ''),
                        'action_id': metadata.get('action-id', ''),
                        'file_type': metadata.get('file-type', ''),
                        'content_type': metadata.get('content_type', ''),
                    })
            except Exception as e:
                logger.warning(f"Failed to get metadata for file {file_info['key']}: {e}")
                
        return files

    async def get_code_file_content(self, file_key: str) -> bytes:
        """
        Get content of a code file.
        
        Args:
            file_key: File key in storage
            
        Returns:
            File content as bytes
        """
        logger.warning(f"Getting code file content from Tigris: {file_key}")
        return await self.download_file(file_key)

    def generate_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        http_method: str = "GET"
    ) -> str:
        self._check_availability()
        """
        Generate a presigned URL for direct access to a file.
        
        Args:
            file_key: File key in storage
            expiration: URL expiration time in seconds
            http_method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Presigned URL string
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration,
                HttpMethod=http_method
            )

            logger.info(f"Generated presigned URL for {file_key} (expires in {expiration}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating presigned URL: {e}")
            raise

    def health_check(self) -> dict[str, Any]:
        """
        Perform comprehensive health check of the Tigris service.
        
        Returns:
            Health status dictionary
        """
        try:
            start_time = time.time()
            
            # Test bucket access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            # Test presigned URL generation
            test_key = "health-check/test-presigned-url"
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': test_key},
                ExpiresIn=60
            )
            
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy',
                'bucket': self.bucket_name,
                'endpoint': settings.tigris_endpoint,
                'presigned_urls': 'supported',
                'response_time_ms': round(response_time * 1000, 2),
                'timestamp': datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'bucket': self.bucket_name,
                'endpoint': settings.tigris_endpoint,
                'error': str(e),
                'timestamp': datetime.now(UTC).isoformat()
            }


# Global instance - lazy initialized
_tigris_service = None

def get_tigris_service() -> TigrisService:
    """Get or create the global Tigris service instance"""
    global _tigris_service
    if _tigris_service is None:
        _tigris_service = TigrisService()
    return _tigris_service
