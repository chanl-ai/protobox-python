"""Knowledge Base MCP Tool for assistant integration."""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from protobox.admin.database.connection import get_database_connection
from protobox.admin.models.knowledge_base import SearchFilters, SearchRequest
from protobox.admin.services.embedding_service import EmbeddingService
from protobox.admin.services.knowledge_base_service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class KnowledgeSearchParams(BaseModel):
    """Parameters for knowledge base search tool."""

    query: str = Field(..., description="Search query for knowledge base")
    max_results: int = Field(
        default=5, ge=1, le=10, description="Maximum number of results to return"
    )
    min_relevance: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum relevance score")
    categories: list[str] | None = Field(default=None, description="Filter by categories")
    tags: list[str] | None = Field(default=None, description="Filter by tags")
    search_type: str = Field(
        default="hybrid", description="Search type: semantic, keyword, or hybrid"
    )


class KnowledgeSearchResult(BaseModel):
    """Knowledge base search result for MCP response."""

    title: str
    question: str | None = None
    answer: str | None = None
    content_snippet: str
    category: str
    tags: list[str]
    relevance_score: float
    url: str
    entry_id: str


class KnowledgeBaseTool:
    """MCP tool for searching knowledge base content."""

    def __init__(self):
        self.name = "search_knowledge_base"
        self.description = "Search the workspace knowledge base for relevant information"
        self._kb_service: KnowledgeBaseService | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        """Get tool parameters schema."""
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for knowledge base",
                    "minLength": 1,
                    "maxLength": 500,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score (0.0-1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.6,
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by categories",
                    "maxItems": 5,
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags",
                    "maxItems": 10,
                },
                "search_type": {
                    "type": "string",
                    "enum": ["semantic", "keyword", "hybrid"],
                    "description": "Search type",
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        }

    async def _get_kb_service(self) -> KnowledgeBaseService:
        """Get or initialize knowledge base service."""
        if not self._kb_service:
            # Initialize database connection
            db_connection = get_database_connection()
            database = db_connection.database

            # Initialize embedding service
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OpenAI API key not configured for knowledge base")

            embedding_service = EmbeddingService(api_key=openai_api_key)
            self._kb_service = KnowledgeBaseService(database, embedding_service)

        return self._kb_service

    async def execute(self, workspace_id: str, **kwargs) -> dict[str, Any]:
        """Execute knowledge base search."""
        try:
            # Validate parameters
            params = KnowledgeSearchParams(**kwargs)

            # Get knowledge base service
            kb_service = await self._get_kb_service()

            # Create search request
            filters = SearchFilters(
                categories=params.categories,
                tags=params.tags,
                min_relevance=params.min_relevance,
                max_results=params.max_results,
                search_type=params.search_type,
            )

            search_request = SearchRequest(query=params.query, filters=filters)

            # Perform search
            search_response = await kb_service.search_entries(workspace_id, search_request)

            # Format results for MCP
            results = []
            for result in search_response.results:
                formatted_result = KnowledgeSearchResult(
                    title=result.title,
                    question=result.question,
                    answer=result.answer,
                    content_snippet=result.content_snippet,
                    category=result.category,
                    tags=result.tags,
                    relevance_score=result.relevance_score,
                    url=result.url,
                    entry_id=result.entry_id,
                )
                results.append(formatted_result.dict())

            logger.info(f"Knowledge base search: '{params.query}' returned {len(results)} results")

            return {
                "success": True,
                "results": results,
                "total_results": search_response.total_results,
                "search_time_ms": search_response.search_time_ms,
                "search_type": search_response.search_type,
                "query": params.query,
                "message": (
                    f"Found {len(results)} knowledge base entries"
                    if results
                    else "No knowledge base entries found"
                ),
            }

        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "total_results": 0,
                "message": "Knowledge base search failed",
            }

    def to_mcp_tool_definition(self) -> dict[str, Any]:
        """Convert to MCP tool definition format."""
        return {"name": self.name, "description": self.description, "inputSchema": self.parameters}


# Global instance for MCP registration
knowledge_base_tool = KnowledgeBaseTool()
