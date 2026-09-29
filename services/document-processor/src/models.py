"""Request and Response models for Document Processor Service."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    """Request model for document processing."""
    
    signed_url: str = Field(
        ..., 
        description="Pre-signed S3 URL for document download"
    )
    file_type: str = Field(
        ..., 
        description="File extension (pdf, docx, xlsx, etc.)"
    )
    file_size: Optional[int] = Field(
        None, 
        description="File size in bytes for validation"
    )
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Processing options (OCR, table extraction, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "signed_url": "https://s3.amazonaws.com/bucket/file.pdf?signature=...",
                "file_type": "pdf",
                "file_size": 1048576,
                "options": {
                    "use_ocr": True,
                    "extract_tables": True,
                    "extract_images": False
                }
            }
        }


class ProcessResponse(BaseModel):
    """Response model for document processing."""
    
    status: str = Field(..., description="Processing status")
    content: str = Field(..., description="Extracted text content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Document metadata and statistics"
    )
    processing_time: Optional[float] = Field(
        None, 
        description="Processing time in seconds"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Processing warnings if any"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "content": "Extracted document text...",
                "metadata": {
                    "pages": 10,
                    "words": 5000,
                    "tables": 2,
                    "images": 5,
                    "author": "John Doe",
                    "title": "Document Title"
                },
                "processing_time": 2.5,
                "warnings": []
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    capabilities: List[str] = Field(
        ..., 
        description="Supported file types"
    )
    supported_formats: Dict[str, List[str]] = Field(
        ..., 
        description="Categorized supported formats"
    )
    max_file_size: int = Field(
        ..., 
        description="Maximum file size in bytes"
    )
    version: str = Field(..., description="Service version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "capabilities": ["pdf", "docx", "xlsx", "txt", "md"],
                "supported_formats": {
                    "documents": ["pdf", "docx", "txt", "md"],
                    "spreadsheets": ["xlsx", "csv"],
                    "ocr": ["pdf", "images"]
                },
                "max_file_size": 52428800,
                "version": "0.1.0"
            }
        }


class ParsedDocument(BaseModel):
    """Internal model for parsed document data."""
    
    content: str
    metadata: Dict[str, Any]
    processing_time: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)