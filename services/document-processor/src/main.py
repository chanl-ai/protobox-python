"""Document Processing Service - Main FastAPI Application."""

import os
import secrets
import tempfile
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from loguru import logger

from config import settings
from parsers import PDFParser, DocxParser, ExcelParser, TextParser
from models import ProcessRequest, ProcessResponse, HealthResponse

# Configure logging
logger.add("logs/document-processor.log", rotation="10 MB", retention="7 days")

app = FastAPI(
    title="Document Processor Service",
    description="Microservice for processing PDF, DOCX, XLSX and other documents",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None,
)

# Security scheme - optional for development
security = HTTPBearer(auto_error=False)

def verify_api_key(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> bool:
    """Verify API key from Authorization header."""
    if not settings.api_key:
        # This service downloads whatever URL it is sent, so it never runs without a key.
        raise HTTPException(status_code=503, detail="Service is not configured: API_KEY is unset")
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )
    
    if not secrets.compare_digest(authorization.credentials, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return True


class DocumentProcessor:
    """Main document processing orchestrator."""
    
    def __init__(self):
        self.parsers = {
            "pdf": PDFParser(),
            "docx": DocxParser(),
            "xlsx": ExcelParser(),
            "txt": TextParser(),
            "md": TextParser(),
        }
        self.temp_dir = tempfile.mkdtemp(prefix="doc-processor-")
        logger.info(f"Document processor initialized with temp dir: {self.temp_dir}")
    
    async def process_from_url(
        self, 
        signed_url: str, 
        file_type: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a document from a signed S3 URL.
        
        Args:
            signed_url: Pre-signed S3 URL for document download
            file_type: File extension (pdf, docx, xlsx, etc.)
            options: Processing options (OCR, table extraction, etc.)
        
        Returns:
            Extracted content and metadata
        """
        import time
        
        options = options or {}
        temp_file_path = None
        start_time = time.time()
        processing_id = os.urandom(4).hex()
        
        logger.info(f"🚀 [ID:{processing_id}] Starting document processing - Type: {file_type}, Options: {options}")
        
        try:
            # Step 1: Download file from signed URL
            download_start = time.time()
            logger.info(f"📥 [ID:{processing_id}] Downloading document from signed URL")
            temp_file_path = await self._download_from_url(signed_url, file_type)
            download_time = time.time() - download_start
            
            # Get file size for logging
            file_size = os.path.getsize(temp_file_path)
            logger.info(f"✅ [ID:{processing_id}] Download complete - Size: {file_size:,} bytes, Time: {download_time:.2f}s")
            
            # Step 2: Select appropriate parser
            parser = self.parsers.get(file_type.lower())
            if not parser:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            logger.info(f"🔧 [ID:{processing_id}] Using parser: {parser.__class__.__name__}")
            
            # Step 3: Process document
            processing_start = time.time()
            logger.info(f"⚙️ [ID:{processing_id}] Processing document with options: {options}")
            result = await parser.parse(temp_file_path, **options)
            processing_time = time.time() - processing_start
            
            # Step 4: Prepare results with detailed metrics
            total_time = time.time() - start_time
            content_length = len(result.content) if result.content else 0
            
            logger.info(
                f"🎉 [ID:{processing_id}] Processing complete - "
                f"Content: {content_length:,} chars, "
                f"Processing: {processing_time:.2f}s, "
                f"Total: {total_time:.2f}s"
            )
            
            # Enhanced metadata with timing
            enhanced_metadata = result.metadata.copy() if result.metadata else {}
            enhanced_metadata.update({
                'processing_id': processing_id,
                'file_size_bytes': file_size,
                'download_time_seconds': round(download_time, 2),
                'processing_time_seconds': round(processing_time, 2),
                'total_time_seconds': round(total_time, 2),
                'content_length': content_length,
                'parser_used': parser.__class__.__name__,
                'processing_options': options
            })
            
            return {
                "status": "success",
                "content": result.content,
                "metadata": enhanced_metadata,
                "processing_time": round(total_time, 2),
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(
                f"❌ [ID:{processing_id}] Processing failed after {total_time:.2f}s - "
                f"Error: {str(e)[:200]}{'...' if len(str(e)) > 200 else ''}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document [ID:{processing_id}]: {str(e)}"
            )
        finally:
            # Clean up temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {e}")
    
    async def _download_from_url(self, signed_url: str, file_type: str) -> str:
        """Download file from signed URL to temp location."""
        temp_file_path = os.path.join(self.temp_dir, f"doc_{os.urandom(8).hex()}.{file_type}")
        
        try:
            async with httpx.AsyncClient(timeout=settings.download_timeout) as client:
                logger.debug(f"📡 Starting download from signed URL (timeout: {settings.download_timeout}s)")
                response = await client.get(signed_url)
                response.raise_for_status()
                
                content_length = len(response.content)
                logger.debug(f"📦 Received {content_length:,} bytes, writing to {temp_file_path}")
                
                with open(temp_file_path, "wb") as f:
                    f.write(response.content)
                
                logger.debug(f"💾 File saved successfully: {temp_file_path}")
                return temp_file_path
                
        except httpx.TimeoutException as e:
            logger.error(f"⏰ Download timeout after {settings.download_timeout}s: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"🚫 HTTP error {e.response.status_code} during download: {e}")
            raise
        except Exception as e:
            logger.error(f"💥 Unexpected download error: {e}")
            raise


# Initialize document processor
doc_processor = DocumentProcessor()


@app.post("/v1/process", response_model=ProcessResponse)
async def process_document(request: ProcessRequest, authenticated: bool = Depends(verify_api_key)) -> ProcessResponse:
    """
    Process a document from a signed S3 URL.
    
    The URL should be pre-signed by the main backend with appropriate expiration.
    """
    logger.info(f"Processing request for {request.file_type} document")
    
    # Validate file size if provided
    if request.file_size and request.file_size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size {request.file_size} exceeds maximum {settings.max_file_size}"
        )
    
    # Process document
    result = await doc_processor.process_from_url(
        signed_url=request.signed_url,
        file_type=request.file_type,
        options=request.options or {}
    )
    
    return ProcessResponse(
        status="success",
        content=result["content"],
        metadata=result["metadata"],
        processing_time=result.get("processing_time"),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint with capabilities information."""
    return HealthResponse(
        status="healthy",
        capabilities=list(doc_processor.parsers.keys()),
        supported_formats={
            "documents": ["pdf", "docx", "txt", "md"],
            "spreadsheets": ["xlsx", "csv"],
            "ocr": ["pdf", "images"],
        },
        max_file_size=settings.max_file_size,
        version="0.1.0",
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Document Processor",
        "version": "0.1.0",
        "docs": "/docs" if settings.environment == "development" else None,
    }


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info(f"Document Processor Service starting in {settings.environment} mode")
    logger.info(f"Max file size: {settings.max_file_size:,} bytes")
    logger.info(f"Processing timeout: {settings.processing_timeout}s")
    logger.info(f"Available parsers: {list(doc_processor.parsers.keys())}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Document Processor Service shutting down")
    # Clean up temp directory
    if os.path.exists(doc_processor.temp_dir):
        try:
            import shutil
            shutil.rmtree(doc_processor.temp_dir)
            logger.info(f"Cleaned up temp directory: {doc_processor.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )


@app.exception_handler(httpx.RequestError)
async def request_error_handler(request, exc):
    """Handle download errors."""
    return JSONResponse(
        status_code=502,
        content={"error": f"Failed to download document: {str(exc)}"}
    )