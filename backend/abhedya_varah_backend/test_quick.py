#!/usr/bin/env python
"""Quick test runner - run directly with Python"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Now run pytest programmatically
import pytest
sys.exit(pytest.main([str(Path(__file__).parent / "test_main.py"), "-v", "--tb=short"]))