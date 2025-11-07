"""
General API endpoints tests.
Tests: Healthcheck, Homepage, and general connectivity
"""

import pytest
from conftest import make_request, log_section


def test_01_healthcheck(base_url, logger):
    """Test API healthcheck endpoint."""
    log_section(logger, "TEST: HEALTHCHECK")

    success, response, resp_data = make_request(base_url, logger, "GET", "/health/", token=None)

    assert success, f"Healthcheck failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ API is healthy and responsive")


def test_02_homepage(base_url, logger):
    """Test homepage endpoint."""
    log_section(logger, "TEST: HOMEPAGE")

    success, response, resp_data = make_request(base_url, logger, "GET", "/", token=None)

    assert success, f"Homepage failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ Homepage is accessible")


def test_03_api_root_endpoint(base_url, logger):
    """Test API root endpoint."""
    log_section(logger, "TEST: API ROOT ENDPOINT")

    internal_api_url = f"{base_url}/internal/api"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/", token=None)

    # Should provide some info about available endpoints
    if response and response.status_code == 200:
        logger.info("✓ API root endpoint is accessible")
    else:
        logger.info(f"ℹ API root returns: {response.status_code if response else 'error'}")
