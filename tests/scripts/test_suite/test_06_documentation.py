"""
Documentation endpoint tests.
Tests: /docs/, /docs/client-api-spec/, /docs/internal-api-spec/
"""

import pytest
from conftest import make_request, log_section


def test_01_get_docs_info(internal_api_url, logger):
    """Test getting API documentation info."""
    log_section(logger, "TEST: GET DOCUMENTATION INFO (/docs/)")

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/docs/", token=None)

    assert success, f"Get docs info failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "endpoints" in resp_data, "Documentation endpoints not found"

    endpoints = resp_data.get("endpoints", [])
    logger.info(f"✓ Retrieved documentation info:")
    logger.info(f"  - Available endpoints: {len(endpoints)}")
    for endpoint in endpoints:
        logger.info(f"    • {endpoint.get('name')}: {endpoint.get('access')}")


def test_02_get_client_api_spec(internal_api_url, logger):
    """Test getting Client API specification file."""
    log_section(logger, "TEST: GET CLIENT API SPECIFICATION (/docs/client-api-spec/)")

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/docs/client-api-spec/", token=None)

    assert success, f"Get client API spec failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Check if response is YAML content
    content_type = response.headers.get("Content-Type", "")
    logger.info(f"✓ Retrieved Client API specification:")
    logger.info(f"  - Content-Type: {content_type}")
    logger.info(f"  - Size: {len(response.text)} bytes")
    logger.info(f"  - Format: YAML")


def test_03_get_internal_api_spec(internal_api_url, logger, test_data):
    """Test getting Internal API specification file (requires admin access)."""
    log_section(logger, "TEST: GET INTERNAL API SPECIFICATION (/docs/internal-api-spec/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for this test")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/docs/internal-api-spec/", token=token)

    assert success, f"Get internal API spec failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Check if response is YAML content
    content_type = response.headers.get("Content-Type", "")
    logger.info(f"✓ Retrieved Internal API specification:")
    logger.info(f"  - Content-Type: {content_type}")
    logger.info(f"  - Size: {len(response.text)} bytes")
    logger.info(f"  - Format: YAML")
    logger.info(f"  - Access: Admin only")


def test_04_internal_api_spec_requires_admin(internal_api_url, logger, test_data):
    """Test that internal API spec requires admin access."""
    log_section(logger, "TEST: INTERNAL API SPEC - REQUIRES ADMIN (/docs/internal-api-spec/)")

    # Try with a regular user
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/docs/internal-api-spec/", token=token)

    # Should fail with 403 Forbidden
    assert response is not None, "Request failed"
    assert response.status_code == 403, f"Expected 403 for non-admin user, got {response.status_code}"
    logger.info(f"✓ Access correctly denied for non-admin users (403 Forbidden)")


def test_05_client_api_spec_public_access(base_url, logger):
    """Test that client API spec is publicly accessible."""
    log_section(logger, "TEST: CLIENT API SPEC - PUBLIC ACCESS (/docs/client-api-spec/)")

    # Test without authentication
    success, response, resp_data = make_request(base_url + "/internal/api", logger, "GET", "/docs/client-api-spec/", token=None)

    assert success, f"Get client API spec failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ Client API specification is publicly accessible")
