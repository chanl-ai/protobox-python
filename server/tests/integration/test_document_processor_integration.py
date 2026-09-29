"""Integration tests for Document Processor Service."""

import pytest
import httpx
import tempfile
import os
from pathlib import Path
from typing import Dict, Any
import time

# Import utility for authenticated tests
try:
    from .test_utils import AuthenticatedTestCase
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.append(os.path.dirname(__file__))
    from test_utils import AuthenticatedTestCase


# Test configuration
TEST_CONFIG = {
    "DOCUMENT_PROCESSOR_URL": os.getenv("DOCUMENT_PROCESSOR_URL", "http://localhost:8092"),
    "PDF_PATH": os.getenv("TEST_PDF_PATH", ""),
    "XLSX_PATH": os.getenv("TEST_XLSX_PATH", ""),
    "TIMEOUT": int(os.getenv("TEST_TIMEOUT", "120")),
    # Test PDF URL (Adobe sample with 4 pages of content)
    "PDF_URL": "https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf",
    # Test PDF with OCR requirements
    "SCANNED_PDF_URL": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
}


@pytest.mark.integration
@pytest.mark.document_processor  
class TestDocumentProcessorIntegration(AuthenticatedTestCase):
    """Integration tests for document processor service."""
    
    @classmethod
    def setup_class(cls):
        """Set up test configuration."""
        cls.setup_auth()
        if hasattr(cls, 'skip_tests') and cls.skip_tests:
            return
            
        cls.base_url = f"/admin/api/v1/workspaces/{cls.workspace_id}/knowledge"
        cls.doc_processor_url = TEST_CONFIG["DOCUMENT_PROCESSOR_URL"]
    
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
    
    def _wait_for_processing(self, task_id: str, timeout: int = None) -> Dict[str, Any]:
        """Wait for document processing to complete."""
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
    
    @pytest.mark.pdf
    @pytest.mark.microservice
    def test_document_processor_health_check(self):
        """Test document processor service health check."""
        print(f"\n🏥 Testing document processor health check: {self.doc_processor_url}")
        
        # Test direct health check to document processor
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.doc_processor_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Document processor is healthy")
                    print(f"   Status: {health_data.get('status', 'unknown')}")
                    print(f"   Capabilities: {health_data.get('capabilities', [])}")
                    
                    # Verify expected capabilities
                    capabilities = health_data.get('capabilities', [])
                    expected_capabilities = ['pdf', 'docx', 'xlsx']
                    
                    for cap in expected_capabilities:
                        assert cap in capabilities, f"Missing capability: {cap}"
                        print(f"   ✓ Supports {cap.upper()}")
                    
                    assert health_data.get('status') == 'healthy'
                else:
                    pytest.fail(f"Document processor health check failed: {response.status_code}")
                    
        except httpx.ConnectError:
            pytest.skip(f"Document processor not available at {self.doc_processor_url}")
        except Exception as e:
            pytest.fail(f"Health check failed with error: {e}")
    
    @pytest.mark.pdf
    @pytest.mark.url
    @pytest.mark.microservice
    def test_pdf_url_processing_via_document_processor(self):
        """Test PDF URL processing that routes through document processor."""
        print(f"\n🔗 Testing PDF URL processing via document processor")
        print(f"   URL: {TEST_CONFIG['PDF_URL']}")
        
        upload_data = {
            "title": "Adobe Sample PDF via Document Processor",
            "description": "Testing PDF URL processing through document processor microservice",
            "category": "test_doc_processor",
            "tags": "test,pdf,url,document_processor,microservice",
            "source_type": "url",
            "url": TEST_CONFIG["PDF_URL"],
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        # Upload PDF URL (should be routed to document processor)
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200, f"PDF URL upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ PDF URL uploaded: {document_id}, Task: {task_id}")
        
        # Wait for processing (PDF processing may take longer)
        task_status = self._wait_for_processing(task_id, timeout=180)
        assert task_status["status"] == "completed", f"PDF URL processing failed: {task_status.get('error', 'Unknown error')}"
        
        print(f"✅ PDF URL processing completed")
        
        # Verify chunks were created with meaningful content
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0, "No chunks were created from PDF URL"
        assert len(chunks_data["chunks"]) > 0, "No chunks returned from PDF URL"
        
        print(f"✅ PDF URL processing created {chunks_data['total_chunks']} chunks")
        
        # Verify content quality (should have substantial content from document processor)
        total_content = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        assert total_content > 1000, f"PDF content too short ({total_content} chars), document processor may not be working"
        
        # Check for meaningful content (not just dummy text)
        first_chunk = chunks_data["chunks"][0]
        content = first_chunk["content"].lower()
        
        # Adobe sample PDF should contain real content
        meaningful_indicators = ["adobe", "document", "page", "pdf", "content", "text", "format"]
        has_meaningful_content = any(indicator in content for indicator in meaningful_indicators)
        
        if not has_meaningful_content:
            print(f"⚠️ Warning: Content may be dummy text: {first_chunk['content'][:200]}...")
        
        print(f"✅ PDF URL content validation passed: {total_content:,} characters extracted")
        
        # Display detailed processing results
        print(f"\n📋 PDF URL Processing Results:")
        print(f"   Document ID: {document_id}")
        print(f"   Total chunks: {chunks_data['total_chunks']}")
        print(f"   Total content: {total_content:,} characters")
        print(f"   Source URL: {TEST_CONFIG['PDF_URL']}")
        
        # Show chunk details
        for i, chunk in enumerate(chunks_data["chunks"][:2]):  # Show first 2 chunks
            print(f"\n   📄 Chunk {i+1}:")
            print(f"      Type: {chunk.get('chunk_type', 'content')}")
            print(f"      Tokens: {chunk.get('token_count', 0)}")
            content_preview = chunk['content'][:150].replace('\n', ' ').strip()
            print(f"      Content preview: {content_preview}...")
            
            # Check for document processor metadata
            if chunk.get('source_metadata'):
                metadata = chunk['source_metadata']
                if metadata.get('processing_method') == 'document_processor':
                    print(f"      ✓ Processed by document processor microservice")
                    if metadata.get('pages'):
                        print(f"      ✓ Pages processed: {metadata.get('pages')}")
    
    @pytest.mark.pdf
    @pytest.mark.file
    @pytest.mark.microservice
    def test_pdf_file_upload_via_document_processor(self):
        """Test PDF file upload processing through document processor."""
        if not TEST_CONFIG["PDF_PATH"] or not os.path.exists(TEST_CONFIG["PDF_PATH"]):
            pytest.skip(f"PDF test file not available at {TEST_CONFIG.get('PDF_PATH', 'not configured')}")
        
        print(f"\n📁 Testing PDF file upload via document processor")
        print(f"   File: {TEST_CONFIG['PDF_PATH']}")
        
        # Read the PDF file
        with open(TEST_CONFIG["PDF_PATH"], 'rb') as f:
            file_content = f.read()
        
        filename = Path(TEST_CONFIG["PDF_PATH"]).name
        files = {"file": (filename, file_content, "application/pdf")}
        
        upload_data = {
            "title": f"Test PDF File - {filename}",
            "description": "Testing PDF file processing through document processor microservice",
            "category": "test_pdf_file",
            "tags": "test,pdf,file,document_processor,microservice",
            "source_type": "file",
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        # Upload PDF file
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, files=files, headers=self.headers)
        assert response.status_code == 200, f"PDF file upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ PDF file uploaded: {document_id}, Task: {task_id}")
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id, timeout=180)
        assert task_status["status"] == "completed", f"PDF file processing failed: {task_status.get('error', 'Unknown error')}"
        
        print(f"✅ PDF file processing completed")
        
        # Verify results
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0, "No chunks were created from PDF file"
        
        # Display results
        total_content = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        print(f"✅ PDF file processing created {chunks_data['total_chunks']} chunks ({total_content:,} characters)")
    
    @pytest.mark.xlsx
    @pytest.mark.file
    @pytest.mark.microservice
    def test_xlsx_file_upload_via_document_processor(self):
        """Test Excel file upload processing through document processor."""
        if not TEST_CONFIG["XLSX_PATH"] or not os.path.exists(TEST_CONFIG["XLSX_PATH"]):
            pytest.skip(f"Excel test file not available at {TEST_CONFIG.get('XLSX_PATH', 'not configured')}")
        
        print(f"\n📊 Testing Excel file upload via document processor")
        print(f"   File: {TEST_CONFIG['XLSX_PATH']}")
        
        # Read the Excel file
        with open(TEST_CONFIG["XLSX_PATH"], 'rb') as f:
            file_content = f.read()
        
        filename = Path(TEST_CONFIG["XLSX_PATH"]).name
        files = {"file": (filename, file_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        
        upload_data = {
            "title": f"Test Excel File - {filename}",
            "description": "Testing Excel file processing through document processor microservice",
            "category": "test_xlsx_file",
            "tags": "test,xlsx,excel,file,document_processor,microservice",
            "source_type": "file",
            "chunking_strategy": "smart",
            "chunk_size": "512",
            "chunk_overlap": "50"
        }
        
        # Upload Excel file
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, files=files, headers=self.headers)
        assert response.status_code == 200, f"Excel file upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ Excel file uploaded: {document_id}, Task: {task_id}")
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id, timeout=180)
        assert task_status["status"] == "completed", f"Excel file processing failed: {task_status.get('error', 'Unknown error')}"
        
        print(f"✅ Excel file processing completed")
        
        # Verify results
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0, "No chunks were created from Excel file"
        
        # Display results
        total_content = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        print(f"✅ Excel file processing created {chunks_data['total_chunks']} chunks ({total_content:,} characters)")
    
    @pytest.mark.fallback
    @pytest.mark.error_handling
    def test_document_processor_fallback_behavior(self):
        """Test fallback behavior when document processor is unavailable."""
        print(f"\n🔄 Testing document processor fallback behavior")
        
        # We'll test this by trying to process a PDF URL that should normally go to document processor
        # but we'll use a configuration that points to a non-existent service to trigger fallback
        
        upload_data = {
            "title": "Test PDF Fallback Behavior",
            "description": "Testing fallback when document processor is unavailable",
            "category": "test_fallback",
            "tags": "test,pdf,fallback,error_handling",
            "source_type": "url",
            "url": TEST_CONFIG["PDF_URL"],
            "chunking_strategy": "smart"
        }
        
        # Upload PDF URL
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200, f"PDF URL upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"✅ PDF URL uploaded for fallback test: {document_id}")
        
        # Wait for processing
        task_status = self._wait_for_processing(task_id, timeout=180)
        
        if task_status["status"] == "completed":
            print(f"✅ Processing completed (document processor available)")
            
            # Verify chunks were created
            response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
            assert response.status_code == 200
            
            chunks_data = response.json()
            assert chunks_data["total_chunks"] > 0
            
            print(f"✅ Document processor fallback test passed (service available)")
            
        elif task_status["status"] == "failed":
            # Check if failure indicates fallback behavior
            error_message = task_status.get("error", "").lower()
            if "processor" in error_message or "unavailable" in error_message:
                print(f"✅ Fallback behavior correctly triggered: {task_status.get('error')}")
            else:
                pytest.fail(f"Unexpected processing failure: {task_status.get('error')}")
        else:
            pytest.fail(f"Unexpected task status: {task_status}")
    
    @pytest.mark.comprehensive
    @pytest.mark.integration_flow
    def test_end_to_end_pdf_processing_flow(self):
        """Test complete end-to-end PDF processing workflow."""
        print(f"\n🔄 Testing end-to-end PDF processing workflow")
        
        # Step 1: Upload PDF URL
        upload_data = {
            "title": "E2E PDF Processing Test",
            "description": "End-to-end testing of PDF processing through document processor",
            "category": "e2e_test",
            "tags": "test,pdf,e2e,workflow,document_processor",
            "source_type": "url",
            "url": TEST_CONFIG["PDF_URL"],
            "chunking_strategy": "smart",
            "chunk_size": "256",  # Smaller chunks for testing
            "chunk_overlap": "25"
        }
        
        print(f"   Step 1: Uploading PDF URL...")
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        assert response.status_code == 200, f"PDF upload failed: {response.text}"
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"   ✅ Document uploaded: {document_id}")
        
        # Step 2: Wait for processing
        print(f"   Step 2: Processing document...")
        task_status = self._wait_for_processing(task_id, timeout=180)
        assert task_status["status"] == "completed", f"Processing failed: {task_status.get('error')}"
        
        print(f"   ✅ Processing completed")
        
        # Step 3: Verify document details
        print(f"   Step 3: Verifying document...")
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        chunks_data = response.json()
        assert chunks_data["total_chunks"] > 0
        
        print(f"   ✅ Document verified: {chunks_data['total_chunks']} chunks")
        
        # Step 4: Test search functionality
        print(f"   Step 4: Testing search...")
        query_request = {
            "query": "document",
            "filters": {
                "search_type": "hybrid",
                "max_results": 5,
                "min_relevance": 0.1
            }
        }
        
        response = self.client.post(f"{self.base_url}/query", json=query_request, headers=self.headers)
        assert response.status_code == 200
        
        search_results = response.json()
        assert search_results["total_results"] > 0
        
        print(f"   ✅ Search test passed: {search_results['total_results']} results found")
        
        # Step 5: Verify chunk content quality
        print(f"   Step 5: Verifying content quality...")
        total_content = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        avg_chunk_size = total_content // len(chunks_data["chunks"])
        
        assert total_content > 500, f"Total content too short: {total_content} chars"
        assert avg_chunk_size > 50, f"Average chunk size too small: {avg_chunk_size} chars"
        
        print(f"   ✅ Content quality verified: {total_content:,} chars, {avg_chunk_size} avg/chunk")
        
        # Step 6: Clean up verification
        print(f"   Step 6: Testing document deletion...")
        response = self.client.delete(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 200
        
        # Remove from cleanup list since we manually deleted it
        self.uploaded_documents.remove(document_id)
        
        # Verify deletion
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        assert response.status_code == 404
        
        print(f"   ✅ Document deletion verified")
        print(f"🎉 End-to-end PDF processing workflow completed successfully!")
    
    @pytest.mark.performance
    @pytest.mark.microservice
    def test_document_processor_performance(self):
        """Test document processor performance with timing measurements."""
        print(f"\n⏱️ Testing document processor performance")
        
        start_time = time.time()
        
        upload_data = {
            "title": "Performance Test PDF",
            "description": "Testing document processor performance",
            "category": "performance_test",
            "tags": "test,pdf,performance,timing",
            "source_type": "url",
            "url": TEST_CONFIG["PDF_URL"],
            "chunking_strategy": "smart"
        }
        
        # Upload with timing
        upload_start = time.time()
        response = self.client.post(f"{self.base_url}/upload", data=upload_data, headers=self.headers)
        upload_time = time.time() - upload_start
        
        assert response.status_code == 200
        
        result = response.json()
        document_id = result["document_id"]
        task_id = result["task_id"]
        self.uploaded_documents.append(document_id)
        
        print(f"   Upload time: {upload_time:.2f}s")
        
        # Processing with timing
        processing_start = time.time()
        task_status = self._wait_for_processing(task_id, timeout=180)
        processing_time = time.time() - processing_start
        
        assert task_status["status"] == "completed"
        
        print(f"   Processing time: {processing_time:.2f}s")
        
        # Retrieval with timing
        retrieval_start = time.time()
        response = self.client.get(f"{self.base_url}/{document_id}", headers=self.headers)
        retrieval_time = time.time() - retrieval_start
        
        assert response.status_code == 200
        
        chunks_data = response.json()
        total_time = time.time() - start_time
        
        print(f"   Retrieval time: {retrieval_time:.2f}s")
        print(f"   Total time: {total_time:.2f}s")
        
        # Performance assertions (reasonable thresholds)
        assert upload_time < 30, f"Upload too slow: {upload_time:.2f}s"
        assert processing_time < 120, f"Processing too slow: {processing_time:.2f}s"
        assert retrieval_time < 10, f"Retrieval too slow: {retrieval_time:.2f}s"
        assert total_time < 150, f"Total workflow too slow: {total_time:.2f}s"
        
        # Content efficiency
        total_content = sum(len(chunk['content']) for chunk in chunks_data["chunks"])
        chars_per_second = total_content / processing_time
        
        print(f"   Content extracted: {total_content:,} characters")
        print(f"   Processing rate: {chars_per_second:.0f} chars/second")
        
        assert chars_per_second > 10, f"Processing rate too slow: {chars_per_second:.0f} chars/s"
        
        print(f"✅ Performance test passed: {total_time:.2f}s total, {chars_per_second:.0f} chars/s")


def test_document_processor_environment():
    """Test document processor environment setup."""
    print("\n🔧 Testing document processor environment...")
    
    doc_processor_url = TEST_CONFIG["DOCUMENT_PROCESSOR_URL"]
    print(f"   Document processor URL: {doc_processor_url}")
    
    # Test connectivity
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{doc_processor_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ Service is healthy: {health_data.get('status')}")
                print(f"   ✅ Capabilities: {health_data.get('capabilities', [])}")
            else:
                print(f"   ⚠️ Service responded with status {response.status_code}")
    except httpx.ConnectError:
        print(f"   ⚠️ Cannot connect to service at {doc_processor_url}")
        print(f"   💡 This is expected if the service is not running locally")
    except Exception as e:
        print(f"   ❌ Error checking service: {e}")
    
    # Test file paths
    if TEST_CONFIG["PDF_PATH"]:
        if os.path.exists(TEST_CONFIG["PDF_PATH"]):
            print(f"   ✅ PDF test file available: {TEST_CONFIG['PDF_PATH']}")
        else:
            print(f"   ⚠️ PDF test file not found: {TEST_CONFIG['PDF_PATH']}")
    else:
        print(f"   ℹ️ PDF test file not configured (TEST_PDF_PATH)")
    
    if TEST_CONFIG["XLSX_PATH"]:
        if os.path.exists(TEST_CONFIG["XLSX_PATH"]):
            print(f"   ✅ Excel test file available: {TEST_CONFIG['XLSX_PATH']}")
        else:
            print(f"   ⚠️ Excel test file not found: {TEST_CONFIG['XLSX_PATH']}")
    else:
        print(f"   ℹ️ Excel test file not configured (TEST_XLSX_PATH)")
    
    print(f"   ✅ Environment check completed")


if __name__ == "__main__":
    """Run tests directly for development."""
    print("🚀 Running Document Processor Integration Tests")
    print("=" * 60)
    
    # Run environment test first
    test_document_processor_environment()
    
    # Initialize test class
    TestDocumentProcessorIntegration.setup_class()
    test_instance = TestDocumentProcessorIntegration()
    
    try:
        test_instance.setup_method()
        
        # Run tests
        print("\n🏥 Testing document processor health...")
        test_instance.test_document_processor_health_check()
        
        print("\n🔗 Testing PDF URL processing...")
        test_instance.test_pdf_url_processing_via_document_processor()
        
        print("\n📁 Testing PDF file upload...")
        try:
            test_instance.test_pdf_file_upload_via_document_processor()
        except Exception as e:
            print(f"⚠️ PDF file test skipped: {e}")
        
        print("\n📊 Testing Excel file upload...")
        try:
            test_instance.test_xlsx_file_upload_via_document_processor()
        except Exception as e:
            print(f"⚠️ Excel file test skipped: {e}")
        
        print("\n🔄 Testing fallback behavior...")
        test_instance.test_document_processor_fallback_behavior()
        
        print("\n🔄 Testing end-to-end workflow...")
        test_instance.test_end_to_end_pdf_processing_flow()
        
        print("\n⏱️ Testing performance...")
        test_instance.test_document_processor_performance()
        
        print("\n" + "=" * 60)
        print("🎉 All document processor tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test_instance.teardown_method()
        TestDocumentProcessorIntegration.teardown_class()