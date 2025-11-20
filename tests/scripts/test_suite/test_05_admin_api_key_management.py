"""
Admin API Key Management endpoint tests.
Tests: /admin/api-keys/, /admin/api-keys/{key_id}/update/, /admin/api-keys/{key_id}/delete/
"""

import pytest
import time
from conftest import make_request, log_section
from .helpers import ensure_admin_token, ensure_approved_user, ensure_user_token


def test_01_admin_create_api_keys_for_testing(internal_api_url, logger, test_data):
    """Test creating API keys for admin testing operations."""
    log_section(logger, "TEST: ADMIN - CREATE API KEYS FOR ADMIN TESTS")

    admin_token = ensure_admin_token(internal_api_url, logger, test_data)
    regular_username = ensure_approved_user(internal_api_url, logger, test_data)
    regular_token = ensure_user_token(regular_username, internal_api_url, logger, test_data)

    if "api_keys" not in test_data:
        test_data["api_keys"] = {}

    for base_label in ["admin-test-key-1", "admin-test-key-2", "admin-test-key-3"]:
        unique_name = f"{base_label}-{int(time.time())}"
        data = {"name": unique_name, "expires_in_days": None}

        success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=regular_token, data=data)

        if success and response.status_code == 201 and resp_data and "api_key" in resp_data:
            key_id = resp_data["api_key"].get("key_id")
            test_data["api_keys"][base_label] = key_id
            logger.info(f"  ✓ Created {unique_name} (label: {base_label})")
        else:
            logger.warning(f"  ✗ Failed to create {key_name}")

    logger.info(f"✓ Total test API keys available: {len([k for k in test_data['api_keys'] if k.startswith('admin-test-')])}")


def test_02_admin_list_all_api_keys(internal_api_url, logger, test_data):
    """Test admin listing all API keys across all users."""
    log_section(logger, "TEST: ADMIN - LIST ALL API KEYS (/admin/api-keys/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"page": 1, "limit": 20}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=token, params=params)

    assert success, f"List all API keys failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_keys" in resp_data, "API keys list not found"

    keys = resp_data["api_keys"]
    pagination = resp_data.get("pagination", {})
    logger.info(f"✓ Listed all API keys:")
    logger.info(f"  - Fetched: {len(keys)}")
    logger.info(f"  - Total: {pagination.get('total')}")
    logger.info(f"  - Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")
    for key in keys[:3]:
        logger.info(f"    • {key.get('name')} (User: {key.get('username')}): {key.get('status')}")


def test_03_admin_list_api_keys_by_user(internal_api_url, logger, test_data):
    """Test admin listing API keys filtered by username."""
    log_section(logger, "TEST: ADMIN - LIST API KEYS BY USER (/admin/api-keys/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    target_username = list(test_data["test_users"].keys())[0]
    assert token, f"No token found for admin {admin_username}"

    params = {"username": target_username, "page": 1, "limit": 20}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=token, params=params)

    assert success, f"List API keys by user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_keys" in resp_data, "API keys list not found"

    keys = resp_data["api_keys"]
    logger.info(f"✓ Listed API keys for user '{target_username}':")
    logger.info(f"  - Total: {len(keys)}")
    for key in keys[:3]:
        logger.info(f"    • {key.get('name')}: {key.get('status')}")


def test_04_admin_list_api_keys_by_status(internal_api_url, logger, test_data):
    """Test admin listing API keys filtered by status."""
    log_section(logger, "TEST: ADMIN - LIST API KEYS BY STATUS (/admin/api-keys/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"status": "active", "page": 1, "limit": 20}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=token, params=params)

    assert success, f"List API keys by status failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_keys" in resp_data, "API keys list not found"

    keys = resp_data["api_keys"]
    logger.info(f"✓ Listed active API keys:")
    logger.info(f"  - Total: {len(keys)}")


def test_05_admin_update_api_key(internal_api_url, logger, test_data):
    """Test admin updating any user's API key."""
    log_section(logger, "TEST: ADMIN - UPDATE ANY API KEY (/admin/api-keys/{key_id}/update/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"

    # Find any admin test key to update
    key_name = None
    for name in ["admin-test-key-1"]:
        if name in test_data["api_keys"]:
            key_name = name
            break

    if not key_name and test_data["api_keys"]:
        key_name = list(test_data["api_keys"].keys())[0]

    if not key_name:
        pytest.skip("No API keys available for update test")

    key_id = test_data["api_keys"][key_name]

    data = {
        "status": "active",
        "rate_limit_per_minute": 200,
        "rate_limit_per_hour": 2000,
    }

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

    assert success, f"Admin update API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ API key updated:")
    logger.info(f"  - Status: active")
    logger.info(f"  - Rate limit: 200/min, 2000/hr")


def test_06_admin_suspend_api_key(internal_api_url, logger, test_data):
    """Test admin suspending an API key."""
    log_section(logger, "TEST: ADMIN - SUSPEND API KEY (/admin/api-keys/{key_id}/update/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"

    key_name = None
    for name in ["admin-test-key-2"]:
        if name in test_data["api_keys"]:
            key_name = name
            break

    if not key_name:
        pytest.skip("No API keys available")

    key_id = test_data["api_keys"][key_name]

    data = {"status": "suspended"}

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

    assert success, f"Suspend API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ API key suspended")


def test_07_admin_delete_api_key(internal_api_url, logger, test_data):
    """Test admin deleting any user's API key."""
    log_section(logger, "TEST: ADMIN - DELETE ANY API KEY (/admin/api-keys/{key_id}/delete/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"

    # Find any admin test key to delete
    key_name = None
    for name in ["admin-test-key-3"]:
        if name in test_data["api_keys"]:
            key_name = name
            break

    if not key_name:
        pytest.skip("No API keys available for delete test")

    key_id = test_data["api_keys"][key_name]

    success, response, resp_data = make_request(internal_api_url, logger, "DELETE", f"/admin/api-keys/{key_id}/delete/", token=admin_token)

    assert success, f"Admin delete API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    if key_name in test_data["api_keys"]:
        del test_data["api_keys"][key_name]
    logger.info(f"✓ API key deleted successfully")
