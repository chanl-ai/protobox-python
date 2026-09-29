"""Text parser for plain text and markdown files."""

import os
from typing import Dict, Any
from datetime import datetime, timezone
from loguru import logger

from parsers.base_parser import BaseParser
from models import ParsedDocument


class TextParser(BaseParser):
    """Parser for plain text and markdown files."""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.txt', 'txt', '.md', 'md', '.text', 'text'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB max for text files
    
    async def parse(
        self, 
        file_path: str,
        encoding: str = 'utf-8',
        **kwargs
    ) -> ParsedDocument:
        """
        Parse text/markdown file.
        
        Args:
            file_path: Path to text file
            encoding: Text encoding (default: utf-8)
            
        Returns:
            ParsedDocument with extracted content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Text file not found: {file_path}")
        
        start_time = datetime.now(timezone.utc)
        file_size = os.path.getsize(file_path)
        
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
        
        try:
            logger.info(f"Starting text parsing ({file_size:,} bytes)")
            
            # Read file content
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # Count lines and words
            lines = content.split('\n')
            words = content.split()
            
            # Extract metadata
            metadata = {
                "file_size": file_size,
                "encoding": encoding,
                "lines": len(lines),
                "words": len(words),
                "characters": len(content),
                "file_extension": os.path.splitext(file_path)[1],
            }
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Text parsing complete: {len(lines)} lines, "
                f"{len(words)} words in {processing_time:.2f}s"
            )
            
            return ParsedDocument(
                content=content,
                metadata=metadata,
                processing_time=processing_time
            )
            
        except UnicodeDecodeError:
            # Try with different encoding
            logger.warning(f"Failed to decode with {encoding}, trying latin-1")
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                
                return ParsedDocument(
                    content=content,
                    metadata={
                        "file_size": file_size,
                        "encoding": "latin-1",
                        "lines": len(content.split('\n')),
                        "words": len(content.split()),
                        "characters": len(content),
                    },
                    processing_time=(datetime.now(timezone.utc) - start_time).total_seconds()
                )
            except Exception as e:
                logger.error(f"Failed to parse text file with fallback encoding: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to parse text file: {e}")
            raise