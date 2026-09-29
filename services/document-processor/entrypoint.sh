#!/bin/bash
# Document Processor Entrypoint Script

# Set Python path for module imports
export PYTHONPATH=/app/src:$PYTHONPATH

# Start the application
exec .venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8092