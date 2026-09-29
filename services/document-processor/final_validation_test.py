#!/usr/bin/env python3
"""
Final comprehensive validation test for Document Processor Service.
This test validates all core functionality is working correctly.
"""

import json
import time
import httpx
import asyncio
from pathlib import Path

SERVICE_URL = "http://localhost:8092"
VALID_API_KEY = "test-api-key-12345"

class DocumentProcessorValidator:
    def __init__(self):
        self.base_url = SERVICE_URL
        self.api_key = VALID_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    async def test_service_health(self):
        """Validate service is healthy and responsive."""
        print("🏥 Testing service health...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/health")
            
            if response.status_code != 200:
                print(f"❌ Health check failed: {response.status_code}")
                return False
            
            data = response.json()
            required_fields = ['status', 'capabilities', 'max_file_size', 'version']
            
            for field in required_fields:
                if field not in data:
                    print(f"❌ Missing field in health response: {field}")
                    return False
            
            if data['status'] != 'healthy':
                print(f"❌ Service not healthy: {data['status']}")
                return False
            
            expected_capabilities = ['pdf', 'docx', 'xlsx', 'txt', 'md']
            for cap in expected_capabilities:
                if cap not in data['capabilities']:
                    print(f"❌ Missing capability: {cap}")
                    return False
            
            print(f"✅ Service healthy with {len(data['capabilities'])} capabilities")
            print(f"   Max file size: {data['max_file_size']:,} bytes")
            print(f"   Version: {data['version']}")
            return True
    
    async def test_authentication(self):
        """Validate API key authentication works correctly."""
        print("🔐 Testing authentication...")
        
        test_data = {
            "signed_url": "https://httpbin.org/json",
            "file_type": "json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test without auth
            response = await client.post(f"{self.base_url}/v1/process", json=test_data)
            if response.status_code != 401:
                print(f"❌ Expected 401 without auth, got {response.status_code}")
                return False
            
            # Test with wrong auth
            wrong_headers = {"Authorization": "Bearer wrong-key"}
            response = await client.post(f"{self.base_url}/v1/process", json=test_data, headers=wrong_headers)
            if response.status_code != 401:
                print(f"❌ Expected 401 with wrong auth, got {response.status_code}")
                return False
            
            print("✅ Authentication working correctly")
            return True
    
    async def test_pdf_processing(self):
        """Validate PDF processing with real file."""
        print("📄 Testing PDF processing...")
        
        test_data = {
            "signed_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "file_type": "pdf",
            "options": {
                "use_ocr": True,
                "extract_tables": True,
                "extract_images": False
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            start_time = time.time()
            response = await client.post(
                f"{self.base_url}/v1/process", 
                json=test_data, 
                headers=self.headers
            )
            processing_time = time.time() - start_time
            
            if response.status_code != 200:
                print(f"❌ PDF processing failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False
            
            result = response.json()
            required_fields = ['status', 'content', 'metadata', 'processing_time']
            
            for field in required_fields:
                if field not in result:
                    print(f"❌ Missing field in response: {field}")
                    return False
            
            if result['status'] != 'success':
                print(f"❌ Processing not successful: {result['status']}")
                return False
            
            content = result.get('content', '')
            if not content or len(content) == 0:
                print("❌ No content extracted from PDF")
                return False
            
            metadata = result.get('metadata', {})
            if 'pages' not in metadata:
                print("❌ No page count in metadata")
                return False
            
            print(f"✅ PDF processed successfully")
            print(f"   Content: {len(content)} chars - '{content[:50]}{'...' if len(content) > 50 else ''}'")
            print(f"   Pages: {metadata.get('pages')}")
            print(f"   Processing time: {result.get('processing_time'):.2f}s")
            print(f"   Total time: {processing_time:.2f}s")
            return True
    
    async def test_error_handling(self):
        """Validate proper error handling."""
        print("⚠️ Testing error handling...")
        
        test_cases = [
            {
                "name": "Invalid URL",
                "data": {"signed_url": "not-a-url", "file_type": "pdf"},
                "expected_status": [400, 500]
            },
            {
                "name": "Unsupported file type",
                "data": {"signed_url": "https://httpbin.org/json", "file_type": "exe"},
                "expected_status": [400, 500]
            },
            {
                "name": "Missing signed_url",
                "data": {"file_type": "pdf"},
                "expected_status": [422]
            }
        ]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for test_case in test_cases:
                response = await client.post(
                    f"{self.base_url}/v1/process",
                    json=test_case["data"],
                    headers=self.headers
                )
                
                if response.status_code not in test_case["expected_status"]:
                    print(f"❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status_code}")
                    return False
            
            print("✅ Error handling working correctly")
            return True
    
    async def test_performance(self):
        """Validate performance meets requirements."""
        print("⚡ Testing performance...")
        
        test_data = {
            "signed_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            "file_type": "pdf",
            "options": {"use_ocr": False, "extract_tables": False}  # Faster processing
        }
        
        times = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Run 3 tests to get average
            for i in range(3):
                start_time = time.time()
                response = await client.post(
                    f"{self.base_url}/v1/process",
                    json=test_data,
                    headers=self.headers
                )
                total_time = time.time() - start_time
                
                if response.status_code != 200:
                    print(f"❌ Performance test {i+1} failed: {response.status_code}")
                    return False
                
                times.append(total_time)
            
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            # Performance requirements (reasonable for small PDF)
            MAX_PROCESSING_TIME = 5.0  # 5 seconds max
            
            if avg_time > MAX_PROCESSING_TIME:
                print(f"❌ Average processing time too slow: {avg_time:.2f}s (max: {MAX_PROCESSING_TIME}s)")
                return False
            
            print(f"✅ Performance acceptable")
            print(f"   Average: {avg_time:.2f}s")
            print(f"   Range: {min_time:.2f}s - {max_time:.2f}s")
            return True
    
    async def run_all_validations(self):
        """Run all validation tests."""
        print("🚀 Starting Document Processor Final Validation")
        print("=" * 60)
        
        validations = [
            ("Service Health", self.test_service_health),
            ("Authentication", self.test_authentication),
            ("PDF Processing", self.test_pdf_processing),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
        ]
        
        results = {}
        
        for validation_name, validation_func in validations:
            try:
                print(f"\n{validation_name}:")
                results[validation_name] = await validation_func()
            except Exception as e:
                print(f"❌ {validation_name} failed with exception: {e}")
                results[validation_name] = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 FINAL VALIDATION RESULTS")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for validation_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{validation_name:.<40} {status}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} validations passed")
        
        if passed == total:
            print("\n🎉 DOCUMENT PROCESSOR SERVICE IS PRODUCTION READY!")
            print("   ✅ All core functionality validated")
            print("   ✅ Authentication working correctly") 
            print("   ✅ Error handling robust")
            print("   ✅ Performance acceptable")
            print("   ✅ Ready for integration with main app")
            return True
        else:
            print("\n💥 SERVICE NOT READY FOR PRODUCTION!")
            print(f"   {total - passed} validation(s) failed")
            return False

async def main():
    """Main validation runner."""
    validator = DocumentProcessorValidator()
    success = await validator.run_all_validations()
    return success

if __name__ == "__main__":
    print("Document Processor Service - Final Validation")
    print("Make sure the service is running with API key authentication")
    print()
    
    success = asyncio.run(main())
    exit(0 if success else 1)