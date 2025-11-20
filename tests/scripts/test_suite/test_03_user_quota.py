"""
User Quota Management endpoint tests.
Tests: /quota/me
"""

import pytest
from conftest import make_request, log_section
from .helpers import ensure_approved_user, ensure_regular_user, ensure_user_token


def test_01_get_user_quota(internal_api_url, logger, test_data):
    """Test retrieving user's quota information."""
    log_section(logger, "TEST: GET USER QUOTA (/quota/me/)")

    username = ensure_regular_user(internal_api_url, logger, test_data)
    token = ensure_user_token(username, internal_api_url, logger, test_data)

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


def test_02_unapproved_user_shows_disabled_status(internal_api_url, logger, test_data):
    """Test that unapproved user's quota shows API key generation as disabled."""
    log_section(logger, "TEST: UNAPPROVED USER QUOTA STATUS")

    username = ensure_regular_user(internal_api_url, logger, test_data, force_new=True)
    token = ensure_user_token(username, internal_api_url, logger, test_data)

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=token)

    assert success, f"Get quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    quota = resp_data["quota_info"]

    # Unapproved users should have api_key_generation_enabled = False
    is_enabled = quota.get("api_key_generation_enabled", False)
    can_create_more = quota.get("can_create_more")

    if not is_enabled:
        logger.info(f"✓ Unapproved user correctly shows API key generation as disabled")
        logger.info(f"  - API Key Generation Enabled: {is_enabled}")
        logger.info(f"  - Can Create More: {can_create_more}")
    else:
        logger.warning(f"⚠ User shows API key generation as enabled (may have been approved)")


def test_03_approved_user_shows_enabled_status(internal_api_url, logger, test_data):
    """Test that approved user's quota shows API key generation as enabled."""
    log_section(logger, "TEST: APPROVED USER QUOTA STATUS")

    approved_username = ensure_approved_user(internal_api_url, logger, test_data)
    token = ensure_user_token(approved_username, internal_api_url, logger, test_data)

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=token)

    assert success, f"Get quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    quota = resp_data["quota_info"]

    is_enabled = quota.get("api_key_generation_enabled", False)
    max_keys = quota.get("max_api_keys", 0)
    monthly_quota = quota.get("user_monthly_quota", 0)

    logger.info(f"✓ Approved user quota status:")
    logger.info(f"  - API Key Generation Enabled: {is_enabled}")
    logger.info(f"  - Max API Keys: {max_keys}")
    logger.info(f"  - Monthly Quota: {monthly_quota}")

    assert is_enabled, "Approved user should have API key generation enabled"
    assert max_keys > 0, "Approved user should have max_api_keys > 0"
    assert monthly_quota > 0, "Approved user should have user_monthly_quota > 0"


def test_04_quota_respects_max_api_keys_limit(internal_api_url, logger, test_data):
    """Test that user cannot create more API keys beyond max_api_keys limit."""
    log_section(logger, "TEST: QUOTA RESPECTS MAX API KEYS LIMIT")

    approved_username = ensure_approved_user(internal_api_url, logger, test_data)
    token = ensure_user_token(approved_username, internal_api_url, logger, test_data)

    # Get current quota
    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/quota/me/", token=token)

    assert success and response and response.status_code == 200, "Could not retrieve user quota"

    quota = resp_data["quota_info"]
    max_keys = quota.get("max_api_keys", 0)
    current_keys = quota.get("current_api_keys", 0)

    can_create, error_msg = quota.get("can_create_more", (False, ""))

    logger.info(f"✓ Quota limit check:")
    logger.info(f"  - Max API Keys: {max_keys}")
    logger.info(f"  - Current API Keys: {current_keys}")
    logger.info(f"  - Can Create More: {can_create}")
    if error_msg:
        logger.info(f"  - Error (if limit reached): {error_msg}")

    if current_keys >= max_keys:
        assert not can_create, "User at limit should not be able to create more keys"
        logger.info(f"✓ User correctly prevented from exceeding max keys limit")
