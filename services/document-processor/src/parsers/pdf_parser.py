"""PDF parser with PyMuPDF and PDFplumber."""

import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import pymupdf
import pdfplumber
from loguru import logger

from parsers.base_parser import BaseParser
from models import ParsedDocument
from config import settings


class PDFParser(BaseParser):
    """PDF parser using PyMuPDF (primary) and PDFplumber (for tables)."""
    
    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.pdf', 'pdf'}
        self.min_text_threshold = 5  # Lower threshold for testing
        self.max_pages = settings.max_pages_per_document
    
    async def parse(
        self, 
        file_path: str,
        use_ocr: bool = True,
        extract_tables: bool = True,
        extract_images: bool = False,
        **kwargs
    ) -> ParsedDocument:
        """
        Parse PDF document with PyMuPDF and PDFplumber.
        
        Args:
            file_path: Path to PDF file
            use_ocr: Whether to use OCR for scanned pages
            extract_tables: Whether to extract tables
            extract_images: Whether to extract images
            
        Returns:
            ParsedDocument with extracted content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        start_time = datetime.now(timezone.utc)
        file_size = os.path.getsize(file_path)
        
        try:
            logger.info(f"Starting PDF parsing ({file_size:,} bytes)")
            
            # Extract content
            loop = asyncio.get_event_loop()
            content, metadata = await self._extract_content(
                file_path, 
                use_ocr, 
                extract_tables,
                extract_images,
                loop
            )
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"PDF parsing complete: {metadata.get('pages', 0)} pages, "
                f"{len(content):,} chars in {processing_time:.2f}s"
            )
            
            return ParsedDocument(
                content=content,
                metadata={
                    **metadata,
                    "file_size": file_size,
                    "processing_method": "pymupdf_pdfplumber",
                    "ocr_enabled": use_ocr,
                    "tables_extracted": extract_tables,
                },
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise
    
    async def _extract_content(
        self, 
        file_path: str,
        use_ocr: bool,
        extract_tables: bool,
        extract_images: bool,
        loop
    ) -> tuple[str, Dict[str, Any]]:
        """Extract content from PDF using hybrid approach."""
        
        # Open with PyMuPDF
        doc = await loop.run_in_executor(None, pymupdf.open, file_path)
        
        try:
            page_count = len(doc)
            if page_count > self.max_pages:
                logger.warning(f"PDF has {page_count} pages, limiting to {self.max_pages}")
                page_count = min(page_count, self.max_pages)
            
            all_text = []
            tables_found = 0
            images_found = 0
            
            # Also open with PDFplumber for tables
            plumber_doc = None
            if extract_tables:
                plumber_doc = await loop.run_in_executor(None, pdfplumber.open, file_path)
            
            try:
                for page_num in range(page_count):
                    # Extract text with PyMuPDF
                    page = doc[page_num]
                    text = await loop.run_in_executor(None, page.get_text)
                    
                    if text and text.strip():
                        text_content = text.strip()
                        logger.debug(f"Page {page_num + 1}: {len(text_content)} chars - '{text_content[:100]}{'...' if len(text_content) > 100 else ''}'")
                        if len(text_content) > self.min_text_threshold:
                            all_text.append(text_content)
                        elif len(text_content) > 0:
                            # Include short text anyway but mark it
                            all_text.append(f"[SHORT] {text_content}")
                    
                    # Extract tables with PDFplumber
                    if extract_tables and plumber_doc and page_num < len(plumber_doc.pages):
                        tables = await loop.run_in_executor(
                            None, 
                            plumber_doc.pages[page_num].extract_tables
                        )
                        if tables:
                            tables_found += len(tables)
                            for table in tables:
                                # Convert table to text
                                table_text = self._format_table(table)
                                if table_text:
                                    all_text.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
                    
                    # Count images
                    if extract_images:
                        images = page.get_images()
                        images_found += len(images)
                
            finally:
                if plumber_doc:
                    plumber_doc.close()
            
            # Extract metadata
            metadata = {
                "pages": page_count,
                "tables": tables_found,
                "images": images_found,
            }
            
            # Try to get document metadata
            try:
                doc_metadata = doc.metadata
                if doc_metadata:
                    metadata.update({
                        "title": doc_metadata.get("title", ""),
                        "author": doc_metadata.get("author", ""),
                        "subject": doc_metadata.get("subject", ""),
                        "keywords": doc_metadata.get("keywords", ""),
                        "creator": doc_metadata.get("creator", ""),
                        "producer": doc_metadata.get("producer", ""),
                    })
            except Exception as e:
                logger.warning(f"Could not extract PDF metadata: {e}")
            
            return "\n\n".join(all_text), metadata
            
        finally:
            doc.close()
    
    def _format_table(self, table: List[List]) -> str:
        """Format table data as readable text."""
        if not table:
            return ""
        
        lines = []
        for row in table:
            if row and any(cell for cell in row if cell):
                lines.append(" | ".join(str(cell or "") for cell in row))
        
        return "\n".join(lines) if lines else ""