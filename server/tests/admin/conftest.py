"""Test configuration for admin tests: ensure src/ on Python path."""

import os
import sys

# Add project src/ directory to Python import path for protobox package.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT, "src")
sys.path.insert(0, SRC_DIR)
