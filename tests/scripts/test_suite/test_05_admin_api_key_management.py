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

    created_count = 0
    for base_label in ["admin-test-key-1", "admin-test-key-2", "admin-test-key-3"]:
        unique_name = f"{base_label}-{int(time.time())}"
        data = {"name": unique_name, "expires_in_days": None}

        # Add retry logic for connection issues
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=regular_token, data=data)

            if success and response and response.status_code == 201 and resp_data and "api_key" in resp_data:
                key_id = resp_data["api_key"].get("key_id")
                test_data["api_keys"][base_label] = key_id
                logger.info(f"  ✓ Created {unique_name} (label: {base_label})")
                created_count += 1
                break

            if not response and attempt < max_retries - 1:
                logger.warning(f"  Connection error creating {base_label}, retrying...")
                time.sleep(retry_delay)
                continue

            if attempt == max_retries - 1:
                logger.warning(f"  ✗ Failed to create {base_label} after {max_retries} attempts")

        time.sleep(0.3)  # Small delay between creations

    logger.info(f"✓ Total test API keys created: {created_count}")

    # Store the count for later tests to check
    test_data["admin_test_keys_created"] = created_count


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

    # Find any admin test key to update, or fallback to any available key
    key_name = None
    key_id = None

    # First try preferred admin test keys
    for name in ["admin-test-key-1", "admin-test-key-2", "admin-test-key-3"]:
        if name in test_data.get("api_keys", {}):
            key_name = name
            key_id = test_data["api_keys"][name]
            break

    # If no admin test keys, try any available key
    if not key_id and test_data.get("api_keys"):
        key_name = list(test_data["api_keys"].keys())[0]
        key_id = test_data["api_keys"][key_name]

    # If still no keys, try to list keys from API and use one
    if not key_id:
        success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=admin_token, params={"limit": 1})
        if success and resp_data and resp_data.get("api_keys"):
            keys = resp_data["api_keys"]
            if keys:
                key_id = keys[0].get("key_id")
                key_name = keys[0].get("name")

    if not key_id:
        pytest.skip("No API keys available for update test")

    data = {
        "status": "active",
        "rate_limit_per_minute": 200,
        "rate_limit_per_hour": 2000,
    }

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

    assert success, f"Admin update API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ API key '{key_name}' updated:")
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

    # Find any admin test key, or fallback to any available key
    key_name = None
    key_id = None

    # First try preferred admin test keys
    for name in ["admin-test-key-2", "admin-test-key-1", "admin-test-key-3"]:
        if name in test_data.get("api_keys", {}):
            key_name = name
            key_id = test_data["api_keys"][name]
            break

    # If no admin test keys, try any available key
    if not key_id and test_data.get("api_keys"):
        available_keys = [k for k in test_data["api_keys"].keys()]
        if available_keys:
            key_name = available_keys[0]
            key_id = test_data["api_keys"][key_name]

    # If still no keys, try to list keys from API and use one
    if not key_id:
        success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=admin_token, params={"limit": 1})
        if success and resp_data and resp_data.get("api_keys"):
            keys = resp_data["api_keys"]
            if keys:
                key_id = keys[0].get("key_id")
                key_name = keys[0].get("name")

    if not key_id:
        pytest.skip("No API keys available")

    data = {"status": "suspended"}

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

    assert success, f"Suspend API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ API key '{key_name}' suspended")


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

    # Find any admin test key to delete, or fallback to any available key
    key_name = None
    key_id = None

    # First try preferred admin test keys
    for name in ["admin-test-key-3", "admin-test-key-2", "admin-test-key-1"]:
        if name in test_data.get("api_keys", {}):
            key_name = name
            key_id = test_data["api_keys"][name]
            break

    # If no admin test keys, try any available key (but not production/staging keys used in other tests)
    if not key_id and test_data.get("api_keys"):
        available_keys = [k for k in test_data["api_keys"].keys() if k not in ["production-key", "staging-key"]]
        if available_keys:
            key_name = available_keys[0]
            key_id = test_data["api_keys"][key_name]

    # If still no keys, try to list keys from API and use one
    if not key_id:
        success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=admin_token, params={"limit": 1})
        if success and resp_data and resp_data.get("api_keys"):
            keys = resp_data["api_keys"]
            if keys:
                key_id = keys[0].get("key_id")
                key_name = keys[0].get("name")

    if not key_id:
        pytest.skip("No API keys available for delete test")

    success, response, resp_data = make_request(internal_api_url, logger, "DELETE", f"/admin/api-keys/{key_id}/delete/", token=admin_token)

    assert success, f"Admin delete API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    if key_name in test_data.get("api_keys", {}):
        del test_data["api_keys"][key_name]
    logger.info(f"✓ API key '{key_name}' deleted successfully")
