# Multi-stage build for security and minimal attack surface
FROM python:3.11-alpine AS builder

# Install build dependencies in builder stage
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage with minimal base image
FROM python:3.11-alpine

# Create non-root user for security
RUN addgroup -g 1001 -S coderunner && \
    adduser -u 1001 -S coderunner -G coderunner

# Install minimal runtime dependencies only
RUN apk add --no-cache \
    dumb-init \
    && rm -rf /var/cache/apk/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/coderunner/.local

# Create secure directories
RUN mkdir -p /app /tmp/code-exec && \
    chown -R coderunner:coderunner /app /tmp/code-exec && \
    chmod 755 /app && \
    chmod 700 /tmp/code-exec

# Copy application code
COPY --chown=coderunner:coderunner src/ /app/

# Set PATH for user-installed packages
ENV PATH=/home/coderunner/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER coderunner

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["/usr/bin/dumb-init", "--"]

# Default command
CMD ["python", "-m", "protobox.admin.actions.code_run_service"] 