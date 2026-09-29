"""Main entry point for uvicorn when running the admin API directly."""

import sys
from pathlib import Path

# Add parent directory to path for imports when running with uvicorn
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from ..server import create_app

logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<blue>{name}</blue>:<cyan>{function}:{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# Create the FastAPI app instance for uvicorn
# The create_app function will use environment variables directly
app = create_app()
