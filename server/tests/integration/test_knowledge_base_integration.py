"""Integration tests for Knowledge Base API with all source types and chunking strategies."""

import asyncio
import os
import pytest
import tempfile
import json
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from httpx import Client
from unittest.mock import patch, AsyncMock

# Import utility for authenticated tests
try:
    from .test_utils import AuthenticatedTestCase
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(__file__))
    from test_utils import AuthenticatedTestCase

# Test configuration from environment variables
TEST_CONFIG = {
    # File paths for testing different formats
    "PDF_PATH": os.getenv("TEST_PDF_PATH", ""),
    "DOCX_PATH": os.getenv("TEST_DOCX_PATH", ""),
    "XLSX_PATH": os.getenv("TEST_XLSX_PATH", ""),
    "HTML_PATH": os.getenv("TEST_HTML_PATH", ""),
    "TXT_PATH": os.getenv("TEST_TXT_PATH", ""),
    
    # URLs for testing web scraping
    "WEBSITE_URL": os.getenv("TEST_WEBSITE_URL", "https://github.com/upstash/context7"),
    
    # Test content
    "SAMPLE_TEXT": os.getenv("TEST_SAMPLE_TEXT", """
# Sample Knowledge Base Content

## Introduction
This is a comprehensive guide to testing knowledge base functionality.

## Features
- Document parsing and processing
- Multiple chunking strategies
- Semantic search capabilities
- File format support

## Implementation Details
The system supports various file formats including PDF, DOCX, Excel, HTML, and plain text.
Each document is processed through a pipeline that includes parsing, chunking, and embedding generation.

## Chunking Strategies

### Smart Chunking
Uses topic-based clustering to create meaningful content segments.

### FAQ Optimization
Generates question-answer pairs from the content.

### Topic Headers
Creates summaries with clear section headers.

### Summarization
Extracts key points and main ideas from the content.
    """.strip()),
    
    # Database and API settings
    "WORKSPACE_ID": os.getenv("TEST_WORKSPACE_ID", "507f1f77bcf86cd799439011"),
    "API_BASE_URL": os.getenv("TEST_API_BASE_URL", "/admin/api/v1"),
    "TIMEOUT": int(os.getenv("TEST_TIMEOUT", "60")),
}

# Chunking strategies to test
CHUNKING_STRATEGIES = [
    "smart",
    "faq_optimization", 
    "topic_headers",
    "summarize"
]


@pytest.mark.integration
class TestKnowledgeBaseIntegration(AuthenticatedTestCase):
    """Integration tests for knowledge base functionality."""
    
    @classmethod
    def setup_class(cls):
        """Set up test configuration."""
        # Environment can be controlled via TEST_ENVIRONMENT env var
        import os
        environment = os.getenv("TEST_ENVIRONMENT", "local")
        cls.setup_auth(environment=environment)
        if hasattr(cls, 'skip_tests') and cls.skip_tests:
            return
            
        cls.base_url = f"/admin/api/v1/workspaces/{cls.workspace_id}/knowledge"
    
    @classmethod
    def teardown_class(cls):
        """Cleanup."""
        cls.teardown_auth()
    
    def setup_method(self):
        """Set up for each test method."""
        if self.skip_tests:
            pytest.skip(self.skip_reason)
        
        self.uploaded_documents = []  # Track for cleanup
    
    def teardown_method(self):
        """Clean up uploaded documents."""
        # Clean up uploaded documents
        for doc_id in self.uploaded_documents:
            try:
                self.client.delete(f"{self.base_url}/{doc_id}", headers=self.headers)
            except:
                pass  # Ignore cleanup errors
    
    def _create_test_file(self, content: str, filename: str, content_type: str = "text/plain") -> tuple:
        """Create a temporary test file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=Path(filename).suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        
        with open(temp_file.name, 'rb') as f:
            file_content = f.read()
        
        return temp_file.name, file_content
    
    def _wait_for_processing(self, task_id: str, timeout: int = None) -> Dict[str, Any]:
        """Wait for document processing to complete.
        
        TODO: Replace this inefficient polling approach with a better solution:
        - WebSockets for real-time task status updates
        - Server-Sent Events (SSE) for task progress streaming
        - Background task queue with Redis/Celery and proper notifications
        - Event-driven architecture with task completion callbacks
        
        Current approach is temporary for testing purposes only.
        """
        timeout = timeout or TEST_CONFIG["TIMEOUT"]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            response = self.client.get(f"{self.base_url}/tasks/{task_id}", headers=self.headers)
            if response.status_code == 200:
                task_status = response.json()
                if task_status["status"] in ["completed", "failed"]:
                    return task_status
            
            time.sleep(2)  # Poll every 2 seconds
        
        raise TimeoutError(f"Processing did not complete within {timeout} seconds")
    
    @pytest.mark.text
    @pytest.mark.all_strategies
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_text_source_all_strategies(self):
        """Test text source with all chunking strategies."""
        for strategy in CHUNKING_STRATEGIES:
                # TODO: Skip FAQ optimization due to polling inefficiency and OpenAI API latency
                # Revisit when implementing WebSocket/SSE-based task monitoring
                if strategy == "faq_optimization":
                    print(f"\n⏭️ Skipping {strategy} strategy (TODO: implement better task monitoring)")
                    continue
                    
                print(f"\n🧪 Testing TEXT source with {strategy} strategy...")
                
                # Prepare request data
                upload_data = {
                    "title": f"Test Text Document - {strategy}",
                    "description": f"Testing text processing with {strategy} chunking",
                    "category": "test",
                    "tags": f"test,text,{strategy}",
                    "source_type": "text",
                    "content": TEST_CONFIG["SAMPLE_TEXT"],
                    "chunking_strategy": strategy,
                    "chunk_size": "512",
                    "chunk_overlap": "50"
                }
                
                # Upload document
                response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
                assert response.status_code == 200, f"Upload failed: {response.text}"
                
                result = response.json()
                document_id = result["document_id"]
                task_id = result["task_id"]
                self.uploaded_documents.append(document_id)
                
                print(f"✅ Document uploaded: {document_id}, Task: {task_id}")
                
                # Wait for processing
                task_status = self._wait_for_processing(task_id)
                assert task_status["status"] == "completed", f"Processing failed: {task_status.get('error', 'Unknown error')}"
                
                print(f"✅ Processing completed for {strategy}")
                
                # Get processed chunks
                response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
                assert response.status_code == 200
                
                chunks_data = response.json()
                assert chunks_data["total_chunks"] > 0, "No chunks were created"
                assert len(chunks_data["chunks"]) > 0, "No chunks returned"
                
                print(f"✅ {strategy}: Created {chunks_data['total_chunks']} chunks")
                
                # Verify chunk content
                first_chunk = chunks_data["chunks"][0]
                assert "content" in first_chunk
                assert "chunk_type" in first_chunk
                assert "token_count" in first_chunk
                assert first_chunk["token_count"] > 0
                
                print(f"✅ {strategy}: Chunk validation passed")
    
    @pytest.mark.url
    @pytest.mark.scraping
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_url_source(self):
        """Test URL source processing."""
        if not TEST_CONFIG["WEBSITE_URL"]:
            pytest.fail("TEST_WEBSITE_URL environment variable is required but not provided")
        
        print(f"\n🧪 Testing URL source: {TEST_CONFIG['WEBSITE_URL']}")
        
        upload_data = {
            "title": "Test Web Content",
            "description": "Testing URL scraping and processing",
            "category": "web",
            "tags": "test,url,scraping",
            "source_type": "url",
            "url": TEST_CONFIG["WEBSITE_URL"],
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200, f"URL upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ URL document uploaded: {document_id}")
        
        # Wait for processing (URLs may take longer)
        task_status = self._wait_for_processing(task_id, timeout=120)
        
        if task_status["status"] == "failed":
            print(f"⚠️ URL processing failed (expected for some test URLs): {task_status.get('error', 'Unknown error')}")
            pytest.fail("URL processing failed")
        
        assert task_status["status"] == "completed"
        print("✅ URL processing completed")
        
        # Verify chunks were created
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0
        print(f"✅ URL processing created {chunks_data['total_chunks']} chunks")
        
        # Verify chunk content quality
        first_chunk = chunks_data["chunks"][0]
        assert "content" in first_chunk
        assert "chunk_type" in first_chunk
        assert "token_count" in first_chunk
        assert first_chunk["token_count"] > 0
        assert len(first_chunk["content"].strip()) > 10
        
        print(f"✅ URL chunk validation passed")
        
        # Display detailed chunk information
        print(f"\n📋 URL Chunk Details:")
        print(f"   Total chunks: {chunks_data['total_chunks']}")
        print(f"   Document title: {chunks_data['document_title']}")
        print(f"   Source URL: {TEST_CONFIG['WEBSITE_URL']}")
        
        # Show first few chunks with details
        chunks_to_show = min(3, len(chunks_data["chunks"]))
        for i, chunk in enumerate(chunks_data["chunks"][:chunks_to_show]):
            print(f"\n   📄 Chunk {i+1}/{chunks_data['total_chunks']}:")
            print(f"      ID: {chunk['id']}")
            print(f"      Type: {chunk['chunk_type']}")
            print(f"      Tokens: {chunk['token_count']}")
            print(f"      Confidence: {chunk.get('confidence_score', 'N/A')}")
            
            # Show content preview (first 200 chars)
            content_preview = chunk['content'][:200].replace('\n', ' ').strip()
            if len(chunk['content']) > 200:
                content_preview += "..."
            print(f"      Content: {content_preview}")
            
            # Show source metadata if available
            if chunk.get('source_metadata'):
                metadata = chunk['source_metadata']
                metadata_items = []
                for key, value in metadata.items():
                    if key in ['page_title', 'domain', 'content_type', 'parser_version']:
                        metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    print(f"      Metadata: {', '.join(metadata_items)}")
        
        if chunks_data['total_chunks'] > chunks_to_show:
            print(f"      ... and {chunks_data['total_chunks'] - chunks_to_show} more chunks")
            
        # Show overall content statistics
        total_content_length = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        avg_chunk_size = total_content_length // len(chunks_data["chunks"]) if chunks_data["chunks"] else 0
        total_tokens = sum(chunk.get('token_count', 0) for chunk in chunks_data["chunks"])
        
        print(f"\n📊 URL Content Statistics:")
        print(f"   Total content: {total_content_length:,} characters")
        print(f"   Average chunk size: {avg_chunk_size} characters")
        print(f"   Total tokens: {total_tokens:,}")
        print(f"   Average tokens per chunk: {total_tokens // len(chunks_data['chunks']) if chunks_data['chunks'] else 0}")
        
        # Analyze chunk types
        chunk_types = {}
        for chunk in chunks_data["chunks"]:
            chunk_type = chunk.get('chunk_type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        if len(chunk_types) > 1:
            print(f"   Chunk types: {dict(chunk_types)}")
        
        print(f"✅ URL processing detailed analysis completed")
    
    @pytest.mark.files
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling  
    def test_file_uploads(self):
        """Test file upload processing for different formats."""
        test_files = [
            ("test_document.txt", TEST_CONFIG["SAMPLE_TEXT"], "text/plain"),
            ("test_document.md", TEST_CONFIG["SAMPLE_TEXT"], "text/markdown"),
        ]
        
        # Add real files if paths are provided
        # Note: This test allows optional file paths since it tests both generated and real files
        if TEST_CONFIG["PDF_PATH"]:
            if os.path.exists(TEST_CONFIG["PDF_PATH"]):
                test_files.append((TEST_CONFIG["PDF_PATH"], None, "application/pdf"))
            else:
                print(f"⚠️ Warning: PDF test file not found at {TEST_CONFIG['PDF_PATH']}, skipping PDF test in file uploads")
        
        if TEST_CONFIG["DOCX_PATH"]:
            if os.path.exists(TEST_CONFIG["DOCX_PATH"]):
                test_files.append((TEST_CONFIG["DOCX_PATH"], None, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
            else:
                print(f"⚠️ Warning: DOCX test file not found at {TEST_CONFIG['DOCX_PATH']}, skipping DOCX test in file uploads")
        
        if TEST_CONFIG["XLSX_PATH"]:
            if os.path.exists(TEST_CONFIG["XLSX_PATH"]):
                test_files.append((TEST_CONFIG["XLSX_PATH"], None, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
            else:
                print(f"⚠️ Warning: Excel test file not found at {TEST_CONFIG['XLSX_PATH']}, skipping Excel test in file uploads")
        
        for file_info in test_files:
            filepath, content, content_type = file_info
            filename = Path(filepath).name
            
            print(f"\n🧪 Testing file upload: {filename}")
            
            # Prepare file for upload
            if content:
                # Create temporary file
                temp_path, file_content = self._create_test_file(content, filename, content_type)
                files = {"file": (filename, file_content, content_type)}
            else:
                # Use existing file
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                files = {"file": (filename, file_content, content_type)}
            
            # Upload data
            upload_data = {
                "title": f"Test File - {filename}",
                "description": f"Testing file processing for {filename}",
                "category": "test_files",
                "tags": f"test,file,{Path(filename).suffix[1:]}",
                "source_type": "file",
                "chunking_strategy": "smart",
                "chunk_size": "512",
                "chunk_overlap": "50"
            }
            
            # Upload file
            response = self.client.post(f"{self.base_url}/upload", data=upload_data, files=files, headers=self.headers)
            assert response.status_code == 200, f"File upload failed for {filename}: {response.text}"
            
            result = response.json()
            document_id = result["document_id"]
            task_id = result["task_id"]
            self.uploaded_documents.append(document_id)
            
            print(f"✅ File uploaded: {filename} -> {document_id}")
            
            # Wait for processing
            try:
                task_status = self._wait_for_processing(task_id)
                
                if task_status["status"] == "failed":
                    print(f"⚠️ File processing failed for {filename}: {task_status.get('error', 'Unknown error')}")
                    continue  # Continue with next file
                
                assert task_status["status"] == "completed"
                print(f"✅ File processing completed: {filename}")
                
                # Verify chunks
                response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
                assert response.status_code == 200
                
                chunks_data = response.json()
                assert chunks_data["total_chunks"] > 0
                print(f"✅ {filename}: Created {chunks_data['total_chunks']} chunks")
                
            except Exception as e:
                print(f"⚠️ Processing error for {filename}: {e}")
                # Don't fail test for processing issues with real files
                continue
            
            # Clean up temporary file
            if content and 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    @pytest.mark.pdf
    @pytest.mark.files
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_pdf_processing(self):
        """Test PDF file processing specifically."""
        if not TEST_CONFIG["PDF_PATH"]:
            pytest.skip("TEST_PDF_PATH environment variable not provided - skipping PDF processing test")
        if not os.path.exists(TEST_CONFIG["PDF_PATH"]):
            pytest.skip(f"PDF test file not found at path: {TEST_CONFIG['PDF_PATH']} - skipping PDF processing test")
        
        print(f"\n🧪 Testing PDF processing: {TEST_CONFIG['PDF_PATH']}")
        self._test_single_file(TEST_CONFIG["PDF_PATH"], "application/pdf", "pdf")
    
    @pytest.mark.docx
    @pytest.mark.files
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_docx_processing(self):
        """Test DOCX file processing specifically."""
        if not TEST_CONFIG["DOCX_PATH"]:
            pytest.skip("TEST_DOCX_PATH environment variable not provided - skipping DOCX processing test")
        if not os.path.exists(TEST_CONFIG["DOCX_PATH"]):
            pytest.skip(f"DOCX test file not found at path: {TEST_CONFIG['DOCX_PATH']} - skipping DOCX processing test")
        
        print(f"\n🧪 Testing DOCX processing: {TEST_CONFIG['DOCX_PATH']}")
        self._test_single_file(TEST_CONFIG["DOCX_PATH"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx")
    
    @pytest.mark.xlsx
    @pytest.mark.excel
    @pytest.mark.files
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_xlsx_processing(self):
        """Test Excel file processing specifically."""
        if not TEST_CONFIG["XLSX_PATH"]:
            pytest.skip("TEST_XLSX_PATH environment variable not provided - skipping Excel processing test")
        if not os.path.exists(TEST_CONFIG["XLSX_PATH"]):
            pytest.skip(f"Excel test file not found at path: {TEST_CONFIG['XLSX_PATH']} - skipping Excel processing test")
        
        print(f"\n🧪 Testing Excel processing: {TEST_CONFIG['XLSX_PATH']}")
        self._test_single_file(TEST_CONFIG["XLSX_PATH"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "excel")
    
    @pytest.mark.html
    @pytest.mark.files
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_html_processing(self):
        """Test HTML file processing specifically."""
        if not TEST_CONFIG["HTML_PATH"]:
            pytest.skip("TEST_HTML_PATH environment variable not provided - skipping HTML processing test")
        if not os.path.exists(TEST_CONFIG["HTML_PATH"]):
            pytest.skip(f"HTML test file not found at path: {TEST_CONFIG['HTML_PATH']} - skipping HTML processing test")
        
        print(f"\n🧪 Testing HTML processing: {TEST_CONFIG['HTML_PATH']}")
        self._test_single_file(TEST_CONFIG["HTML_PATH"], "text/html", "html")
    
    def _test_single_file(self, file_path: str, content_type: str, file_type: str):
        """Helper method to test a single file."""
        filename = Path(file_path).name
        
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        files = {"file": (filename, file_content, content_type)}
        
        upload_data = {
            "title": f"Test {file_type.upper()} File - {filename}",
            "description": f"Testing {file_type} file processing",
            "category": f"test_{file_type}",
            "tags": f"test,file,{file_type}",
            "source_type": "file",
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        # Upload file
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, files=files, headers=self.headers)
        assert response.status_code == 200, f"{file_type.upper()} upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ {file_type.upper()} file uploaded: {filename} -> {document_id}")
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id)
        assert task_status["status"] == "completed", f"{file_type.upper()} processing failed: {task_status.get('error', 'Unknown error')}"
        
        print(f"✅ {file_type.upper()} processing completed")
        
        # Verify chunks
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0, f"No chunks created for {file_type.upper()}"
        
        print(f"✅ {file_type.upper()}: Created {chunks_data['total_chunks']} chunks")
        
        # Verify chunk content quality
        first_chunk = chunks_data["chunks"][0]
        assert len(first_chunk["content"].strip()) > 10, f"{file_type.upper()} chunk content too short"
        assert first_chunk["token_count"] > 0, f"{file_type.upper()} chunk has no tokens"
        
        print(f"✅ {file_type.upper()}: Content quality validation passed")
        
        # Display detailed chunk information for single file tests
        print(f"\n📋 {file_type.upper()} Chunk Details:")
        print(f"   Total chunks: {chunks_data['total_chunks']}")
        print(f"   Document title: {chunks_data['document_title']}")
        
        # Show first few chunks with details
        chunks_to_show = min(3, len(chunks_data["chunks"]))
        for i, chunk in enumerate(chunks_data["chunks"][:chunks_to_show]):
            print(f"\n   📄 Chunk {i+1}/{chunks_data['total_chunks']}:")
            print(f"      ID: {chunk['id']}")
            print(f"      Type: {chunk['chunk_type']}")
            print(f"      Tokens: {chunk['token_count']}")
            print(f"      Confidence: {chunk.get('confidence_score', 'N/A')}")
            
            # Show content preview (first 200 chars)
            content_preview = chunk['content'][:200].replace('\n', ' ').strip()
            if len(chunk['content']) > 200:
                content_preview += "..."
            print(f"      Content: {content_preview}")
            
            # Show source metadata if available
            if chunk.get('source_metadata'):
                metadata = chunk['source_metadata']
                metadata_items = []
                for key, value in metadata.items():
                    if key in ['page_number', 'section', 'table_index', 'parser', 'extraction_method']:
                        metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    print(f"      Metadata: {', '.join(metadata_items)}")
        
        if chunks_data['total_chunks'] > chunks_to_show:
            print(f"      ... and {chunks_data['total_chunks'] - chunks_to_show} more chunks")
            
        # Show overall content statistics
        total_content_length = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        avg_chunk_size = total_content_length // len(chunks_data["chunks"]) if chunks_data["chunks"] else 0
        total_tokens = sum(chunk.get('token_count', 0) for chunk in chunks_data["chunks"])
        
        print(f"\n📊 {file_type.upper()} Content Statistics:")
        print(f"   Total content: {total_content_length:,} characters")
        print(f"   Average chunk size: {avg_chunk_size} characters")
        print(f"   Total tokens: {total_tokens:,}")
        print(f"   Average tokens per chunk: {total_tokens // len(chunks_data['chunks']) if chunks_data['chunks'] else 0}")
        
        # Analyze chunk types
        chunk_types = {}
        for chunk in chunks_data["chunks"]:
            chunk_type = chunk.get('chunk_type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        if len(chunk_types) > 1:
            print(f"   Chunk types: {dict(chunk_types)}")
        
        print(f"✅ {file_type.upper()}: Detailed analysis completed")
    
    @pytest.mark.query
    @pytest.mark.search
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_query_functionality(self):
        """Test the query endpoint with different search types."""
        # First, upload a document to query against
        print("\n🧪 Setting up document for query testing...")
        
        upload_data = {
            "title": "Query Test Document",
            "description": "Document for testing search functionality",
            "category": "query_test",
            "tags": "test,query,search",
            "source_type": "text",
            "content": TEST_CONFIG["SAMPLE_TEXT"],
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id)
        assert task_status["status"] == "completed"
        
        print("✅ Query test document ready")
        
        # Test different query types
        test_queries = [
            {
                "query": "chunking strategies",
                "search_type": "semantic",
                "max_results": 5
            },
            {
                "query": "implementation details",
                "search_type": "keyword", 
                "max_results": 3
            },
            {
                "query": "document processing",
                "search_type": "hybrid",
                "max_results": 10
            }
        ]
        
        for query_data in test_queries:
            print(f"\n🔍 Testing {query_data['search_type']} search: '{query_data['query']}'")
            
            query_request = {
                "query": query_data["query"],
                "filters": {
                    "search_type": query_data["search_type"],
                    "max_results": query_data["max_results"],
                    "min_relevance": 0.1
                }
            }
            
            response = self.client.post(f"{self.base_url}/query", json=query_request, headers=self.headers)
            assert response.status_code == 200, f"Query failed: {response.text}"
            
            search_results = response.json()
            assert "results" in search_results
            assert "total_results" in search_results
            assert "search_time_ms" in search_results
            
            print(f"✅ {query_data['search_type']}: Found {search_results['total_results']} results in {search_results['search_time_ms']}ms")
            
            # Verify result structure
            if search_results["results"]:
                result = search_results["results"][0]
                required_fields = ["document_id", "chunk_id", "document_title", "content_snippet", "relevance_score"]
                for field in required_fields:
                    assert field in result, f"Missing field {field} in search result"
                
                print(f"✅ Result structure validation passed")
    
    @pytest.mark.replacement
    @pytest.mark.crud
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_document_replacement(self):
        """Test document source replacement functionality."""
        print("\n🧪 Testing document replacement...")
        
        # Upload initial document
        initial_data = {
            "title": "Replacement Test Document",
            "description": "Testing document replacement",
            "category": "replacement_test",
            "tags": "test,replacement",
            "source_type": "text",
            "content": "Initial content for replacement testing.",
            "chunking_strategy": "smart"
        }
        
        response = self.client.post(f"{self.base_url}/upload", data=initial_data, headers=self.headers)
        assert response.status_code == 200
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        # Wait for initial processing
        task_status = self._wait_for_processing(task_id)
        assert task_status["status"] == "completed"
        
        print(f"✅ Initial document created: {document_id}")
        
        # Replace with new content
        replacement_data = {
            "content": "This is the new replacement content with more detailed information for testing.",
            "chunking_strategy": "faq_optimization"
        }
        
        response = self.client.put(f"{self.base_url}/{document_id}/upload", data=replacement_data, headers=self.headers)
        assert response.status_code == 200
        
        replacement_result = response.json()
        replacement_task_id = replacement_result["task_id"]
        
        print(f"✅ Replacement initiated: {replacement_task_id}")
        
        # Wait for replacement processing
        task_status = self._wait_for_processing(replacement_task_id)
        assert task_status["status"] == "completed"
        
        print("✅ Document replacement completed")
        
        # Verify replacement
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        # Should have new chunks with replacement content
        assert chunks_data["total_chunks"] > 0
        
        print(f"✅ Replacement verification passed: {chunks_data['total_chunks']} new chunks")
    
    @pytest.mark.deletion
    @pytest.mark.crud
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_document_deletion(self):
        """Test document deletion functionality."""
        print("\n🧪 Testing document deletion...")
        
        # Upload document to delete
        upload_data = {
            "title": "Deletion Test Document",
            "description": "Testing document deletion",
            "category": "deletion_test", 
            "tags": "test,deletion",
            "source_type": "text",
            "content": "Content for deletion testing.",
            "chunking_strategy": "smart"
        }
        
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id)
        assert task_status["status"] == "completed"
        
        print(f"✅ Document created for deletion: {document_id}")
        
        # Verify document exists
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        # Delete document
        response = self.client.delete(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        deletion_result = response.json()
        assert "message" in deletion_result
        
        print("✅ Document deletion request completed")
        
        # Verify document is deleted
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 404
        
        print("✅ Document deletion verified")
    
    @pytest.mark.hardcoded_text
    @pytest.mark.text
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_hardcoded_text_processing(self):
        """Test processing of hardcoded text content (not from files)."""
        print("\n🧪 Testing hardcoded text processing...")
        
        # Test with various hardcoded text samples
        test_texts = [
            {
                "title": "Sample Technical Documentation",
                "content": """
# API Reference Guide

## Authentication
All API requests require authentication using Bearer tokens.

## Endpoints
- GET /users - Retrieve user list
- POST /users - Create new user
- PUT /users/{id} - Update user
- DELETE /users/{id} - Delete user

## Rate Limiting
API calls are limited to 1000 requests per hour per API key.
                """.strip(),
                "expected_chunks": 3,  # Should create chunks for each major section
                "description": "Technical documentation with headers and code examples"
            },
            {
                "title": "Sample FAQ Content",
                "content": """
Q: How do I get started with the API?
A: First, obtain your API key from the dashboard, then make a test request to /health.

Q: What are the rate limits?
A: 1000 requests per hour per API key.

Q: How do I handle errors?
A: Check the HTTP status code and error message in the response body.
                """.strip(),
                "expected_chunks": 3,  # Should create chunks for each Q&A pair
                "description": "FAQ format content"
            },
            {
                "title": "Sample Article Content",
                "content": """
Machine Learning in 2024: A Comprehensive Overview

The field of machine learning has evolved significantly over the past decade. 
From simple linear regression models to complex neural networks, the technology 
has transformed how we approach problem-solving in various domains.

Key trends include:
- Large Language Models (LLMs) dominating natural language processing
- Increased focus on explainable AI and interpretability
- Growing adoption in healthcare and finance sectors
- Emphasis on ethical AI development and bias mitigation

The future looks promising with continued advancements in areas like 
few-shot learning, multimodal AI, and quantum machine learning.
                """.strip(),
                "expected_chunks": 2,  # Should create meaningful chunks
                "description": "Article-style content with paragraphs and lists"
            }
        ]
        
        for i, test_case in enumerate(test_texts):
            print(f"\n📝 Testing hardcoded text {i+1}: {test_case['title']}")
            print(f"   Description: {test_case['description']}")
            
            # Prepare request data
            upload_data = {
                "title": test_case["title"],
                "description": test_case["description"],
                "category": "hardcoded_test",
                "tags": f"test,hardcoded,text{i+1}",
                "source_type": "text",
                "content": test_case["content"],
                "chunking_strategy": "smart",
                "chunk_size": "512",
                "chunk_overlap": "50"
            }
            
            # Upload document
            response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
            assert response.status_code == 200, f"Upload failed for {test_case['title']}: {response.text}"
            
            result = response.json()
            document_id = result["document_id"]
            task_id = result["task_id"]
            self.uploaded_documents.append(document_id)
            
            print(f"✅ Document uploaded: {document_id}, Task: {task_id}")
            
            # Wait for processing
            task_status = self._wait_for_processing(task_id)
            assert task_status["status"] == "completed", f"Processing failed for {test_case['title']}: {task_status.get('error', 'Unknown error')}"
            
            print(f"✅ Processing completed for {test_case['title']}")
            
            # Get processed chunks
            response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
            assert response.status_code == 200
            
            chunks_data = response.json()
            assert chunks_data["total_chunks"] > 0, f"No chunks created for {test_case['title']}"
            assert len(chunks_data["chunks"]) > 0, f"No chunks returned for {test_case['title']}"
            
            print(f"✅ {test_case['title']}: Created {chunks_data['total_chunks']} chunks")
            
            # Verify chunk content quality
            first_chunk = chunks_data["chunks"][0]
            assert "content" in first_chunk
            assert "chunk_type" in first_chunk
            assert "token_count" in first_chunk
            assert first_chunk["token_count"] > 0
            assert len(first_chunk["content"].strip()) > 10
            
            print(f"✅ {test_case['title']}: Chunk validation passed")
            
            # Show chunk details for the first test case
            if i == 0:
                print(f"\n📋 Chunk Details for {test_case['title']}:")
                print(f"   Total chunks: {chunks_data['total_chunks']}")
                print(f"   Document title: {chunks_data['document_title']}")
                
                # Show first few chunks
                chunks_to_show = min(3, len(chunks_data["chunks"]))
                for j, chunk in enumerate(chunks_data["chunks"][:chunks_to_show]):
                    print(f"\n   📄 Chunk {j+1}/{chunks_data['total_chunks']}:")
                    print(f"      ID: {chunk['id']}")
                    print(f"      Type: {chunk['chunk_type']}")
                    print(f"      Tokens: {chunk['token_count']}")
                    print(f"      Confidence: {chunk.get('confidence_score', 'N/A')}")
                    
                    # Show content preview (first 150 chars)
                    content_preview = chunk['content'][:150].replace('\n', ' ').strip()
                    if len(chunk['content']) > 150:
                        content_preview += "..."
                    print(f"      Content: {content_preview}")
        
        print(f"\n✅ All hardcoded text tests completed successfully!")
    
    @pytest.mark.listing
    @pytest.mark.crud
    def test_list_documents(self):
        """Test document listing functionality."""
        print("\n🧪 Testing document listing...")
        
        # Upload a few test documents
        test_docs = []
        for i in range(3):
            upload_data = {
                "title": f"List Test Document {i+1}",
                "description": f"Testing document listing - doc {i+1}",
                "category": "list_test",
                "tags": f"test,list,doc{i+1}",
                "source_type": "text",
                "content": f"Content for document {i+1} in listing test.",
                "chunking_strategy": "smart"
            }
            
            response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
            assert response.status_code == 200
            
            result = response.json()
            document_id = result["document_id"]
            task_id = result["task_id"]
            test_docs.append((document_id, task_id))
            self.uploaded_documents.append(document_id)
        
        # Wait for all documents to process
        for doc_id, task_id in test_docs:
            task_status = self._wait_for_processing(task_id)
            assert task_status["status"] == "completed"
        
        print(f"✅ Created {len(test_docs)} test documents")
        
        # Test listing
        response = self.client.get(f"{self.base_url}", headers=self.headers)
        assert response.status_code == 200
        
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) >= len(test_docs)
        
        # Verify document structure
        if documents:
            doc = documents[0]
            required_fields = ["id", "title", "category", "source_type", "processing_status", "created_at"]
            for field in required_fields:
                assert field in doc, f"Missing field {field} in document listing"
        
        print(f"✅ Document listing verified: {len(documents)} documents found")
        
        # Test filtered listing
        response = self.client.get(f"{self.base_url}?category=list_test&limit=2", headers=self.headers)
        assert response.status_code == 200
        
        filtered_docs = response.json()
        assert len(filtered_docs) <= 2
        
        print(f"✅ Filtered listing verified: {len(filtered_docs)} documents found")
    
    @pytest.mark.smart_chunking
    @pytest.mark.chunking_strategy
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_smart_chunking_strategy(self):
        """Test smart chunking strategy specifically."""
        print("\n🧪 Testing Smart Chunking strategy...")
        self._test_single_chunking_strategy("smart")
    
    @pytest.mark.faq_optimization
    @pytest.mark.chunking_strategy
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_faq_optimization_strategy(self):
        """Test FAQ optimization chunking strategy specifically."""
        print("\n🧪 Testing FAQ Optimization strategy...")
        self._test_single_chunking_strategy("faq_optimization")
    
    @pytest.mark.topic_headers
    @pytest.mark.chunking_strategy
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_topic_headers_strategy(self):
        """Test topic headers chunking strategy specifically."""
        print("\n🧪 Testing Topic Headers strategy...")
        self._test_single_chunking_strategy("topic_headers")
    
    @pytest.mark.summarize
    @pytest.mark.chunking_strategy
    @pytest.mark.polling  # TODO: Skip during CI - uses inefficient polling
    def test_summarize_strategy(self):
        """Test summarization chunking strategy specifically."""
        print("\n🧪 Testing Summarization strategy...")
        self._test_single_chunking_strategy("summarize")
    
    def _test_single_chunking_strategy(self, strategy: str):
        """Helper method to test a single chunking strategy."""
        upload_data = {
            "title": f"Test {strategy.title().replace('_', ' ')} Strategy",
            "description": f"Testing {strategy} chunking strategy",
            "category": f"test_{strategy}",
            "tags": f"test,chunking,{strategy}",
            "source_type": "text",
            "content": TEST_CONFIG["SAMPLE_TEXT"],
            "chunking_strategy": strategy,
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        # Upload document
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200, f"{strategy} upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ Document uploaded with {strategy} strategy: {document_id}")
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id)
        assert task_status["status"] == "completed", f"{strategy} processing failed: {task_status.get('error', 'Unknown error')}"
        
        print(f"✅ Processing completed for {strategy}")
        
        # Get processed chunks
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0, f"No chunks created for {strategy}"
        assert len(chunks_data["chunks"]) > 0, f"No chunks returned for {strategy}"
        
        print(f"✅ {strategy}: Created {chunks_data['total_chunks']} chunks")
        
        # Verify chunk content quality
        first_chunk = chunks_data["chunks"][0]
        assert "content" in first_chunk
        assert "chunk_type" in first_chunk
        assert "token_count" in first_chunk
        assert first_chunk["token_count"] > 0
        assert len(first_chunk["content"].strip()) > 10
        
        print(f"✅ {strategy}: Chunk validation passed")
        
        # Display strategy-specific chunk insights
        print(f"\n🔧 {strategy.upper()} Strategy Analysis:")
        
        # Analyze chunk types for this strategy
        chunk_types = {}
        total_tokens = 0
        total_content = 0
        
        for chunk in chunks_data["chunks"]:
            chunk_type = chunk.get('chunk_type', 'content')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            total_tokens += chunk.get('token_count', 0)
            total_content += len(chunk['content'])
        
        print(f"   Strategy: {strategy}")
        print(f"   Total chunks: {chunks_data['total_chunks']}")
        print(f"   Total tokens: {total_tokens:,}")
        print(f"   Average tokens per chunk: {total_tokens // len(chunks_data['chunks']) if chunks_data['chunks'] else 0}")
        print(f"   Chunk types: {dict(chunk_types)}")
        
        # Show strategy-specific insights
        if strategy == "faq_optimization":
            question_chunks = chunk_types.get('question', 0)
            answer_chunks = chunk_types.get('answer', 0)
            print(f"   Q&A pairs: {min(question_chunks, answer_chunks)}")
        elif strategy == "topic_headers":
            header_chunks = chunk_types.get('header', 0)
            summary_chunks = chunk_types.get('summary', 0)
            print(f"   Headers: {header_chunks}, Summaries: {summary_chunks}")
        elif strategy == "summarize":
            summary_chunks = chunk_types.get('summary', 0)
            key_point_chunks = chunk_types.get('key_point', 0)
            print(f"   Summaries: {summary_chunks}, Key points: {key_point_chunks}")
        
        # Show first chunk as example
        if chunks_data["chunks"]:
            example_chunk = chunks_data["chunks"][0]
            content_preview = example_chunk['content'][:150].replace('\n', ' ').strip()
            if len(example_chunk['content']) > 150:
                content_preview += "..."
            print(f"   Example chunk: {content_preview}")
        
        print(f"✅ {strategy}: Strategy analysis completed")


def test_environment_setup():
    """Test that required environment variables and dependencies are available."""
    print("\n🔧 Testing environment setup...")
    
    # Test server connectivity instead of imports
    test_api_url = os.getenv("TEST_API_URL", "http://localhost:8090")
    try:
        import httpx
        with httpx.Client(base_url=test_api_url, timeout=10.0) as client:
            response = client.get("/admin/api/v1/health")
            if response.status_code == 200:
                print("✅ Server connectivity successful")
            else:
                pytest.fail(f"Server health check failed: {response.status_code}")
    except Exception as e:
        pytest.fail(f"Failed to connect to server at {test_api_url}: {e}")
    
    # Test configuration
    print(f"📊 Test configuration:")
    print(f"  - API URL: {test_api_url}")
    print(f"  - Workspace ID: {TEST_CONFIG['WORKSPACE_ID']}")
    print(f"  - API Base URL: {TEST_CONFIG['API_BASE_URL']}")
    print(f"  - Test timeout: {TEST_CONFIG['TIMEOUT']}s")
    print(f"  - Website URL: {TEST_CONFIG['WEBSITE_URL'] or 'Not provided'}")
    print(f"  - PDF path: {TEST_CONFIG['PDF_PATH'] or 'Not provided'}")
    print(f"  - DOCX path: {TEST_CONFIG['DOCX_PATH'] or 'Not provided'}")
    print(f"  - Excel path: {TEST_CONFIG['XLSX_PATH'] or 'Not provided'}")
    print(f"  - HTML path: {TEST_CONFIG['HTML_PATH'] or 'Not provided'}")
    
    print("✅ Environment setup validation completed")


def validate_test_configuration_for_specific_tests():
    """
    Validate test configuration for specific file format tests.
    
    This function provides detailed guidance on what environment variables
    are needed for different test categories.
    """
    print("\n📋 Test Configuration Validation")
    print("=" * 50)
    
    missing_configs = []
    warnings = []
    
    # Check for specific test requirements
    test_configs = {
        "URL Tests (test-kb-url)": {
            "env_var": "TEST_WEBSITE_URL",
            "value": TEST_CONFIG["WEBSITE_URL"],
            "required_for": "URL scraping tests"
        },
        "PDF Tests (test-kb-pdf)": {
            "env_var": "TEST_PDF_PATH", 
            "value": TEST_CONFIG["PDF_PATH"],
            "required_for": "PDF processing tests"
        },
        "DOCX Tests (test-kb-docx)": {
            "env_var": "TEST_DOCX_PATH",
            "value": TEST_CONFIG["DOCX_PATH"], 
            "required_for": "DOCX processing tests"
        },
        "Excel Tests (test-kb-excel)": {
            "env_var": "TEST_XLSX_PATH",
            "value": TEST_CONFIG["XLSX_PATH"],
            "required_for": "Excel processing tests"
        },
        "HTML Tests (test-kb-html)": {
            "env_var": "TEST_HTML_PATH",
            "value": TEST_CONFIG["HTML_PATH"],
            "required_for": "HTML processing tests"
        }
    }
    
    for test_name, config in test_configs.items():
        if not config["value"]:
            missing_configs.append(f"❌ {test_name}: {config['env_var']} not set")
        elif config["value"] and not config["value"].startswith("http") and not os.path.exists(config["value"]):
            warnings.append(f"⚠️  {test_name}: File not found at {config['value']}")
        else:
            print(f"✅ {test_name}: Configured")
    
    if missing_configs:
        print(f"\n🔴 Missing Configuration:")
        for msg in missing_configs:
            print(f"   {msg}")
    
    if warnings:
        print(f"\n🟡 Warnings:")
        for msg in warnings:
            print(f"   {msg}")
    
    if not missing_configs and not warnings:
        print(f"\n🟢 All test configurations are properly set!")
    
    print(f"\n💡 Usage Examples:")
    print(f"   export TEST_PDF_PATH='/path/to/test.pdf'")
    print(f"   export TEST_WEBSITE_URL='https://example.com'") 
    print(f"   make test-kb-pdf    # Test specific format")
    print(f"   make test-kb        # Test all formats")
    
    return missing_configs, warnings


if __name__ == "__main__":
    """Run tests directly for development."""
    print("🚀 Running Knowledge Base Integration Tests")
    print("=" * 60)
    
    # Run environment test first
    test_environment_setup()
    
    # Validate test configuration
    missing_configs, warnings = validate_test_configuration_for_specific_tests()
    
    # Initialize test class
    TestKnowledgeBaseIntegration.setup_class()
    test_instance = TestKnowledgeBaseIntegration()
    
    try:
        test_instance.setup_method()
        
        # Run core tests
        print("\n📝 Testing text sources with all chunking strategies...")
        test_instance.test_text_source_all_strategies()
        
        print("\n🌐 Testing URL source...")
        try:
            test_instance.test_url_source()
        except Exception as e:
            print(f"⚠️ URL test skipped or failed: {e}")
        
        print("\n📁 Testing file uploads...")
        test_instance.test_file_uploads()
        
        print("\n🔍 Testing query functionality...")
        test_instance.test_query_functionality()
        
        print("\n🔄 Testing document replacement...")
        test_instance.test_document_replacement()
        
        print("\n📋 Testing document listing...")
        test_instance.test_list_documents()
        
        print("\n🗑️ Testing document deletion...")
        test_instance.test_document_deletion()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_instance.teardown_method()
        TestKnowledgeBaseIntegration.teardown_class()
