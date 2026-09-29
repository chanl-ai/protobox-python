"""Security regression tests: put src/ on the import path."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ.setdefault("MCP_SECRET_KEY", "test-master-key-0123456789abcdef0123456789")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-0123456789abcdef0123456789")
