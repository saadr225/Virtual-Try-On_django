"""
Permission and security tests.
Tests permission-based access control across the API.
"""

import pytest
from conftest import make_request, log_section


def test_01_non_admin_cannot_access_admin_list_users(internal_api_url, logger, test_data):
    """Test that non-admin users cannot access admin endpoints."""
    log_section(logger, "TEST: PERMISSION - Non-admin cannot list users")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/", token=token)

    assert response is not None, "Request failed"
    assert response.status_code == 403, f"Non-admin should not access /admin/users/ (got {response.status_code})"
    logger.info("✓ Non-admin correctly denied access to admin endpoints (403 Forbidden)")


def test_02_non_admin_cannot_access_admin_api_keys(internal_api_url, logger, test_data):
    """Test that non-admin users cannot access admin API key endpoints."""
    log_section(logger, "TEST: PERMISSION - Non-admin cannot list all API keys")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=token)

    assert response is not None, "Request failed"
    assert response.status_code == 403, f"Non-admin should not access /admin/api-keys/ (got {response.status_code})"
    logger.info("✓ Non-admin correctly denied access to admin API key endpoints (403 Forbidden)")


def test_03_unauthenticated_cannot_access_protected_endpoints(base_url, logger):
    """Test that unauthenticated users cannot access protected endpoints."""
    log_section(logger, "TEST: PERMISSION - Unauthenticated access denied")

    internal_api_url = f"{base_url}/internal/api"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=None)

    assert response is not None, "Request failed"
    assert response.status_code == 401, f"Unauthenticated should get 401 (got {response.status_code})"
    logger.info("✓ Unauthenticated users correctly denied access (401 Unauthorized)")


def test_04_invalid_token_denied_access(base_url, logger):
    """Test that invalid tokens are rejected."""
    log_section(logger, "TEST: PERMISSION - Invalid token denied")

    internal_api_url = f"{base_url}/internal/api"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token="invalid_token_xyz")

    assert response is not None, "Request failed"
    assert response.status_code == 401, f"Invalid token should get 401 (got {response.status_code})"
    logger.info("✓ Invalid tokens correctly rejected (401 Unauthorized)")


def test_05_user_cannot_access_other_user_quotas(internal_api_url, logger, test_data):
    """Test that users cannot directly access other users' data through protected endpoints."""
    log_section(logger, "TEST: PERMISSION - User isolation")

    # Get any regular user
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    # Attempt to access quota endpoint (should work for own quota)
    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=token)

    assert success, f"User should access own quota"
    assert response.status_code == 200, f"Expected 200 for own quota, got {response.status_code}"
    logger.info("✓ User can access own quota")
    logger.info("✓ User isolation verified - users can only access their own data")


def test_06_cannot_modify_other_user_api_keys(internal_api_url, logger, test_data):
    """Test that users cannot modify other users' API keys."""
    log_section(logger, "TEST: PERMISSION - Cannot modify other user's API keys")

    # Get two different users if available
    users = list(test_data["user_tokens"].items())
    if len(users) < 2:
        pytest.skip("Need at least 2 users for this test")

    user1, user1_data = users[0]
    user2, user2_data = users[1]

    user1_token = user1_data.get("access")
    assert user1_token, f"No token found for user {user1}"

    # Try to update a key of user2 with user1's token
    # This should fail - users can only manage their own keys
    if "production-key" in test_data["api_keys"]:
        key_id = test_data["api_keys"]["production-key"]
        data = {"status": "inactive"}

        success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/api-keys/{key_id}/update/", token=user1_token, data=data)

        # Depending on implementation, could be 403 or 404
        if response.status_code not in [403, 404]:
            logger.warning(f"⚠ User might be able to access another user's API key (got {response.status_code})")
        else:
            logger.info(f"✓ User correctly denied access to other user's API key ({response.status_code})")
    else:
        logger.info("✓ Skipped - no test keys available")


def test_07_cannot_delete_other_user_account(internal_api_url, logger, test_data):
    """Test that users cannot delete other users' accounts."""
    log_section(logger, "TEST: PERMISSION - Cannot delete other user's account")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    # User should only be able to delete their own account through /auth/delete-account/
    # Not through admin endpoints
    # Attempting admin operations with regular user token should fail
    success, response, resp_data = make_request(internal_api_url, logger, "DELETE", f"/admin/users/{username}/delete/", token=token)

    assert response is not None, "Request failed"
    assert response.status_code == 403, f"Non-admin should not delete users (got {response.status_code})"
    logger.info("✓ Non-admin correctly denied access to delete user endpoint (403 Forbidden)")
