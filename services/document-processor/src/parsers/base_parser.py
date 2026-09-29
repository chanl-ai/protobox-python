"""Base parser class for all document parsers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import time
from loguru import logger
from models import ParsedDocument


class BaseParser(ABC):
    """Abstract base class for document parsers."""
    
    def __init__(self):
        self.supported_extensions = set()
    
    @abstractmethod
    async def parse(
        self, 
        file_path: str, 
        **kwargs
    ) -> ParsedDocument:
        """
        Parse a document and extract content.
        
        Args:
            file_path: Path to the document file
            **kwargs: Additional parsing options
            
        Returns:
            ParsedDocument with extracted content and metadata
        """
        pass
    
    def is_supported(self, file_extension: str) -> bool:
        """Check if file extension is supported."""
        return file_extension.lower() in self.supported_extensions
    
    async def _measure_time(self, func, *args, **kwargs):
        """Measure execution time of an async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        processing_time = time.time() - start_time
        return result, processing_time