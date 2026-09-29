"""Client for Document Processor Service."""

from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings


class DocumentProcessorClient:
    """Client for calling the document processor microservice."""

    def __init__(self):
        # Use environment variable or default to Docker service name
        self.base_url = getattr(settings, 'document_processor_url', 'http://document-processor:8092')
        self.timeout = httpx.Timeout(120.0, connect=10.0)
        self.headers = {"Content-Type": "application/json"}

        # Add API key if configured
        api_key = getattr(settings, 'document_processor_api_key', None)
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
            logger.info(f"Document processor client initialized with URL: {self.base_url} (authenticated)")
        else:
            logger.info(f"Document processor client initialized with URL: {self.base_url} (no authentication)")

    async def check_health(self) -> bool:
        """Check if document processor service is healthy."""
        try:
            headers = {}
            api_key = getattr(settings, 'document_processor_api_key', None)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health", headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Document processor healthy: {data.get('capabilities', [])}")
                    return True
                logger.warning(f"Document processor health check failed with status {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Document processor health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def process_document(
        self,
        signed_url: str,
        file_type: str,
        file_size: int | None = None,
        options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a document using the document processor service.
        
        Args:
            signed_url: Pre-signed S3 URL for document access
            file_type: File extension (pdf, docx, xlsx, etc.)
            file_size: Optional file size for validation
            options: Processing options (OCR, table extraction, etc.)
            
        Returns:
            Processed document content and metadata
            
        Raises:
            httpx.RequestError: If service is unreachable
            httpx.HTTPStatusError: If processing fails
        """
        options = options or {}

        # Check if service is available
        is_healthy = await self.check_health()
        if not is_healthy:
            logger.warning("Document processor not available, using fallback")
            return await self._fallback_processing(signed_url, file_type)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Sending {file_type} document to processor service")

                response = await client.post(
                    f"{self.base_url}/v1/process",
                    json={
                        "signed_url": signed_url,
                        "file_type": file_type,
                        "file_size": file_size,
                        "options": options
                    },
                    headers=self.headers
                )

                response.raise_for_status()
                result = response.json()

                logger.info(
                    f"Document processed successfully: "
                    f"{result.get('metadata', {}).get('pages', 'N/A')} pages, "
                    f"{len(result.get('content', '')):,} chars"
                )

                return result

        except httpx.ConnectError as e:
            logger.error(f"Could not connect to document processor: {e}")
            return await self._fallback_processing(signed_url, file_type)

        except httpx.TimeoutException as e:
            logger.error(f"Document processing timed out: {e}")
            raise

        except httpx.HTTPStatusError as e:
            logger.error(f"Document processing failed: {e.response.status_code} - {e.response.text}")

            # If it's a client error, don't retry
            if 400 <= e.response.status_code < 500:
                raise

            # For server errors, try fallback
            return await self._fallback_processing(signed_url, file_type)

        except Exception as e:
            logger.error(f"Unexpected error during document processing: {e}")
            return await self._fallback_processing(signed_url, file_type)

    async def _fallback_processing(
        self,
        signed_url: str,
        file_type: str
    ) -> dict[str, Any]:
        """
        Fallback processing when document processor is unavailable.
        Uses simplified extraction with PDFplumber or basic text extraction.
        """
        logger.warning(f"Using fallback processing for {file_type} document")

        # For now, return a simple structure
        # In production, this could use PDFplumber or other lightweight libraries
        return {
            "status": "fallback",
            "content": "[Document content unavailable - processor service offline]",
            "metadata": {
                "file_type": file_type,
                "processing_method": "fallback",
                "error": "Document processor service unavailable"
            },
            "warnings": ["Document processed with fallback method - limited extraction"]
        }

    async def get_capabilities(self) -> dict[str, Any] | None:
        """Get the capabilities of the document processor service."""
        try:
            headers = {}
            api_key = getattr(settings, 'document_processor_api_key', None)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health", headers=headers)
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get document processor capabilities: {e}")
            return None


# Global client instance
document_processor_client = DocumentProcessorClient()
