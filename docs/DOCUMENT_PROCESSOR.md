# Document Processor Microservice

## Overview

The Document Processor is a dedicated microservice that handles heavy document processing operations, including PDF parsing, OCR, table extraction, and document conversion. It's designed to be isolated from the main backend to optimize resource usage and build times.

## Architecture

### Design Principles

1. **Separation of Concerns**: Heavy document processing isolated from main API
2. **Signed URL Communication**: No direct file system sharing - uses pre-signed S3 URLs
3. **Graceful Degradation**: Main backend can fallback to basic processing
4. **Independent Scaling**: Scale document processing separately from API
5. **Optimized Builds**: Main backend uses Alpine, document processor uses Ubuntu

### System Architecture

```
┌──────────────────┐         ┌──────────────────┐
│   Main Backend   │────────►│ Document         │
│   (Alpine)       │  HTTP   │ Processor        │
│                  │         │ (Ubuntu)         │
└──────────────────┘         └──────────────────┘
        │                            │
        │                            │
        └──────────┬─────────────────┘
                   │
                   ▼
            ┌──────────────┐
            │  Tigris S3   │
            │  (Storage)   │
            └──────────────┘
```

### Communication Flow

1. **File Upload**: User uploads file to main backend
2. **S3 Storage**: Main backend stores file in Tigris S3
3. **Signed URL**: Main backend generates pre-signed URL with expiration
4. **Processing Request**: Main backend calls document processor with signed URL
5. **Download & Process**: Document processor downloads file via signed URL
6. **Return Results**: Processor returns extracted content and metadata
7. **Store Results**: Main backend stores results in MongoDB

## API Reference

### Health Check

```http
GET /health
```

Response:
```json
{
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
```

### Process Document

```http
POST /v1/process
```

Request:
```json
{
  "signed_url": "https://s3.amazonaws.com/bucket/file.pdf?signature=...",
  "file_type": "pdf",
  "file_size": 1048576,
  "options": {
    "use_ocr": true,
    "extract_tables": true,
    "extract_images": false
  }
}
```

Response:
```json
{
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
```

## Supported Formats

### Documents
- **PDF** (.pdf) - Full support with PyMuPDF and PDFplumber
  - Text extraction
  - Table extraction
  - Image extraction
  - OCR for scanned pages
  - Metadata extraction
- **Word** (.docx) - Microsoft Word documents
  - Paragraph extraction
  - Table extraction
  - Document properties
- **Text** (.txt, .md) - Plain text and markdown
  - UTF-8 and Latin-1 encoding
  - Line and word counting

### Spreadsheets
- **Excel** (.xlsx, .xls) - Excel spreadsheets
  - Multi-sheet support
  - Table data extraction
  - Column headers
- **CSV** (.csv) - Comma-separated values
  - Automatic delimiter detection
  - Header row detection

## Deployment

### Local Development

```bash
# Run with Docker Compose
make doc-processor-docker

# Run standalone
make doc-processor-run

# View logs
make doc-processor-logs

# Test health
make doc-processor-test
```

### Docker Configuration

The service uses two different Docker images:

#### Main Backend (Alpine-optimized)
```dockerfile
FROM python:3.11-alpine
# Lightweight, fast builds
# ~200MB image size
# No heavy document processing libraries
```

#### Document Processor (Ubuntu-based)
```dockerfile
FROM python:3.11-slim
# Ubuntu base for better compatibility
# Includes PyMuPDF, Tesseract, etc.
# ~800MB image size
# All document processing capabilities
```

### Environment Variables

```env
# Service Configuration
ENVIRONMENT=development
SERVICE_PORT=8092
SERVICE_HOST=0.0.0.0

# Processing Limits
MAX_FILE_SIZE=52428800  # 50MB
PROCESSING_TIMEOUT=120   # seconds
DOWNLOAD_TIMEOUT=60      # seconds

# OCR Settings
OCR_ENABLED=true
OCR_LANGUAGES=eng
OCR_CONFIDENCE_THRESHOLD=60.0

# Table Extraction
TABLE_EXTRACTION_ENABLED=true

# Performance
MAX_PAGES_PER_DOCUMENT=500
MAX_IMAGE_DIMENSION=4000
```

## Integration with Main Backend

### Document Client

The main backend uses a client to communicate with the document processor:

```python
from protobox.admin.services.document_client import document_processor_client

# Process a document
result = await document_processor_client.process_document(
    signed_url="https://s3.../file.pdf?signature=...",
    file_type="pdf",
    options={
        "use_ocr": True,
        "extract_tables": True
    }
)

# Check health
is_healthy = await document_processor_client.check_health()
```

### Fallback Processing

If the document processor is unavailable, the main backend falls back to basic processing:

1. **PDFplumber only** for PDFs (no PyMuPDF)
2. **Basic text extraction** for other formats
3. **No OCR capabilities**
4. **Limited metadata extraction**

### Signed URL Generation

The main backend generates pre-signed URLs for secure file access:

```python
# Generate signed URL with 1-hour expiration
signed_url = tigris_service.generate_presigned_url(
    bucket_name="documents",
    object_key="workspace/file.pdf",
    expiration=3600
)
```

## Performance Optimization

### Build Time Optimization

- **Main Backend**: Alpine image builds in ~30 seconds
- **Document Processor**: Ubuntu image builds in ~2 minutes
- **Parallel Builds**: Both services can build simultaneously

### Runtime Optimization

- **Connection Pooling**: Reuse HTTP connections
- **Timeout Configuration**: Aggressive timeouts for resilience
- **Retry Logic**: Automatic retry with exponential backoff
- **Health Checks**: Regular health monitoring

### Resource Management

- **Memory Limits**: Document processor limited to 2GB RAM
- **CPU Limits**: Can be CPU-limited in production
- **Temp File Cleanup**: Automatic cleanup after processing
- **Request Queuing**: Queue long-running requests

## Monitoring & Logging

### Logging

All operations are logged with structured logging:

```
INFO: Processing request for pdf document
INFO: Downloading document from signed URL for pdf processing
INFO: Downloaded 1,048,576 bytes to /tmp/doc_abc123.pdf
INFO: Processing pdf document with options: {'use_ocr': True}
INFO: PDF parsing complete: 10 pages, 5000 chars in 2.50s
```

### Health Monitoring

```bash
# Check health via curl
curl http://localhost:8092/health

# Check via Make
make doc-processor-test

# Monitor with Docker
docker compose --profile services ps
```

### Error Handling

- **Download Errors**: Return 502 Bad Gateway
- **Processing Timeouts**: Return 504 Gateway Timeout
- **Invalid Files**: Return 400 Bad Request
- **Service Errors**: Return 500 Internal Server Error

## Testing

### Unit Tests

```bash
cd services/document-processor
pytest tests/unit/
```

### Integration Tests

```bash
# Start service
make doc-processor-docker

# Run integration tests
pytest tests/integration/test_document_processor.py
```

### Manual Testing

```bash
# Test with curl
curl -X POST http://localhost:8092/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "signed_url": "https://example.com/test.pdf",
    "file_type": "pdf",
    "options": {"use_ocr": true}
  }'
```

### Remote Environment Testing

```bash
# Test staging document processor
make doc-processor-test-remote ENV=staging                    # Health check
make doc-processor-test-remote ENV=staging TEST_TYPE=health   # Health check only  
make doc-processor-test-remote ENV=staging TEST_TYPE=upload   # Test API structure
make doc-processor-test-remote ENV=staging TEST_TYPE=comprehensive  # Full test suite

# Test production document processor
make doc-processor-test-remote ENV=production                 # Health check
make doc-processor-test-remote ENV=production TEST_TYPE=health
make doc-processor-test-remote ENV=production TEST_TYPE=upload
make doc-processor-test-remote ENV=production TEST_TYPE=comprehensive
```

Available test types:
- **health**: Basic health check and service status
- **upload**: Test API structure and authentication requirements  
- **comprehensive**: Run full integration test suite against remote environment

## Troubleshooting

### Common Issues

1. **PyMuPDF Build Failures**
   - Solution: Use Ubuntu base image instead of Alpine
   - Alternative: Remove PyMuPDF, use PDFplumber only

2. **Service Unavailable**
   - Check: `docker compose ps`
   - Logs: `make doc-processor-logs`
   - Health: `make doc-processor-test`

3. **Timeout Errors**
   - Increase `PROCESSING_TIMEOUT`
   - Check file size limits
   - Monitor memory usage

4. **OCR Not Working**
   - Verify Tesseract installed
   - Check `OCR_ENABLED=true`
   - Verify language packs installed

## Future Enhancements

- [ ] Add Redis caching for processed documents
- [ ] Implement async job queue with Celery
- [ ] Add support for more formats (RTF, ODT)
- [ ] Implement document preview generation
- [ ] Add virus scanning before processing
- [ ] Implement rate limiting per workspace
- [ ] Add Prometheus metrics endpoint
- [ ] Support for document conversion (PDF to DOCX, etc.)