"""Shared helper utilities for the API integration tests."""

import time

from conftest import make_request


def ensure_admin_token(internal_api_url, logger, test_data):
    """Make sure we have a valid admin token available."""
    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if admin_token:
        return admin_token

    login_payload = {"username": admin_username, "password": "admin"}
    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/admin-login/", data=login_payload)

    assert success and response and response.status_code == 200 and resp_data and "access" in resp_data, "Admin login failed"

    test_data["user_tokens"][admin_username] = {
        "access": resp_data["access"],
        "refresh": resp_data.get("refresh"),
        "user_type": resp_data.get("user_type", "admin"),
    }
    return resp_data["access"]


def ensure_regular_user(internal_api_url, logger, test_data, force_new: bool = False):
    """Return username of an existing or freshly created regular test user."""
    if not force_new and test_data["test_users"]:
        return next(iter(test_data["test_users"]))

    username = f"apitest_{int(time.time())}"
    email = f"{username}@test.local"
    payload = {
        "username": username,
        "email": email,
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "first_name": "API",
        "last_name": "Tester",
    }

    success, response, _ = make_request(internal_api_url, logger, "POST", "/auth/register/", data=payload)
    assert success and response and response.status_code == 201, "Failed to auto-register test user"

    test_data["test_users"][username] = {"email": email, "password": payload["password"], "username": username}
    return username


def ensure_user_token(username, internal_api_url, logger, test_data):
    """Guarantee that the given username has a valid access token cached."""
    token_info = test_data["user_tokens"].get(username)
    if token_info and token_info.get("access"):
        return token_info["access"]

    password = test_data["test_users"].get(username, {}).get("password")
    assert password, f"No stored password for {username}"

    login_payload = {"username": username, "password": password}
    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/login/", data=login_payload)

    assert success and response and response.status_code == 200 and resp_data and "access" in resp_data, f"Login failed for {username}"

    test_data["user_tokens"][username] = {
        "access": resp_data["access"],
        "refresh": resp_data.get("refresh"),
        "user_type": resp_data.get("user_type", "customer"),
    }
    return resp_data["access"]


def ensure_approved_user(internal_api_url, logger, test_data):
    """Ensure at least one regular test user has an approved API key request."""
    approved_username = test_data.get("approved_request_user")
    if approved_username:
        ensure_user_token(approved_username, internal_api_url, logger, test_data)
        return approved_username

    # Always create a NEW dedicated user for approved tests to avoid conflicts
    username = ensure_regular_user(internal_api_url, logger, test_data, force_new=True)
    token = ensure_user_token(username, internal_api_url, logger, test_data)

    # Submit a fresh API key request for this new user
    submit_payload = {
        "requested_key_name": f"auto-approved-key-{int(time.time())}",
        "reason": "Automated test flow",
        "intended_use": "Integration tests",
        "requested_rate_limit_per_minute": 60,
        "requested_rate_limit_per_hour": 3600,
        "requested_rate_limit_per_day": 50000,
        "requested_monthly_quota": 100000,
    }
    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        "/api-key-requests/submit/",
        token=token,
        data=submit_payload,
    )
    assert success and response and response.status_code == 201 and resp_data and resp_data.get("request"), "Failed to submit API key request for approval"
    request_id = resp_data["request"].get("request_id")

    admin_token = ensure_admin_token(internal_api_url, logger, test_data)
    approved_monthly_quota = 1_000_000
    max_api_keys = 5
    user_monthly_quota = approved_monthly_quota * max_api_keys
    approval_payload = {
        "payment_date": "2025-11-20",
        "payment_amount": "99.99",
        "admin_notes": "Auto-approved for testing",
        "approved_rate_limit_per_minute": 100,
        "approved_rate_limit_per_hour": 5000,
        "approved_rate_limit_per_day": 50000,
        "approved_monthly_quota": approved_monthly_quota,
        "max_api_keys": max_api_keys,
        "user_monthly_quota": user_monthly_quota,
    }

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        f"/admin/api-key-requests/{request_id}/approve/",
        token=admin_token,
        data=approval_payload,
    )

    assert success and response and response.status_code == 201 and resp_data and resp_data.get("request"), "Failed to approve API key request"

    approved_request = resp_data["request"]
    test_data["approved_request_user"] = username
    test_data["approved_request_id"] = approved_request.get("request_id", request_id)
    logger.info(f"Auto-approved API key request for {username}")
    return username


def ensure_pending_request(internal_api_url, logger, test_data, force_new: bool = False):
    """Ensure there is a pending API key request available for admin workflows."""
    cached = test_data.get("pending_request")
    if cached and not force_new:
        ensure_user_token(cached["username"], internal_api_url, logger, test_data)
        return cached

    username = ensure_regular_user(internal_api_url, logger, test_data, force_new=True)
    token = ensure_user_token(username, internal_api_url, logger, test_data)

    request_payload = {
        "requested_key_name": f"pending-key-{int(time.time())}",
        "reason": "Generated pending request for automated tests",
        "intended_use": "Integration tests",
        "requested_rate_limit_per_minute": 60,
        "requested_rate_limit_per_hour": 3600,
        "requested_rate_limit_per_day": 50000,
        "requested_monthly_quota": 100000,
    }

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        "/api-key-requests/submit/",
        token=token,
        data=request_payload,
    )
    assert success and response and response.status_code == 201 and resp_data and resp_data.get("request"), "Failed to submit pending API key request"

    request_info = {
        "username": username,
        "request_id": resp_data["request"]["request_id"],
    }
    test_data["pending_request"] = request_info
    return request_info


def ensure_rejected_request(internal_api_url, logger, test_data):
    """Ensure there is a rejected API key request available."""
    cached = test_data.get("rejected_request")
    if cached:
        ensure_user_token(cached["username"], internal_api_url, logger, test_data)
        return cached

    request_info = ensure_pending_request(internal_api_url, logger, test_data, force_new=True)
    admin_token = ensure_admin_token(internal_api_url, logger, test_data)

    rejection_payload = {
        "rejection_reason": "Automated rejection for integration tests",
        "admin_notes": "Generated to verify rejected user behavior",
    }

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        f"/admin/api-key-requests/{request_info['request_id']}/reject/",
        token=admin_token,
        data=rejection_payload,
    )
    assert success and response and response.status_code == 200 and resp_data and resp_data.get("request"), "Failed to reject API key request"

    rejected_info = {
        "username": request_info["username"],
        "request_id": request_info["request_id"],
    }
    test_data["rejected_request"] = rejected_info
    return rejected_info
