"""Knowledge Document service - Document-oriented processing with parsers and chunkers."""

import asyncio
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bson import ObjectId
from langchain_core.documents import Document
from langchain_mongodb import MongoDBAtlasVectorSearch
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from protobox.admin.config import settings
from protobox.admin.models.knowledge_base import (
    ChunkingStrategy,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    ProcessedChunk,
    ProcessingStatus,
    QueryFilters,
    QueryRequest,
    QueryResponse,
    SearchResult,
    SearchType,
    SourceType,
)

# Import chunkers
from protobox.admin.services.chunkers import FAQOptimizer, SmartChunker, Summarizer, TopicHeaderizer
from protobox.admin.services.chunkers.base_chunker import ChunkedContent
from protobox.admin.services.document_client import document_processor_client
from protobox.admin.services.embedding_service import EmbeddingService

# Import parsers
from protobox.admin.services.parsers import (
    HTMLParser,
    TextParser,
    URLScraper,
)
from protobox.admin.services.parsers.base_parser import ParsedDocument
from protobox.admin.services.tigris_service import get_tigris_service


class DocumentProcessor:
    """Handles document parsing and chunking workflow."""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service

        # Initialize parsers (complex formats like PDF, DOCX, XLSX handled by document processor)
        self.parsers = {
            '.html': HTMLParser(),
            '.htm': HTMLParser(),
            '.txt': TextParser(),
            '.md': TextParser(),
            '.markdown': TextParser(),
            '.csv': TextParser(),
            '.json': TextParser(),
            '.rst': TextParser()
        }

        # Initialize special parsers for non-file sources
        self.url_scraper = URLScraper()
        self.text_parser = TextParser()

        # Initialize chunkers
        self.chunkers = {
            ChunkingStrategy.SMART: SmartChunker,
            ChunkingStrategy.FAQ_OPTIMIZATION: FAQOptimizer,
            ChunkingStrategy.TOPIC_HEADERS: TopicHeaderizer,
            ChunkingStrategy.SUMMARIZE: Summarizer
        }

        # File handling settings - include both local parsers and document processor extensions
        self.supported_extensions = set(self.parsers.keys())
        
        # Add document processor extensions (PDF, DOCX, XLSX are handled by microservice)
        document_processor_extensions = {'.pdf', '.docx', '.xlsx'}
        self.supported_extensions.update(document_processor_extensions)
        
        self.max_file_size = 50 * 1024 * 1024  # 50MB

        logger.info(f"Initialized DocumentProcessor with parsers, chunkers and document processor extensions: {document_processor_extensions}")

    async def process_document(
        self,
        document: KnowledgeDocument,
        file_key: str | None = None,
        source_url: str | None = None,
        text_content: str | None = None
    ) -> tuple[list[ProcessedChunk], dict[str, Any]]:
        """
        Process a document through parsing and chunking.
        
        Returns:
            Tuple of (chunks, processing_metadata)
        """
        logger.info(f"Processing document {document.id}: {document.title}")

        # Get timeout from settings
        processing_timeout = getattr(settings, 'kb_source_processing_timeout', 300)  # Default 5 minutes

        try:
            # Step 1: Parse document based on source type with timeout protection
            if document.source_type == SourceType.FILE and file_key:
                parsed_doc = await asyncio.wait_for(
                    self._parse_file(file_key, document.filename),
                    timeout=processing_timeout
                )
            elif document.source_type == SourceType.URL and source_url:
                parsed_doc = await asyncio.wait_for(
                    self._parse_url(source_url),
                    timeout=processing_timeout
                )
            elif document.source_type == SourceType.TEXT and text_content:
                parsed_doc = await asyncio.wait_for(
                    self._parse_text(text_content, document.title),
                    timeout=processing_timeout
                )
            else:
                raise ValueError(f"Invalid source configuration for document {document.id}")

            # Step 2: Chunk the parsed content with timeout protection
            chunked_content = await asyncio.wait_for(
                self._chunk_content(
                    parsed_doc.content,
                    document.chunking_strategy,
                    chunk_size=document.chunk_size,
                    chunk_overlap=document.chunk_overlap,
                    document_metadata=parsed_doc.metadata
                ),
                timeout=processing_timeout
            )

            # Step 3: Generate embeddings and create ProcessedChunk objects with timeout protection
            chunks = await asyncio.wait_for(
                self._create_processed_chunks(
                    document_id=document.id,
                    chunked_content=chunked_content,
                    source_metadata=parsed_doc.metadata
                ),
                timeout=processing_timeout
            )

            # Step 4: Create processing metadata
            processing_metadata = {
                'parsed_at': parsed_doc.parsed_at.isoformat(),
                'parser_metadata': parsed_doc.metadata,
                'chunker_metadata': chunked_content.metadata,
                'total_chunks': len(chunks),
                'successful_chunks': len([c for c in chunks if c.confidence_score > 0.5]),
                'processing_completed_at': datetime.now(UTC).isoformat(),
                'processing_timeout': processing_timeout,
                'processing_status': 'completed'
            }

            logger.info(f"Successfully processed document {document.id}: {len(chunks)} chunks created")
            return chunks, processing_metadata

        except TimeoutError:
            logger.error(f"Processing timed out for document {document.id} after {processing_timeout}s")

            # Create partial results with whatever we have
            partial_chunks = []
            partial_metadata = {
                'processing_error': f"Processing timed out after {processing_timeout}s",
                'processing_status': 'partial',
                'processing_timeout': processing_timeout,
                'processing_completed_at': datetime.now(UTC).isoformat()
            }

            # If we have parsed content, try to create at least some chunks
            if 'parsed_doc' in locals():
                try:
                    # Create minimal chunks from parsed content
                    chunked_content = await self._chunk_content(
                        parsed_doc.content,
                        ChunkingStrategy.SMART,  # Use smart chunking as fallback
                        chunk_size=512,
                        chunk_overlap=50
                    )

                    chunks = await self._create_processed_chunks(
                        document_id=document.id,
                        chunked_content=chunked_content,
                        source_metadata=parsed_doc.metadata
                    )

                    partial_chunks = chunks
                    partial_metadata.update({
                        'parsed_at': parsed_doc.parsed_at.isoformat(),
                        'parser_metadata': parsed_doc.metadata,
                        'total_chunks': len(chunks),
                        'successful_chunks': len(chunks),
                        'warnings': ['Processing completed with timeout - using partial results']
                    })

                    logger.info(f"Created {len(chunks)} partial chunks after timeout for document {document.id}")

                except Exception as chunk_error:
                    logger.error(f"Failed to create partial chunks after timeout: {chunk_error}")
                    partial_metadata['warnings'] = ['Failed to create partial chunks after timeout']

            return partial_chunks, partial_metadata

        except Exception as e:
            logger.error(f"Failed to process document {document.id}: {e}")
            raise

    async def _parse_file(self, file_key: str, filename: str) -> ParsedDocument:
        """Parse a file using document processor service for complex formats or local parsers for simple ones."""
        import tempfile
        from pathlib import Path

        file_ext = Path(filename).suffix.lower()

        # Complex formats that benefit from document processor microservice
        complex_formats = {'.pdf', '.docx', '.doc', '.xlsx', '.xls'}

        if file_ext in complex_formats:
            logger.info(f"📄 Processing {filename} via document processor service")
            try:
                # Check if document processor is available
                is_healthy = await document_processor_client.check_health()
                if not is_healthy:
                    raise Exception("Document processor service unavailable")

                # Generate signed URL for document processor access
                signed_url = get_tigris_service().generate_presigned_url(
                    file_key=file_key,
                    expiration=3600  # 1 hour
                )

                # File size is optional for document processor
                file_size = None

                # Process document via microservice
                result = await document_processor_client.process_document(
                    signed_url=signed_url,
                    file_type=file_ext.lstrip('.'),
                    file_size=file_size,
                    options={
                        "use_ocr": True,
                        "extract_tables": True,
                        "extract_images": False  # For now, focus on text content
                    }
                )

                # Convert document processor result to ParsedDocument format
                return self._convert_processor_result_to_parsed_document(
                    result, filename, file_ext
                )

            except Exception as e:
                logger.error(f"Document processor failed for {filename}: {e}")
                # For production, we want to fail fast rather than degrade
                raise ValueError(f"Failed to process {filename} via document processor: {str(e)}")

        else:
            # Simple formats - use local parsers
            logger.info(f"📄 Processing {filename} via local parser")
            parser = self.parsers.get(file_ext)

            if not parser:
                raise ValueError(f"No parser available for file extension: {file_ext}")

            # Download file from Tigris to temporary location for parsing
            try:
                file_content = await get_tigris_service().download_file(file_key)

                # Create temporary file for parser
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name

                try:
                    # Parse the file
                    result = await parser.parse(temp_file_path)
                    return result
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {temp_file_path}: {e}")

            except Exception as e:
                logger.error(f"Failed to download and parse file {file_key}: {e}")
                raise

    async def _parse_url(self, url: str) -> ParsedDocument:
        """Parse URL content - route PDFs to document processor, HTML to URL scraper."""
        # Check if URL appears to be a PDF by checking the URL or content type
        if url.lower().endswith('.pdf'):
            logger.info(f"📄 Detected PDF URL, routing to document processor: {url}")
            try:
                # Use document processor for PDF URLs
                result = await document_processor_client.process_document(
                    signed_url=url,
                    file_type="pdf",
                    options={
                        "use_ocr": True,
                        "extract_tables": True,
                        "extract_images": False
                    }
                )

                # Include processing time in metadata
                metadata = result.get('metadata', {})
                if result.get('processing_time'):
                    metadata['processing_time'] = result.get('processing_time')

                return ParsedDocument(
                    content=result.get('content', ''),
                    metadata=metadata
                )
            except Exception as e:
                logger.error(f"Document processor failed for PDF URL {url}: {e}")
                raise Exception(f"Failed to process PDF from URL: {str(e)}")
        else:
            # Use URL scraper for HTML content
            logger.info(f"🌐 Detected HTML URL, routing to URL scraper: {url}")
            return await self.url_scraper.parse(url)

    async def _parse_text(self, content: str, title: str) -> ParsedDocument:
        """Parse raw text content."""
        return await self.text_parser.parse_text(content, title)

    async def _chunk_content(
        self,
        content: str,
        chunking_strategy: ChunkingStrategy,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        document_metadata: dict[str, Any] | None = None
    ) -> ChunkedContent:
        """Chunk content using specified strategy."""
        chunker_class = self.chunkers.get(chunking_strategy, SmartChunker)
        chunker = chunker_class(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        return await chunker.chunk(content, document_metadata=document_metadata)

    def _convert_processor_result_to_parsed_document(
        self,
        processor_result: dict[str, Any],
        filename: str,
        file_ext: str
    ) -> ParsedDocument:
        """Convert document processor service result to ParsedDocument format."""

        # Create ParsedDocument from processor result
        parsed_doc = ParsedDocument(
            content=processor_result.get('content', ''),
            metadata=processor_result.get('metadata', {}),
            parsed_at=datetime.now(UTC),
            parser_name=f"document-processor-{file_ext.lstrip('.')}"
        )

        # Enhance metadata with processing info
        parsed_doc.metadata.update({
            'filename': filename,
            'file_extension': file_ext,
            'processing_method': 'document-processor-microservice',
            'processor_status': processor_result.get('status', 'unknown'),
            'processing_time': processor_result.get('processing_time'),
            'warnings': processor_result.get('warnings', [])
        })

        logger.info(f"✅ Converted processor result for {filename}: {len(parsed_doc.content):,} chars")
        return parsed_doc

    async def _create_processed_chunks(
        self,
        document_id: ObjectId,
        chunked_content: ChunkedContent,
        source_metadata: dict[str, Any]
    ) -> list[ProcessedChunk]:
        """Create ProcessedChunk objects with embeddings."""
        processed_chunks = []

        for i, chunk_data in enumerate(chunked_content.chunks):
            # Generate embedding for chunk content
            embedding = await self.embedding_service.generate_embedding(chunk_data['content'])

            # Create ProcessedChunk
            chunk = ProcessedChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_data['content'],
                chunk_type=chunk_data.get('chunk_type', 'content'),
                embedding=embedding,
                token_count=chunk_data.get('token_count', 0),
                confidence_score=chunk_data.get('confidence_score', 1.0),
                source_metadata={
                    **source_metadata,
                    **chunk_data.get('source_metadata', {}),
                    'chunker_metadata': {
                        'chunker': chunked_content.metadata.get('chunker'),
                        'chunk_size': chunked_content.metadata.get('chunk_size'),
                        'strategy_specific': chunk_data.get('strategy_metadata', {})
                    }
                }
            )

            processed_chunks.append(chunk)

        return processed_chunks


class KnowledgeDocumentService:
    """Service for managing document-oriented knowledge base with LangChain integration."""

    def __init__(self, database: AsyncIOMotorDatabase, embedding_service: EmbeddingService):
        self.db = database
        self.documents_collection: AsyncIOMotorCollection = database.knowledge_documents
        self.chunks_collection: AsyncIOMotorCollection = database.knowledge_chunks
        self.tasks_collection: AsyncIOMotorCollection = database.processing_tasks
        self.embedding_service = embedding_service
        self.processor = DocumentProcessor(embedding_service)

        # Initialize LangChain vector store
        self._init_langchain_vector_store()

        logger.info("Initialized KnowledgeDocumentService with LangChain integration")

    def _init_langchain_vector_store(self):
        """Initialize LangChain MongoDB vector store using from_connection_string."""
        try:
            # Use connection string from settings directly

            # Use from_connection_string for proper initialization
            self.vector_store = MongoDBAtlasVectorSearch.from_connection_string(
                connection_string=settings.mongodb_url,
                namespace=f"{self.db.name}.knowledge_chunks_vector",
                embedding=self.embedding_service.get_langchain_embeddings(),
                index_name="vector_index"
            )

            logger.info(f"LangChain MongoDB vector store initialized successfully using connection string: {settings.mongodb_url[:10]}...{settings.mongodb_url[-10:]}")

        except Exception as e:
            logger.warning(f"Failed to initialize LangChain vector store: {e}")
            self.vector_store = None

    def is_supported_file(self, filename: str) -> bool:
        """Check if file type is supported."""
        return Path(filename).suffix.lower() in self.processor.supported_extensions

    def get_supported_extensions(self) -> list[str]:
        """Get list of supported file extensions."""
        return list(self.processor.supported_extensions)

    def is_valid_file_size(self, file_size: int) -> bool:
        """Check if file size is within limits."""
        return file_size <= self.processor.max_file_size

    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.processor.max_file_size

    async def upload_file_to_tigris(
        self,
        file_content: bytes,
        filename: str,
        workspace_id: str,
        content_type: str | None = None
    ) -> str:
        """Upload file to Tigris object storage."""
        try:
            file_key = await get_tigris_service().upload_file(
                file_content=file_content,
                filename=filename,
                workspace_id=workspace_id,
                content_type=content_type,
                metadata={
                    'uploaded_by': 'knowledge_document_service',
                    'purpose': 'knowledge_base_processing'
                }
            )

            logger.info(f"Uploaded file to Tigris: {file_key}")
            return file_key

        except Exception as e:
            logger.error(f"Failed to upload file to Tigris: {e}")
            raise

    async def create_document(
        self,
        workspace_id: str,
        document_data: KnowledgeDocumentCreate,
        user_id: str,
        file_key: str | None = None,
        filename: str | None = None,
        file_size: int | None = None,
        mime_type: str | None = None,
        source_url: str | None = None,
        text_content: str | None = None
    ) -> KnowledgeDocument:
        """Create a new knowledge document."""
        logger.info(f"Creating knowledge document: {document_data.title}")

        # Determine original_source based on source type
        if document_data.source_type == SourceType.FILE:
            original_source = file_key or f"file://{filename}"
        elif document_data.source_type == SourceType.URL:
            original_source = source_url or document_data.url
        else:  # TEXT
            original_source = text_content or document_data.content or "inline_text"

        # Create document
        document = KnowledgeDocument(
            workspace_id=ObjectId(workspace_id),
            title=document_data.title,
            description=document_data.description,
            category=document_data.category,
            tags=document_data.tags,
            source_type=document_data.source_type,
            original_source=original_source,
            file_size=file_size,
            filename=filename,
            mime_type=mime_type,
            chunking_strategy=document_data.chunking_strategy,
            chunk_size=document_data.chunk_size,
            chunk_overlap=document_data.chunk_overlap,
            author_id=user_id,
            processing_metadata={
                'crawl_depth': getattr(document_data, 'crawl_depth', 3)
            }
        )

        # Save to database
        document_dict = document.model_dump(by_alias=True)
        result = await self.documents_collection.insert_one(document_dict)
        document.id = result.inserted_id

        logger.info(f"Created knowledge document {document.id}")
        return document

    async def get_document(self, workspace_id: str, document_id: str) -> KnowledgeDocument | None:
        """Get a knowledge document by ID."""
        document_data = await self.documents_collection.find_one({
            "_id": ObjectId(document_id),
            "workspace_id": ObjectId(workspace_id)
        })

        if not document_data:
            return None

        return KnowledgeDocument(**document_data)

    async def list_documents(
        self,
        workspace_id: str,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        status: str | None = None
    ) -> list[KnowledgeDocument]:
        """List knowledge documents."""
        query = {"workspace_id": ObjectId(workspace_id)}

        if category:
            query["category"] = category
        if status:
            query["status"] = status

        cursor = self.documents_collection.find(
            query,
            sort=[("updated_at", -1)],
            skip=skip,
            limit=limit
        )

        documents = []
        async for doc_data in cursor:
            documents.append(KnowledgeDocument(**doc_data))

        return documents

    async def delete_document(self, workspace_id: str, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        # Get document to clean up files
        document = await self.get_document(workspace_id, document_id)

        # Delete chunks first
        await self.chunks_collection.delete_many({
            "document_id": ObjectId(document_id)
        })

        # Delete chunks from vector store if available
        if self.vector_store:
            try:
                # Delete chunks from the vector store collection directly
                vector_collection = self.db.knowledge_chunks_vector
                delete_result = await vector_collection.delete_many({
                    "document_id": str(document_id)
                })
                logger.info(f"Deleted {delete_result.deleted_count} chunks from vector store for document {document_id}")
            except Exception as e:
                logger.warning(f"Failed to delete chunks from vector store: {e}")

        # Delete file from Tigris if it's a file document
        if document and document.source_type == SourceType.FILE:
            try:
                await get_tigris_service().delete_file(document.original_source)
                logger.info(f"Deleted file from Tigris: {document.original_source}")
            except Exception as e:
                logger.warning(f"Failed to delete file from Tigris: {e}")

        # Delete document
        result = await self.documents_collection.delete_one({
            "_id": ObjectId(document_id),
            "workspace_id": ObjectId(workspace_id)
        })

        return result.deleted_count > 0

    async def get_document_chunks(
        self,
        document_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> list[ProcessedChunk]:
        """Get processed chunks for a document."""
        cursor = self.chunks_collection.find(
            {"document_id": ObjectId(document_id)},
            sort=[("chunk_index", 1)],
            skip=skip,
            limit=limit
        )

        chunks = []
        async for chunk_data in cursor:
            chunks.append(ProcessedChunk(**chunk_data))

        return chunks

    async def queue_processing_task(self, document_id: str, workspace_id: str) -> str:
        """Queue a document processing task."""
        task_id = str(uuid.uuid4())

        task_data = {
            "_id": task_id,
            "document_id": ObjectId(document_id),
            "workspace_id": ObjectId(workspace_id),
            "status": "queued",
            "created_at": datetime.now(UTC),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "progress": 0
        }

        await self.tasks_collection.insert_one(task_data)
        logger.info(f"Queued processing task {task_id} for document {document_id}")

        return task_id

    async def _add_chunks_to_vector_store(self, chunks: list[ProcessedChunk], workspace_id: str):
        """Add processed chunks to LangChain vector store."""
        if not self.vector_store:
            return

        # Convert ProcessedChunks to LangChain Documents
        documents = []
        for chunk in chunks:
            doc = Document(
                page_content=chunk.content,
                metadata={
                    "_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "workspace_id": workspace_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_type": chunk.chunk_type,
                    "token_count": chunk.token_count,
                    "confidence_score": chunk.confidence_score,
                    "source_metadata": chunk.source_metadata or {},
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
            )
            documents.append(doc)

        # Add documents to vector store (LangChain will use existing embeddings)
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.vector_store.add_documents,
            documents
        )

    async def process_document_background(self, document_id: str, task_id: str):
        """Background task to process a document."""
        logger.info(f"Starting background processing for document {document_id}, task {task_id}")
        start_time = datetime.now(UTC)

        try:
            # Update task status to processing
            await self.tasks_collection.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": "processing",
                        "started_at": start_time,
                        "progress": 10
                    }
                }
            )

            # Get document
            document = await self.documents_collection.find_one({"_id": ObjectId(document_id)})
            if not document:
                raise ValueError(f"Document {document_id} not found")

            document_obj = KnowledgeDocument(**document)

            # Update document status to processing
            await self.documents_collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": {"processing_status": ProcessingStatus.PROCESSING}}
            )

            # Process document based on source type
            source_args = {}
            if document_obj.source_type == SourceType.FILE:
                source_args['file_key'] = document_obj.original_source
            elif document_obj.source_type == SourceType.URL:
                source_args['source_url'] = document_obj.original_source
            else:  # TEXT
                source_args['text_content'] = document_obj.original_source

            # Update progress
            await self.tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"progress": 30}}
            )

            # Execute document processing
            chunks, processing_metadata = await self.processor.process_document(
                document_obj, **source_args
            )

            # Update progress after processing
            await self.tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {"progress": 70}}
            )

            # Save chunks to database and vector store
            if chunks:
                # Save to traditional MongoDB collection
                chunk_dicts = []
                for chunk in chunks:
                    chunk_dict = chunk.model_dump(by_alias=True)
                    if '_id' not in chunk_dict:
                        chunk_dict['_id'] = chunk.id
                    chunk_dicts.append(chunk_dict)

                await self.chunks_collection.insert_many(chunk_dicts)
                logger.info(f"Saved {len(chunk_dicts)} chunks to traditional database")

                # Save to LangChain vector store if available
                if self.vector_store:
                    try:
                        await self._add_chunks_to_vector_store(chunks, str(document_obj.workspace_id))
                        logger.info(f"Added {len(chunks)} chunks to LangChain vector store")
                    except Exception as vector_error:
                        logger.warning(f"Failed to add chunks to vector store: {vector_error}")
                        # Continue processing - don't fail the whole operation

            # Calculate processing time
            processing_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            processing_metadata['processing_time_ms'] = processing_time_ms

            # Determine processing status based on metadata
            processing_status = ProcessingStatus.COMPLETED
            if processing_metadata.get('processing_status') == 'partial':
                processing_status = ProcessingStatus.PARTIAL
                logger.warning(f"Document {document_id} processed with partial results")

            # Update document with results (complete or partial)
            await self.documents_collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "processing_status": processing_status,
                        "processed_at": datetime.now(UTC),
                        "total_chunks": len(chunks),
                        "chunk_count": len(chunks),
                        "processing_metadata": processing_metadata,
                        "updated_at": datetime.now(UTC),
                        "processing_error": processing_metadata.get('processing_error')  # May contain timeout info
                    }
                }
            )

            # Update task status to completed
            task_status = "completed"
            if processing_status == ProcessingStatus.PARTIAL:
                task_status = "completed_partial"

            await self.tasks_collection.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": task_status,
                        "completed_at": datetime.now(UTC),
                        "progress": 100,
                        "result": {
                            "chunks_created": len(chunks),
                            "processing_time_ms": processing_time_ms,
                            "successful": True,
                            "processing_status": processing_status.value,
                            "warnings": processing_metadata.get('warnings', [])
                        }
                    }
                }
            )

            logger.info(f"Completed processing document {document_id}: {len(chunks)} chunks created in {processing_time_ms}ms")

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}", exc_info=True)

            # Update document status to failed
            await self.documents_collection.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "processing_status": ProcessingStatus.FAILED,
                        "processing_error": str(e),
                        "updated_at": datetime.now(UTC)
                    }
                }
            )

            # Update task status to failed
            await self.tasks_collection.update_one(
                {"_id": task_id},
                {
                    "$set": {
                        "status": "failed",
                        "completed_at": datetime.now(UTC),
                        "error": str(e),
                        "progress": 0  # Reset progress on failure
                    }
                }
            )

    async def replace_document_source(
        self,
        document_id: str,
        workspace_id: str,
        source_type: SourceType,
        file_key: str | None = None,
        filename: str | None = None,
        file_size: int | None = None,
        mime_type: str | None = None,
        source_url: str | None = None,
        text_content: str | None = None,
        chunking_strategy: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None
    ) -> str:
        """Replace document source and reprocess."""
        # Get existing document to clean up old file if needed
        existing_doc = await self.get_document(workspace_id, document_id)
        if existing_doc and existing_doc.source_type == SourceType.FILE and source_type == SourceType.FILE:
            # Delete old file from Tigris
            try:
                await get_tigris_service().delete_file(existing_doc.original_source)
                logger.info(f"Deleted old file from Tigris: {existing_doc.original_source}")
            except Exception as e:
                logger.warning(f"Failed to delete old file from Tigris: {e}")

        # Delete existing chunks
        await self.chunks_collection.delete_many({
            "document_id": ObjectId(document_id)
        })

        # Update document with new source
        update_data = {
            "source_type": source_type.value,
            "processing_status": ProcessingStatus.PENDING,
            "processing_error": None,
            "total_chunks": 0,
            "chunk_count": 0,
            "updated_at": datetime.now(UTC)
        }

        if source_type == SourceType.FILE:
            update_data.update({
                "original_source": file_key,
                "filename": filename,
                "file_size": file_size,
                "mime_type": mime_type
            })
        elif source_type == SourceType.URL:
            update_data.update({
                "original_source": source_url
            })
        else:  # TEXT
            update_data["original_source"] = text_content

        if chunking_strategy:
            update_data["chunking_strategy"] = chunking_strategy
        if chunk_size:
            update_data["chunk_size"] = chunk_size
        if chunk_overlap:
            update_data["chunk_overlap"] = chunk_overlap

        await self.documents_collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )

        # Queue new processing task
        task_id = await self.queue_processing_task(document_id, workspace_id)
        return task_id

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get processing task status."""
        task = await self.tasks_collection.find_one({"_id": task_id})
        if not task:
            return None

        # Convert ObjectIds to strings for JSON serialization
        if 'document_id' in task:
            task['document_id'] = str(task['document_id'])
        if 'workspace_id' in task:
            task['workspace_id'] = str(task['workspace_id'])

        return task

    async def query_documents(self, workspace_id: str, query_request: QueryRequest) -> QueryResponse:
        """Query knowledge base using LangChain vector store when available."""
        start_time = time.time()

        query = query_request.query
        filters = query_request.filters

        logger.info(f"Starting KB query with LangChain: '{query}' | workspace: {workspace_id} | search_type: {filters.search_type}")

        try:
            # Route to appropriate search method
            search_start = time.time()

            if filters.search_type == SearchType.SEMANTIC:
                if self.vector_store:
                    results = await self._langchain_semantic_search(workspace_id, query, filters)
                    logger.info(f"LangChain semantic search completed: {len(results)} results")
                else:
                    raise ValueError("Semantic search requires LangChain vector store to be available")

            elif filters.search_type == SearchType.HYBRID:
                if self.vector_store:
                    results = await self._langchain_hybrid_search(workspace_id, query, filters)
                    logger.info(f"LangChain hybrid search completed: {len(results)} results")
                else:
                    raise ValueError("Hybrid search requires LangChain vector store to be available")

            elif filters.search_type == SearchType.KEYWORD:
                results = await self._keyword_search(workspace_id, query, filters)
                logger.info(f"Keyword search completed: {len(results)} results")

            else:
                raise ValueError(f"Invalid search type: {filters.search_type}")

            search_time_ms = int((time.time() - start_time) * 1000)

            # Log summary with relevance scores
            if results:
                top_score = results[0].relevance_score if results else 0
                avg_score = sum(r.relevance_score for r in results) / len(results) if results else 0
                logger.info(f"Query results summary - Top score: {top_score:.4f} | Avg score: {avg_score:.4f} | Total time: {search_time_ms}ms")
            else:
                logger.warning(f"No results found for query: '{query}' | Search time: {search_time_ms}ms | Min relevance: {filters.min_relevance}")

            return QueryResponse(
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                search_type=filters.search_type,
                query=query,
                filters=filters
            )

        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Query failed after {search_time_ms}ms: {e}", exc_info=True)
            raise

    async def _langchain_semantic_search(self, workspace_id: str, query: str, filters: QueryFilters) -> list[SearchResult]:
        """Perform semantic search using LangChain vector store."""
        if not self.vector_store:
            raise ValueError("LangChain vector store not available")

        # Perform similarity search with scores using correct LangChain MongoDB API
        import asyncio
        loop = asyncio.get_event_loop()

        doc_score_pairs = await loop.run_in_executor(
            None,
            lambda: self.vector_store.similarity_search_with_relevance_scores(
                query,
                k=filters.max_results * 4  # Get more results to filter manually
            )
        )
        logger.info(f"Retrieved doc_score_pairs: {len(doc_score_pairs)}")
        results = []
        for doc, score in doc_score_pairs:
            if score >= filters.min_relevance:
                # Check workspace_id if we're doing manual filtering (fallback case)
                doc_workspace_id = doc.metadata.get("workspace_id")
                if doc_workspace_id != workspace_id:
                    continue  # Skip results from other workspaces

                # Filter by document_ids if specified
                doc_document_id = doc.metadata.get("document_id")
                if filters.document_ids and doc_document_id not in filters.document_ids:
                    continue  # Skip results not in the specified document list

                # Get document metadata for the result
                document_info = await self._get_document_info(doc_document_id)

                result = SearchResult(
                    document_id=doc_document_id,
                    chunk_id=doc.metadata.get("_id"),
                    document_title=document_info.get("title", "Unknown") if document_info else "Unknown",
                    content_snippet=doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    chunk_type=doc.metadata.get("chunk_type", "content"),
                    category=document_info.get("category", "") if document_info else "",
                    tags=document_info.get("tags", []) if document_info else [],
                    relevance_score=score,
                    search_type="semantic_langchain",
                    source_metadata=doc.metadata.get("source_metadata", {}),
                    token_count=doc.metadata.get("token_count", 0),
                    chunk_index=doc.metadata.get("chunk_index", 0)
                )
                results.append(result)

        return results[:filters.max_results]

    async def _langchain_hybrid_search(self, workspace_id: str, query: str, filters: QueryFilters) -> list[SearchResult]:
        """Perform hybrid search using LangChain vector search + keyword search."""
        if not self.vector_store:
            raise ValueError("LangChain vector store not available")

        # Get semantic results from LangChain vector store
        semantic_results = await self._langchain_semantic_search(workspace_id, query, filters)

        # Get keyword results from traditional MongoDB text search
        keyword_results = await self._keyword_search(workspace_id, query, filters)

        logger.debug(f"Hybrid fusion: {len(semantic_results)} semantic + {len(keyword_results)} keyword results")

        # Simple fusion: combine and deduplicate by chunk_id
        seen_chunks = set()
        combined_results = []

        # Add semantic results first (they typically have better relevance)
        for result in semantic_results:
            if result.chunk_id not in seen_chunks:
                result.search_type = "hybrid"
                combined_results.append(result)
                seen_chunks.add(result.chunk_id)

        # Add keyword results that weren't already included
        for result in keyword_results:
            if result.chunk_id not in seen_chunks:
                result.search_type = "hybrid"
                combined_results.append(result)
                seen_chunks.add(result.chunk_id)

        logger.info(f"Hybrid fusion complete: {len(combined_results)} total unique chunks")

        # Re-sort by relevance score
        combined_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return combined_results[:filters.max_results]


    async def _get_document_info(self, document_id: str) -> dict[str, Any] | None:
        """Get document information from the documents collection."""
        try:
            doc_info = await self.documents_collection.find_one({"_id": ObjectId(document_id)})
            return doc_info
        except Exception as e:
            logger.warning(f"Failed to get document info for {document_id}: {e}")
            return None

    async def _keyword_search(self, workspace_id: str, query: str, filters: QueryFilters) -> list[SearchResult]:
        """Perform keyword search using text search."""
        eligible_doc_ids = await self._get_document_ids(workspace_id, filters)
        match_conditions = {
            "document_id": {"$in": eligible_doc_ids},
            "$text": {"$search": query}
        }

        logger.debug(f"Keyword search: query='{query}' | documents={len(eligible_doc_ids)}")

        cursor = self.chunks_collection.find(
            match_conditions,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(filters.max_results)

        results = []
        chunks_found = 0
        async for chunk_data in cursor:
            chunks_found += 1
            doc = await self.documents_collection.find_one({"_id": chunk_data['document_id']})
            if doc:
                text_score = chunk_data.get('score', 0.5)
                result = SearchResult(
                    document_id=str(chunk_data['document_id']),
                    chunk_id=str(chunk_data['_id']),
                    document_title=doc['title'],
                    content_snippet=chunk_data['content'][:300] + "..." if len(chunk_data['content']) > 300 else chunk_data['content'],
                    chunk_type=chunk_data.get('chunk_type', 'content'),
                    category=doc['category'],
                    tags=doc['tags'],
                    relevance_score=text_score,
                    search_type="keyword",
                    source_metadata=chunk_data.get('source_metadata', {}),
                    token_count=chunk_data.get('token_count', 0),
                    chunk_index=chunk_data.get('chunk_index', 0)
                )
                results.append(result)

        logger.info(f"Keyword search found {chunks_found} matching chunks, returned {len(results)} results")
        return results

    async def _get_document_ids(self, workspace_id: str, filters: QueryFilters) -> list[ObjectId]:
        """Get document IDs matching filters."""
        query = {"workspace_id": ObjectId(workspace_id), "status": "active"}

        if filters.categories:
            query["category"] = {"$in": filters.categories}
        if filters.tags:
            query["tags"] = {"$in": filters.tags}
        if filters.document_ids:
            query["_id"] = {"$in": [ObjectId(doc_id) for doc_id in filters.document_ids]}

        cursor = self.documents_collection.find(query, {"_id": 1})
        return [doc["_id"] async for doc in cursor]
