# Document Processor Service - Ubuntu-based for better compatibility
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    # PyMuPDF dependencies
    libmupdf-dev \
    mupdf-tools \
    # OCR dependencies (if needed later)
    tesseract-ocr \
    tesseract-ocr-eng \
    # Image processing
    libpoppler-cpp-dev \
    poppler-utils \
    # Other utilities
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY services/document-processor/pyproject.toml .
COPY services/document-processor/uv.lock* .

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY services/document-processor/src ./src

# Copy entrypoint script
COPY services/document-processor/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create non-root user
RUN useradd -m -s /bin/bash docprocessor && \
    chown -R docprocessor:docprocessor /app && \
    mkdir -p /tmp/processing && \
    chown -R docprocessor:docprocessor /tmp/processing

USER docprocessor

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8092

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8092/health || exit 1

# Run the application
CMD ["/app/entrypoint.sh"]