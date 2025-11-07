"""
User API Key Management endpoint tests.
Tests: /api-keys/create, /api-keys/, /api-keys/{key_id}, /api-keys/{key_id}/update, /api-keys/{key_id}/regenerate, /api-keys/{key_id}/stats, /api-keys/{key_id}/delete
"""

import pytest
import time
from conftest import make_request, log_section


@pytest.mark.parametrize("key_name", ["production-key", "staging-key"])
def test_01_create_api_key(internal_api_url, logger, test_data, key_name):
    """Test creating a new API key."""
    log_section(logger, f"TEST: CREATE API KEY - {key_name}")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    data = {
        "name": key_name,
        "expires_in_days": None,
    }

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=token, data=data)

    assert success, f"Create API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "api_key" in resp_data, "API key data not found in response"

    key_id = resp_data["api_key"].get("key_id")
    test_data["api_keys"][key_name] = key_id
    logger.info(f"✓ Created API key:")
    logger.info(f"  - Key ID: {key_id}")
    logger.info(f"  - Name: {resp_data['api_key'].get('name')}")
    logger.info(f"  - Status: {resp_data['api_key'].get('status')}")

    time.sleep(0.5)


def test_02_list_api_keys(internal_api_url, logger, test_data):
    """Test listing user's API keys."""
    log_section(logger, "TEST: LIST API KEYS (/api-keys/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/api-keys/", token=token)

    assert success, f"List API keys failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_keys" in resp_data, "API keys list not found in response"

    keys = resp_data["api_keys"]
    pagination = resp_data.get("pagination", {})
    logger.info(f"✓ Listed API keys:")
    logger.info(f"  - Total: {len(keys)}")
    logger.info(f"  - Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")
    for key in keys[:3]:
        logger.info(f"    • {key.get('name')}: {key.get('status')}")


def test_03_get_api_key_detail(internal_api_url, logger, test_data):
    """Test getting detailed information about an API key."""
    log_section(logger, "TEST: GET API KEY DETAIL (/api-keys/{key_id}/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_name = "production-key"
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/api-keys/{key_id}/", token=token)

    assert success, f"Get API key detail failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_key" in resp_data, "API key detail not found in response"

    key = resp_data["api_key"]
    logger.info(f"✓ Retrieved API key details:")
    logger.info(f"  - Name: {key.get('name')}")
    logger.info(f"  - Status: {key.get('status')}")
    logger.info(f"  - Rate Limits: {key.get('rate_limit_per_minute')}/min, {key.get('rate_limit_per_hour')}/hr")
    logger.info(f"  - Monthly Quota: {key.get('monthly_quota')}")
    logger.info(f"  - Created: {key.get('created_at')}")


def test_04_update_api_key(internal_api_url, logger, test_data):
    """Test updating an API key status."""
    log_section(logger, "TEST: UPDATE API KEY (/api-keys/{key_id}/update/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_name = "production-key"
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    data = {"status": "inactive"}

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/api-keys/{key_id}/update/", token=token, data=data)

    assert success, f"Update API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ API key updated to: inactive")


def test_05_regenerate_api_key(internal_api_url, logger, test_data):
    """Test regenerating an API key."""
    log_section(logger, "TEST: REGENERATE API KEY (/api-keys/{key_id}/regenerate/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_name = "staging-key"
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    data = {"confirm": True}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/api-keys/{key_id}/regenerate/", token=token, data=data)

    assert success, f"Regenerate API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ New API key generated")


def test_06_get_api_key_stats(internal_api_url, logger, test_data):
    """Test getting API key usage statistics."""
    log_section(logger, "TEST: GET API KEY STATS (/api-keys/{key_id}/stats/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_name = "production-key"
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/api-keys/{key_id}/stats/", token=token)

    assert success, f"Get API key stats failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "stats" in resp_data, "Stats not found in response"

    stats = resp_data["stats"]
    logger.info(f"✓ Retrieved API key statistics:")
    logger.info(f"  - Total Requests: {stats.get('total_requests', 0)}")
    logger.info(f"  - Requests This Month: {stats.get('requests_this_month', 0)}")
    logger.info(f"  - Requests Today: {stats.get('requests_this_day', 0)}")
    logger.info(f"  - Quota Remaining: {stats.get('quota_remaining', 0)}")


@pytest.mark.parametrize("key_name", ["production-key", "staging-key"])
def test_07_delete_api_key(internal_api_url, logger, test_data, key_name):
    """Test deleting an API key."""
    log_section(logger, f"TEST: DELETE API KEY - {key_name}")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    success, response, resp_data = make_request(internal_api_url, logger, "DELETE", f"/api-keys/{key_id}/delete/", token=token)

    assert success, f"Delete API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    if key_name in test_data["api_keys"]:
        del test_data["api_keys"][key_name]
    logger.info(f"✓ API key deleted successfully")
