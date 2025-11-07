"""
User Quota Management endpoint tests.
Tests: /quota/me
"""

import pytest
from conftest import make_request, log_section


def test_01_get_user_quota(internal_api_url, logger, test_data):
    """Test retrieving user's quota information."""
    log_section(logger, "TEST: GET USER QUOTA (/quota/me/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=token)

    assert success, f"Get quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "quota_info" in resp_data, "Quota info not found in response"

    quota = resp_data["quota_info"]
    logger.info(f"✓ Retrieved user quota information:")
    logger.info(f"  - Max API Keys: {quota.get('max_api_keys')}")
    logger.info(f"  - Current API Keys: {quota.get('current_api_keys')}")
    logger.info(f"  - Can Create More: {quota.get('can_create_more')}")
    logger.info(f"  - API Key Generation Enabled: {quota.get('api_key_generation_enabled')}")
    logger.info(f"  - Monthly Quota: {quota.get('user_monthly_quota')}")
    logger.info(f"  - Quota Used This Month: {quota.get('cumulative_quota_used')}")
    logger.info(f"  - Quota Remaining: {quota.get('quota_remaining')}")
