"""Base parser class for document processing."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from protobox.admin.config import settings

logger = logging.getLogger(__name__)


class ParsedDocument:
    """Container for parsed document content and metadata."""

    def __init__(self, content: str, metadata: dict[str, Any]):
        self.content = content
        self.metadata = metadata
        self.parsed_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'parsed_at': self.parsed_at.isoformat()
        }


class BaseParser(ABC):
    """Base class for all document parsers."""

    def __init__(self):
        self.supported_extensions = set()
        self.parser_name = self.__class__.__name__
        self.processing_timeout = settings.kb_source_processing_timeout

    @abstractmethod
    async def parse(self, file_path: str, **kwargs) -> ParsedDocument:
        """
        Parse a document from file path.
        
        Args:
            file_path: Path to the file to parse
            **kwargs: Additional parser-specific options
            
        Returns:
            ParsedDocument with content and metadata
        """
        pass

    async def parse_bytes(self, file_bytes: bytes, filename: str, **kwargs) -> ParsedDocument:
        """
        Parse a document from bytes.
        
        Args:
            file_bytes: File content as bytes
            filename: Original filename for context
            **kwargs: Additional parser-specific options
            
        Returns:
            ParsedDocument with content and metadata
        """
        # Default implementation saves to temp file and calls parse()
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name

        try:
            return await self.parse(temp_file_path, **kwargs)
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")

    def is_supported(self, filename: str) -> bool:
        """Check if file is supported by this parser."""
        from pathlib import Path
        return Path(filename).suffix.lower() in self.supported_extensions

    def _create_base_metadata(self, filename: str, file_size: int | None = None) -> dict[str, Any]:
        """Create base metadata for parsed documents."""
        from pathlib import Path

        return {
            'parser': self.parser_name,
            'filename': filename,
            'file_extension': Path(filename).suffix.lower(),
            'file_size': file_size,
            'parsing_timestamp': datetime.now(UTC).isoformat()
        }

    async def _run_with_timeout(self, coro, timeout_seconds: int | None = None) -> Any:
        """
        Run a coroutine with timeout protection.
        
        Args:
            coro: Coroutine to run
            timeout_seconds: Timeout in seconds (uses default if None)
            
        Returns:
            Result of the coroutine
            
        Raises:
            asyncio.TimeoutError: If the operation times out
        """
        timeout = timeout_seconds or self.processing_timeout
        return await asyncio.wait_for(coro, timeout=timeout)

    def _handle_timeout_error(self, error: asyncio.TimeoutError, partial_data: dict[str, Any]) -> ParsedDocument:
        """
        Handle timeout errors by creating a partial result with available data.
        
        Args:
            error: The timeout error that occurred
            partial_data: Any data that was extracted before timeout
            
        Returns:
            ParsedDocument with partial content and error metadata
        """
        logger.warning(f"Parser {self.parser_name} timed out after {self.processing_timeout}s")

        # Create partial content
        partial_content = partial_data.get('content', '')
        if not partial_content:
            partial_content = f"[PARSING TIMEOUT] Content extraction timed out after {self.processing_timeout} seconds."

        # Update metadata with timeout information
        partial_data['parsing_error'] = f"Timeout after {self.processing_timeout}s"
        partial_data['parsing_status'] = 'partial'
        partial_data['timeout_occurred'] = True
        partial_data['processing_timeout'] = self.processing_timeout

        return ParsedDocument(partial_content, partial_data)
