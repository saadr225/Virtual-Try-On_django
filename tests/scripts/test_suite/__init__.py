"""
Comprehensive API Test Suite for VTON Django API

This package contains organized tests for all API endpoints.
"""

import pytest

__version__ = "1.0.0"
__author__ = "API Testing Team"


def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line("markers", "admin: marks tests that require admin privileges")


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption("--base-url", action="store", default="http://localhost:8000", help="Base URL of the API")
