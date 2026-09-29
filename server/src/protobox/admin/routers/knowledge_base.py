"""Knowledge Base API router - Document-oriented refactor."""

import os

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from loguru import logger
from protobox.admin.auth.dependencies import User, require_authentication
from protobox.admin.mixins.audit_mixin import AuditLoggerMixin
from protobox.admin.models.knowledge_base import (
    ChunkListResponse,
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    ProcessedChunkResponse,
    ProcessingStatus,
    QueryRequest,
    QueryResponse,
    SourceType,
    UploadResponse,
)
from protobox.admin.routers.audit import get_audit_service
from protobox.admin.routers.workspace import verify_workspace_access
from protobox.admin.services.audit_service import AuditService
from protobox.admin.services.knowledge_document_service import KnowledgeDocumentService
from protobox.admin.utils.validators import validate_object_id, validate_workspace_id

router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["knowledge-base"])


async def get_knowledge_document_service() -> KnowledgeDocumentService:
    """Dependency to get knowledge document service."""
    from protobox.admin.database.connection import get_database_connection
    from protobox.admin.services.embedding_service import EmbeddingService

    # Get database connection
    db_connection = get_database_connection()
    database = db_connection.database

    # Initialize embedding service
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base is unavailable: set OPENAI_API_KEY on the server"
        )

    embedding_service = EmbeddingService(api_key=openai_api_key)

    # Return knowledge document service
    return KnowledgeDocumentService(database, embedding_service)


@router.post("/upload", response_model=UploadResponse)
async def upload_knowledge_source(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    # File upload (optional)
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    file: UploadFile | None = File(None),
    # Form data for non-file sources
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: str = Form("general"),
    tags: str = Form(""),  # Comma-separated
    source_type: str = Form("file"),
    url: str | None = Form(None),
    content: str | None = Form(None),
    chunking_strategy: str = Form("smart"),
    chunk_size: int = Form(512),
    chunk_overlap: int = Form(50),
    # Services
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_authentication),
):
    """
    Upload and process a knowledge source.
    
    Supports:
    - File uploads (PDF, DOCX, Excel, HTML, Markdown, Text)
    - URL scraping
    - Raw text content
    """
    validate_workspace_id(workspace_id)

    # Parse source type
    try:
        source_type_enum = SourceType(source_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source type: {source_type}")

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

    try:
        if source_type_enum == SourceType.FILE:
            # Handle file upload
            if not file or not file.filename:
                raise HTTPException(status_code=400, detail="File is required for FILE source type")

            # Validate file
            if not kb_service.is_supported_file(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Supported: {', '.join(kb_service.get_supported_extensions())}"
                )

            if file.size and not kb_service.is_valid_file_size(file.size):
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {kb_service.get_max_file_size() // (1024*1024)}MB"
                )

            # Upload file to Tigris (temporary storage)
            file_content = await file.read()
            file_key = await kb_service.upload_file_to_tigris(
                file_content, file.filename, workspace_id, file.content_type
            )

            # Create document record
            doc_create = KnowledgeDocumentCreate(
                title=title or file.filename,
                description=description,
                category=category,
                tags=tag_list,
                source_type=source_type_enum,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            document = await kb_service.create_document(
                workspace_id=workspace_id,
                document_data=doc_create,
                user_id=current_user.id,
                file_key=file_key,
                filename=file.filename,
                file_size=file.size,
                mime_type=file.content_type
            )

        elif source_type_enum == SourceType.URL:
            # Handle URL source
            if not url:
                raise HTTPException(status_code=400, detail="URL is required for URL source type")

            doc_create = KnowledgeDocumentCreate(
                title=title or f"Web content from {url}",
                description=description,
                category=category,
                tags=tag_list,
                source_type=source_type_enum,
                url=url,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            document = await kb_service.create_document(
                workspace_id=workspace_id,
                document_data=doc_create,
                user_id=current_user.id,
                source_url=url
            )

        elif source_type_enum == SourceType.TEXT:
            # Handle raw text content
            if not content:
                raise HTTPException(status_code=400, detail="Content is required for TEXT source type")

            if not title:
                raise HTTPException(status_code=400, detail="Title is required for TEXT source type")

            doc_create = KnowledgeDocumentCreate(
                title=title,
                description=description,
                category=category,
                tags=tag_list,
                source_type=source_type_enum,
                content=content,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            document = await kb_service.create_document(
                workspace_id=workspace_id,
                document_data=doc_create,
                user_id=current_user.id,
                text_content=content
            )

        # Queue background processing
        task_id = await kb_service.queue_processing_task(
            document_id=str(document.id),
            workspace_id=workspace_id
        )

        # Start background processing
        background_tasks.add_task(
            kb_service.process_document_background,
            document_id=str(document.id),
            task_id=task_id
        )

        # Log audit entry
        await AuditLoggerMixin.audit_create(
            audit_service=audit_service,
            user_id=current_user.id,
            workspace_id=workspace_id,
            resource_type="knowledge_document",
            resource_id=str(document.id),
            resource_name=document.title,
            metadata={
                "source_type": document.source_type.value,
                "category": document.category,
                "tags": document.tags,
                "chunking_strategy": document.chunking_strategy.value,
                "task_id": task_id
            }
        )

        logger.info(f"Created knowledge document {document.id} with task {task_id}")

        return UploadResponse(
            document_id=str(document.id),
            task_id=task_id,
            message="Knowledge source uploaded and queued for processing",
            filename=getattr(file, 'filename', None) if file else None,
            status=document.processing_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload knowledge source: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload knowledge source")


@router.get("/{document_id}", response_model=ChunkListResponse)
async def get_knowledge_document(
    workspace_id: str,
    document_id: str,
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    skip: int = 0,
    limit: int = 50,
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
):
    """Get a knowledge document and its processed chunks."""
    validate_workspace_id(workspace_id)
    validate_object_id(document_id, "document ID")

    try:
        # Get document
        document = await kb_service.get_document(workspace_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Knowledge document not found")

        # Get chunks
        chunks = await kb_service.get_document_chunks(
            document_id=document_id,
            skip=skip,
            limit=limit
        )

        # Convert to response format
        chunk_responses = [
            ProcessedChunkResponse(
                id=str(chunk.id),
                document_id=str(chunk.document_id),
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                chunk_type=chunk.chunk_type,
                token_count=chunk.token_count,
                confidence_score=chunk.confidence_score,
                source_metadata=chunk.source_metadata,
                created_at=chunk.created_at
            )
            for chunk in chunks
        ]

        return ChunkListResponse(
            chunks=chunk_responses,
            total_chunks=document.chunk_count,
            document_id=str(document.id),
            document_title=document.title
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge document: {e}")
        raise HTTPException(status_code=500, detail="Failed to get knowledge document")


@router.delete("/{document_id}")
async def delete_knowledge_document(
    workspace_id: str,
    document_id: str,
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_authentication),
):
    """Delete a knowledge document and all its chunks."""
    validate_workspace_id(workspace_id)
    validate_object_id(document_id, "document ID")

    try:
        # Get document for audit log
        document = await kb_service.get_document(workspace_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Knowledge document not found")

        # Delete document and chunks
        success = await kb_service.delete_document(workspace_id, document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge document not found")

        # Log audit entry
        await AuditLoggerMixin.audit_delete(
            audit_service=audit_service,
            user_id=current_user.id,
            workspace_id=workspace_id,
            resource_type="knowledge_document",
            resource_id=document_id,
            resource_name=document.title,
            metadata={
                "source_type": document.source_type.value,
                "category": document.category,
                "tags": document.tags,
                "chunk_count": document.chunk_count
            }
        )

        return {"message": "Knowledge document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge document")


@router.put("/{document_id}/upload", response_model=UploadResponse)
async def replace_knowledge_document(
    workspace_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    # File upload (optional)
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    file: UploadFile | None = File(None),
    # Form data
    url: str | None = Form(None),
    content: str | None = Form(None),
    chunking_strategy: str | None = Form(None),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
    # Services
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
    audit_service: AuditService = Depends(get_audit_service),
    current_user: User = Depends(require_authentication),
):
    """Replace an existing knowledge document with new content."""
    validate_workspace_id(workspace_id)
    validate_object_id(document_id, "document ID")

    try:
        # Get existing document
        document = await kb_service.get_document(workspace_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Knowledge document not found")

        # Determine new source based on what's provided
        if file and file.filename:
            # File replacement
            if not kb_service.is_supported_file(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type. Supported: {', '.join(kb_service.get_supported_extensions())}"
                )

            file_content = await file.read()
            file_key = await kb_service.upload_file_to_tigris(
                file_content, file.filename, workspace_id, file.content_type
            )

            # Update document with new file
            task_id = await kb_service.replace_document_source(
                document_id=document_id,
                workspace_id=workspace_id,
                source_type=SourceType.FILE,
                file_key=file_key,
                filename=file.filename,
                file_size=file.size,
                mime_type=file.content_type,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        elif url:
            # URL replacement
            task_id = await kb_service.replace_document_source(
                document_id=document_id,
                workspace_id=workspace_id,
                source_type=SourceType.URL,
                source_url=url,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        elif content:
            # Text content replacement
            task_id = await kb_service.replace_document_source(
                document_id=document_id,
                workspace_id=workspace_id,
                source_type=SourceType.TEXT,
                text_content=content,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

        else:
            raise HTTPException(status_code=400, detail="No new source provided (file, url, or content)")

        # Start background processing
        background_tasks.add_task(
            kb_service.process_document_background,
            document_id=document_id,
            task_id=task_id
        )

        # Log audit entry
        await AuditLoggerMixin.audit_update(
            audit_service=audit_service,
            user_id=current_user.id,
            workspace_id=workspace_id,
            resource_type="knowledge_document",
            resource_id=document_id,
            resource_name=document.title,
            changes={"source_replaced": True, "task_id": task_id},
            metadata={"old_source_type": document.source_type.value}
        )

        logger.info(f"Replaced knowledge document {document_id} with task {task_id}")

        return UploadResponse(
            document_id=document_id,
            task_id=task_id,
            message="Knowledge document source replaced and queued for reprocessing",
            filename=getattr(file, 'filename', None) if file else None,
            status=ProcessingStatus.PENDING
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replace knowledge document: {e}")
        raise HTTPException(status_code=500, detail="Failed to replace knowledge document")


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(
    workspace_id: str,
    query_request: QueryRequest,
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
):
    """Query the knowledge base using semantic/hybrid search."""
    validate_workspace_id(workspace_id)

    try:
        # Perform query
        results = await kb_service.query_documents(workspace_id, query_request)

        logger.info(f"Knowledge query: '{query_request.query}' returned {results.total_results} results in {results.search_time_ms}ms")

        return results

    except Exception as e:
        logger.error(f"Failed to query knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to query knowledge base")


# Optional: Get processing status
@router.get("/tasks/{task_id}")
async def get_processing_status(
    workspace_id: str,
    task_id: str,
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
):
    """Get the status of a document processing task."""
    validate_workspace_id(workspace_id)

    task_status = await kb_service.get_task_status(task_id)
    # A task from another workspace is reported as missing so its existence is not revealed.
    if not task_status or str(task_status.get("workspace_id")) != workspace_id:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_status


# Optional: List documents (for management)
@router.get("", response_model=list[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    workspace_id: str,
    workspace_access: tuple[str, str] = Depends(verify_workspace_access),
    skip: int = 0,
    limit: int = 20,
    category: str | None = None,
    status: str | None = None,
    kb_service: KnowledgeDocumentService = Depends(get_knowledge_document_service),
):
    """List knowledge documents in a workspace."""
    validate_workspace_id(workspace_id)

    try:
        documents = await kb_service.list_documents(
            workspace_id=workspace_id,
            skip=skip,
            limit=limit,
            category=category,
            status=status
        )

        return [
            KnowledgeDocumentResponse(
                id=str(doc.id),
                workspace_id=str(doc.workspace_id),
                title=doc.title,
                description=doc.description,
                category=doc.category,
                tags=doc.tags,
                source_type=doc.source_type,
                filename=doc.filename,
                processing_status=doc.processing_status,
                processing_error=doc.processing_error,
                total_chunks=doc.total_chunks,
                chunk_count=doc.chunk_count,
                status=doc.status,
                author_id=doc.author_id,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                processed_at=doc.processed_at
            )
            for doc in documents
        ]

    except Exception as e:
        logger.error(f"Failed to list knowledge documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge documents")
