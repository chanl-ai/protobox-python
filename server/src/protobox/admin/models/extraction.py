"""Unified extraction model for all data sources."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExtractionMethod(str, Enum):
    """Methods used for content extraction."""
    TEXT = "text"
    OCR = "ocr"
    HYBRID = "hybrid"
    TABLE_EXTRACTION = "table_extraction"
    API = "api"
    SCRAPING = "scraping"
    FAILED = "failed"
    SKIPPED = "skipped"


class ContentType(str, Enum):
    """Types of extracted content."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    METADATA = "metadata"
    HEADING = "heading"
    LIST = "list"
    CODE = "code"
    FORMULA = "formula"


class ImageMetadata(BaseModel):
    """Metadata for extracted images."""
    page_number: int | None = None
    image_index: int
    width: int | None = None
    height: int | None = None
    file_extension: str = "png"
    size_bytes: int | None = None
    image_path: str | None = None
    alt_text: str | None = None
    caption: str | None = None
    ocr_text: str | None = None
    ocr_confidence: float | None = None
    extraction_method: ExtractionMethod = ExtractionMethod.TEXT


class TableMetadata(BaseModel):
    """Metadata for extracted tables."""
    page_number: int | None = None
    table_index: int
    rows: int
    columns: int
    has_headers: bool = False
    extraction_confidence: float | None = None
    extraction_method: ExtractionMethod = ExtractionMethod.TABLE_EXTRACTION


class ContentBlock(BaseModel):
    """Individual content block with metadata."""
    content: str
    content_type: ContentType = ContentType.TEXT
    page_number: int | None = None
    position: dict[str, Any] | None = None  # x, y, width, height
    confidence: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_method: ExtractionMethod = ExtractionMethod.TEXT


class PageExtraction(BaseModel):
    """Extraction data for a single page."""
    page_number: int
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    images: list[ImageMetadata] = Field(default_factory=list)
    tables: list[TableMetadata] = Field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def text_content(self) -> str:
        """Get all text content combined."""
        text_blocks = [block.content for block in self.content_blocks
                      if block.content_type == ContentType.TEXT]
        return "\n".join(text_blocks)

    @property
    def has_meaningful_content(self) -> bool:
        """Check if page has meaningful extractable content."""
        return (len(self.text_content.strip()) > 20 or
                len(self.images) > 0 or
                len(self.tables) > 0)


class DocumentStructure(BaseModel):
    """Document structure information."""
    headings: list[dict[str, Any]] = Field(default_factory=list)
    sections: list[dict[str, Any]] = Field(default_factory=list)
    outline: dict[str, Any] = Field(default_factory=dict)
    reading_order: list[int] = Field(default_factory=list)  # Page numbers in reading order


class UnifiedExtractionResult(BaseModel):
    """Unified result model for all document types."""

    # Source information
    source_path: str
    source_type: str  # pdf, docx, url, etc.
    file_size: int | None = None

    # Content
    pages: list[PageExtraction] = Field(default_factory=list)
    full_text_content: str = ""

    # Document-level metadata
    document_metadata: dict[str, Any] = Field(default_factory=dict)
    structure: DocumentStructure = Field(default_factory=DocumentStructure)

    # Extraction statistics
    total_pages: int = 0
    total_text_chars: int = 0
    total_images: int = 0
    total_tables: int = 0
    pages_with_content: int = 0

    # Processing information
    extraction_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processing_time_seconds: float | None = None
    parser_version: str = "unified_v1"
    extraction_methods_used: list[ExtractionMethod] = Field(default_factory=list)

    # Quality metrics
    text_coverage_ratio: float = 0.0  # Pages with text / total pages
    extraction_success_ratio: float = 0.0  # Successfully processed pages / total pages
    average_confidence: float = 0.0

    # Warnings and errors
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def finalize_extraction(self):
        """Calculate final statistics and content."""
        self.total_pages = len(self.pages)

        # Combine all text content
        text_parts = []
        total_images = 0
        total_tables = 0
        pages_with_content = 0
        methods_used = set()
        confidences = []

        for page in self.pages:
            if page.has_meaningful_content:
                pages_with_content += 1

                # Add page header
                text_parts.append(f"# Page {page.page_number}")

                # Add text content
                if page.text_content:
                    text_parts.append(page.text_content)

                # Add table content
                for i, table in enumerate(page.tables):
                    text_parts.append(f"\n## Table {i+1} (Page {page.page_number})")
                    # Table content should be in content_blocks
                    table_blocks = [block for block in page.content_blocks
                                  if block.content_type == ContentType.TABLE]
                    if table_blocks:
                        text_parts.append(table_blocks[0].content)

                # Track statistics
                total_images += len(page.images)
                total_tables += len(page.tables)

                # Track extraction methods and confidence
                for block in page.content_blocks:
                    methods_used.add(block.extraction_method)
                    confidences.append(block.confidence)

        self.full_text_content = "\n\n".join(text_parts)
        self.total_text_chars = len(self.full_text_content)
        self.total_images = total_images
        self.total_tables = total_tables
        self.pages_with_content = pages_with_content
        self.extraction_methods_used = list(methods_used)

        # Calculate quality metrics
        self.text_coverage_ratio = pages_with_content / max(self.total_pages, 1)
        self.extraction_success_ratio = pages_with_content / max(self.total_pages, 1)
        self.average_confidence = sum(confidences) / max(len(confidences), 1)



    def get_content_by_type(self, content_type: ContentType) -> list[ContentBlock]:
        """Get all content blocks of a specific type."""
        result = []
        for page in self.pages:
            result.extend([block for block in page.content_blocks
                          if block.content_type == content_type])
        return result

    def get_page_content(self, page_number: int) -> PageExtraction | None:
        """Get content for a specific page."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


def create_content_block(
    content: str,
    content_type: ContentType = ContentType.TEXT,
    page_number: int | None = None,
    extraction_method: ExtractionMethod = ExtractionMethod.TEXT,
    confidence: float = 1.0,
    **metadata
) -> ContentBlock:
    """Helper function to create content blocks."""
    return ContentBlock(
        content=content,
        content_type=content_type,
        page_number=page_number,
        extraction_method=extraction_method,
        confidence=confidence,
        metadata=metadata
    )


def create_table_metadata(
    table_data: list[list[str]],
    page_number: int | None = None,
    table_index: int = 0,
    extraction_method: ExtractionMethod = ExtractionMethod.TABLE_EXTRACTION
) -> TableMetadata:
    """Helper function to create table metadata."""
    rows = len(table_data)
    columns = len(table_data[0]) if table_data else 0

    # Simple header detection
    has_headers = False
    if rows > 1 and columns > 0:
        first_row = table_data[0]
        has_headers = any(str(cell).strip() and not str(cell).isdigit()
                         for cell in first_row)

    return TableMetadata(
        page_number=page_number,
        table_index=table_index,
        rows=rows,
        columns=columns,
        has_headers=has_headers,
        extraction_method=extraction_method
    )
