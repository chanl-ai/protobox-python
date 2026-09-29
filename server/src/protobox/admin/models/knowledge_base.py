"""Knowledge Base models for ProtoBox admin API."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Source types for knowledge base content."""
    FILE = "file"
    URL = "url"
    TEXT = "text"


class FilterCategory(str, Enum):
    """Filter categories for knowledge base queries."""
    DOCUMENTS = "documents"
    WEB = "web"
    INTEGRATIONS = "integrations"
    TEXT = "text"


class SearchType(str, Enum):
    """Search types for knowledge base queries."""
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class ProcessingStatus(str, Enum):
    """Processing status for knowledge documents."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some content processed successfully, some failed


class ChunkingStrategy(str, Enum):
    """Chunking strategies for knowledge base content."""
    SMART = "smart"  # Topic-based clustering (default)
    FAQ_OPTIMIZATION = "faq_optimization"  # Q&A generation
    TOPIC_HEADERS = "topic_headers"  # Section summarization
    SUMMARIZE = "summarize"  # Key points extraction


class ProcessedChunk(BaseModel):
    """Processed chunk stored separately for fast RAG retrieval."""
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    document_id: ObjectId = Field(..., description="Reference to parent knowledge document")
    chunk_index: int = Field(..., description="Order in parent document")
    content: str = Field(..., description="Chunk content")
    chunk_type: str = Field(default="content", description="content, question, answer, summary")

    # Embeddings
    embedding: list[float] = Field(..., description="Pre-computed embedding vector")
    embedding_model: str = Field(default="text-embedding-3-small")
    token_count: int = Field(default=0)

    # Metadata
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    source_metadata: dict[str, Any] = Field(default_factory=dict)  # page_number, url, section_title, etc.

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: str}
        arbitrary_types_allowed = True


class KnowledgeDocument(BaseModel):
    """Document-oriented knowledge source with processing metadata."""
    id: ObjectId = Field(default_factory=ObjectId, alias="_id")
    workspace_id: ObjectId

    # Document metadata
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    category: str = Field(default="general")
    tags: list[str] = Field(default_factory=list, max_items=10)

    # Source information
    source_type: SourceType = Field(..., description="Type of source: file, url, or text")
    original_source: str = Field(..., description="File path in Tigris, URL, or raw text content")
    file_size: int | None = Field(None, description="Original file size in bytes")
    filename: str | None = Field(None, description="Original filename if from file upload")
    mime_type: str | None = Field(None, description="MIME type of original file")

    # Processing status and results
    processing_status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    processing_error: str | None = Field(None, description="Error message if processing failed")
    processing_warnings: list[str] = Field(default_factory=list, description="Non-fatal processing warnings")
    total_chunks: int = Field(default=0, description="Number of processed chunks")
    failed_pages: list[str] = Field(default_factory=list, description="URLs/pages that failed to process")
    processing_metadata: dict[str, Any] = Field(default_factory=dict, description="Processing details and metrics")

    # Processing configuration
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.SMART)
    chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)

    # Status and metadata
    status: str = Field(default="active")  # active, archived, deleted
    author_id: str

    # Analytics
    chunk_count: int = Field(default=0, description="Current number of processed chunks")
    last_queried: datetime | None = Field(None, description="Last time this document was queried")
    query_count: int = Field(default=0, description="Number of times this document was queried")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = Field(None, description="When processing was completed")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str, datetime: str}
        arbitrary_types_allowed = True


# Document creation and update schemas
class KnowledgeDocumentCreate(BaseModel):
    """Schema for creating knowledge documents."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    category: str = Field(default="general")
    tags: list[str] = Field(default_factory=list, max_items=10)

    # Source information
    source_type: SourceType = Field(..., description="Type of source: file, url, or text")

    # For URL sources
    url: str | None = Field(None, description="URL to scrape (required for URL source type)")
    crawl_depth: int = Field(default=3, ge=1, le=5, description="Crawling depth for URL sources")

    # For text sources
    content: str | None = Field(None, description="Raw text content (required for TEXT source type)")

    # Processing options
    chunking_strategy: ChunkingStrategy = Field(default=ChunkingStrategy.SMART)
    chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)


class KnowledgeDocumentUpdate(BaseModel):
    """Schema for updating knowledge documents."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    category: str | None = None
    tags: list[str] | None = None
    status: str | None = None
    chunking_strategy: ChunkingStrategy | None = None
    chunk_size: int | None = Field(None, ge=100, le=2000)
    chunk_overlap: int | None = Field(None, ge=0, le=500)


# Search models
class SearchResult(BaseModel):
    """Knowledge base search result."""
    document_id: str
    chunk_id: str

    # Content
    document_title: str
    content_snippet: str
    chunk_type: str
    category: str
    tags: list[str]

    # Relevance
    relevance_score: float
    search_type: str  # semantic, keyword, hybrid

    # Metadata
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    token_count: int
    chunk_index: int


class QueryFilters(BaseModel):
    """Filters for knowledge base queries."""
    categories: FilterCategory | None = None
    tags: list[str] | None = None
    document_ids: list[str] | None = None
    min_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    max_results: int = Field(default=10, ge=1, le=50)
    search_type: SearchType = Field(default=SearchType.HYBRID)  # semantic, keyword, hybrid


class QueryRequest(BaseModel):
    """Query request for searching knowledge chunks."""
    query: str = Field(..., min_length=1, max_length=500)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    include_context: bool = Field(default=True)


# Response models
class KnowledgeDocumentResponse(BaseModel):
    """Response model for knowledge documents."""
    id: str
    workspace_id: str
    title: str
    description: str | None
    category: str
    tags: list[str]
    source_type: SourceType
    filename: str | None
    processing_status: ProcessingStatus
    processing_error: str | None
    total_chunks: int
    chunk_count: int
    status: str
    author_id: str
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None


class ProcessedChunkResponse(BaseModel):
    """Response model for processed chunks."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    chunk_type: str
    token_count: int
    confidence_score: float
    source_metadata: dict[str, Any]
    created_at: datetime


class ChunkListResponse(BaseModel):
    """Response model for chunk listing."""
    chunks: list[ProcessedChunkResponse]
    total_chunks: int
    document_id: str
    document_title: str


class QueryResponse(BaseModel):
    """Response model for query results."""
    results: list[SearchResult]
    total_results: int
    search_time_ms: int
    search_type: str
    query: str
    filters: QueryFilters


class UploadResponse(BaseModel):
    """Response model for file uploads."""
    document_id: str
    task_id: str
    message: str
    filename: str | None
    status: ProcessingStatus
