"""
API Key Request System endpoint tests.
Tests: /api-key-requests/submit, /api-key-requests/my-requests, /api-key-requests/{request_id},
        /admin/api-key-requests, /admin/api-key-requests/{request_id}/approve,
        /admin/api-key-requests/{request_id}/reject
"""

import pytest
import time
from conftest import make_request, log_section


def test_01_submit_api_key_request(internal_api_url, logger, test_data):
    """Test submitting an API key request (should succeed for unapproved users)."""
    log_section(logger, "TEST: SUBMIT API KEY REQUEST")

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
        "requested_key_name": "test-ecommerce-key",
        "reason": "Virtual try-on integration for our fashion e-commerce platform",
        "intended_use": "We plan to integrate on product pages and checkout flow",
        "requested_rate_limit_per_minute": 100,
        "requested_rate_limit_per_hour": 5000,
        "requested_rate_limit_per_day": 50000,
        "requested_monthly_quota": 1000000,
    }

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-key-requests/submit/", token=token, data=data)

    assert success, f"Submit API key request failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "request" in resp_data, "Request data not found in response"

    request_data = resp_data["request"]
    request_id = request_data.get("request_id")
    status = request_data.get("status")

    # Store request data for later tests
    if "api_key_requests" not in test_data:
        test_data["api_key_requests"] = {}
    test_data["api_key_requests"][username] = {
        "request_id": request_id,
        "status": status,
    }

    logger.info(f"✓ API key request submitted:")
    logger.info(f"  - Request ID: {request_id}")
    logger.info(f"  - Key Name: {request_data.get('requested_key_name')}")
    logger.info(f"  - Status: {status}")
    logger.info(f"  - Created: {request_data.get('created_at')}")

    assert status == "pending", f"Expected status 'pending', got '{status}'"


def test_02_submit_duplicate_request(internal_api_url, logger, test_data):
    """Test that submitting another request with the same name fails when one is already pending."""
    log_section(logger, "TEST: SUBMIT DUPLICATE REQUEST (same name, should fail)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    # Get the existing request name from test_data
    existing_request = test_data.get("api_key_requests", {}).get(username, {})
    if not existing_request:
        pytest.skip("No existing request found for user")

    # Try to submit with the same name (should fail)
    data = {
        "requested_key_name": "test-ecommerce-key",  # Same as test_01
        "reason": "Different reason",
    }

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-key-requests/submit/", token=token, data=data)

    # This should fail because user already has a pending request with this name
    assert not success or response.status_code == 400, f"Expected failure (400), but got {response.status_code}"
    logger.info(f"✓ Duplicate request (same name) correctly rejected with status {response.status_code}")


def test_03_list_my_api_key_requests(internal_api_url, logger, test_data):
    """Test listing user's own API key requests."""
    log_section(logger, "TEST: LIST MY API KEY REQUESTS")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/api-key-requests/", token=token)

    assert success, f"List my requests failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "requests" in resp_data, "Requests list not found in response"

    requests_list = resp_data["requests"]
    pagination = resp_data.get("pagination", {})

    logger.info(f"✓ Listed user's API key requests:")
    logger.info(f"  - Total: {len(requests_list)}")
    logger.info(f"  - Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")

    for req in requests_list[:3]:
        logger.info(f"    • {req.get('request_id')}: {req.get('status')} - {req.get('business_name')}")


def test_04_list_my_requests_with_filter(internal_api_url, logger, test_data):
    """Test listing requests with status filter."""
    log_section(logger, "TEST: LIST MY REQUESTS WITH FILTER")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    # Filter by pending status
    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "GET",
        "/api-key-requests/",
        token=token,
        params={"status": "pending"},
    )

    assert success, f"Filter requests failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    pending_requests = resp_data.get("requests", [])
    logger.info(f"✓ Filtered pending requests: {len(pending_requests)} found")

    for req in pending_requests:
        assert req.get("status") == "pending", f"Expected pending, got {req.get('status')}"


def test_05_get_request_detail(internal_api_url, logger, test_data):
    """Test getting details of a specific API key request."""
    log_section(logger, "TEST: GET API KEY REQUEST DETAIL")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    request_id = test_data.get("api_key_requests", {}).get(username, {}).get("request_id")

    assert token, f"No token found for user {username}"
    assert request_id, f"No request_id found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/api-key-requests/{request_id}/", token=token)

    assert success, f"Get request detail failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "request" in resp_data, "Request data not found in response"

    request_data = resp_data["request"]
    logger.info(f"✓ Retrieved API key request details:")
    logger.info(f"  - Request ID: {request_data.get('request_id')}")
    logger.info(f"  - Key Name: {request_data.get('requested_key_name')}")
    logger.info(f"  - Reason: {request_data.get('reason')}")
    logger.info(f"  - Intended Use: {request_data.get('intended_use')}")
    logger.info(f"  - Status: {request_data.get('status')}")
    logger.info(f"  - Created: {request_data.get('created_at')}")


def test_06_admin_list_all_requests(internal_api_url, logger, test_data):
    """Test admin listing all API key requests (Staff/Admin only)."""
    log_section(logger, "TEST: ADMIN LIST ALL API KEY REQUESTS")

    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if not admin_token:
        pytest.skip("Admin user not available or not logged in")

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-key-requests/", token=admin_token)

    assert success, f"Admin list requests failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "requests" in resp_data, "Requests list not found in response"

    requests_list = resp_data["requests"]
    pagination = resp_data.get("pagination", {})

    logger.info(f"✓ Admin listed all API key requests:")
    logger.info(f"  - Total: {len(requests_list)}")
    logger.info(f"  - Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")

    for req in requests_list[:3]:
        logger.info(f"    • {req.get('request_id')}: {req.get('status')} - User: {req.get('user')} - {req.get('business_name')}")


def test_07_admin_filter_pending_requests(internal_api_url, logger, test_data):
    """Test admin filtering pending requests."""
    log_section(logger, "TEST: ADMIN FILTER PENDING REQUESTS")

    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if not admin_token:
        pytest.skip("Admin user not available or not logged in")

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "GET",
        "/admin/api-key-requests/",
        token=admin_token,
        params={"status": "pending"},
    )

    assert success, f"Filter pending failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    pending_requests = resp_data.get("requests", [])
    logger.info(f"✓ Found {len(pending_requests)} pending requests")

    for req in pending_requests:
        assert req.get("status") == "pending", f"Expected pending, got {req.get('status')}"


def test_08_admin_get_request_detail(internal_api_url, logger, test_data):
    """Test admin getting details of a specific request."""
    log_section(logger, "TEST: ADMIN GET REQUEST DETAIL")

    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if not admin_token:
        pytest.skip("Admin user not available or not logged in")

    # Find a pending request to get details for
    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "GET",
        "/admin/api-key-requests/",
        token=admin_token,
        params={"status": "pending", "limit": 1},
    )

    if not success or not resp_data.get("requests"):
        pytest.skip("No pending requests available to test")

    request_id = resp_data["requests"][0].get("request_id")

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/api-key-requests/{request_id}/", token=admin_token)

    assert success, f"Get request detail failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    request_data = resp_data.get("request")
    logger.info(f"✓ Admin retrieved request details:")
    logger.info(f"  - Request ID: {request_data.get('request_id')}")
    logger.info(f"  - User: {request_data.get('user')}")
    logger.info(f"  - Key Name: {request_data.get('requested_key_name')}")
    logger.info(f"  - Status: {request_data.get('status')}")
    logger.info(f"  - Reason: {request_data.get('reason')}")


def test_09_admin_approve_request(internal_api_url, logger, test_data):
    """Test admin approving an API key request."""
    log_section(logger, "TEST: ADMIN APPROVE API KEY REQUEST")

    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if not admin_token:
        pytest.skip("Admin user not available or not logged in")

    # Find a pending request to approve
    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "GET",
        "/admin/api-key-requests/",
        token=admin_token,
        params={"status": "pending", "limit": 1},
    )

    if not success or not resp_data.get("requests"):
        pytest.skip("No pending requests available to test")

    request_id = resp_data["requests"][0].get("request_id")

    # Approve the request with quota details
    approval_data = {
        "payment_date": "2025-11-20",
        "payment_amount": "99.99",
        "admin_notes": "Approved for standard tier",
        "approved_rate_limit_per_minute": 100,
        "approved_rate_limit_per_hour": 5000,
        "approved_rate_limit_per_day": 50000,
        "approved_monthly_quota": 1000000,
        "max_api_keys": 5,
        "user_monthly_quota": 1000000,
    }

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        f"/admin/api-key-requests/{request_id}/approve/",
        token=admin_token,
        data=approval_data,
    )

    assert success, f"Approve request failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    approved_request = resp_data.get("request")
    assert approved_request.get("status") == "approved", "Request was not approved"

    # Store approved request info for later tests
    test_data["approved_request_user"] = approved_request.get("user")
    test_data["approved_request_id"] = request_id

    logger.info(f"✓ Request approved:")
    logger.info(f"  - Request ID: {request_id}")
    logger.info(f"  - User: {approved_request.get('user')}")
    logger.info(f"  - Approved Rate Limit (per min): {approved_request.get('approved_rate_limit_per_minute')}")
    logger.info(f"  - Approved Monthly Quota: {approved_request.get('approved_monthly_quota')}")
    logger.info(f"  - Reviewed By: {approved_request.get('reviewed_by')}")


def test_10_approved_user_can_create_api_key(internal_api_url, logger, test_data):
    """Test that approved user can now create API keys."""
    log_section(logger, "TEST: APPROVED USER CREATE API KEY")

    approved_username = test_data.get("approved_request_user")

    if not approved_username:
        pytest.skip("No approved user available from previous test")

    # Get token for the approved user
    # If the user was not in our test users, we need to skip this
    token = test_data["user_tokens"].get(approved_username, {}).get("access")

    if not token:
        pytest.skip(f"No token available for approved user {approved_username}")

    # Try to create an API key
    data = {"name": "Approved API Key"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=token, data=data)

    assert success, f"Create API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "api_key" in resp_data, "API key data not found in response"

    key_id = resp_data["api_key"].get("key_id")
    logger.info(f"✓ Approved user successfully created API key:")
    logger.info(f"  - Key ID: {key_id}")
    logger.info(f"  - Name: {resp_data['api_key'].get('name')}")
    logger.info(f"  - Status: {resp_data['api_key'].get('status')}")


def test_11_admin_reject_request(internal_api_url, logger, test_data):
    """Test admin rejecting an API key request."""
    log_section(logger, "TEST: ADMIN REJECT API KEY REQUEST")

    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if not admin_token:
        pytest.skip("Admin user not available or not logged in")

    # Find another pending request to reject
    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "GET",
        "/admin/api-key-requests/",
        token=admin_token,
        params={"status": "pending", "limit": 1},
    )

    if not success or not resp_data.get("requests"):
        pytest.skip("No pending requests available to test rejection")

    request_id = resp_data["requests"][0].get("request_id")

    # Reject the request
    rejection_data = {
        "rejection_reason": "Use case does not align with our service policies",
        "admin_notes": "User requested features not currently available in our API",
    }

    success, response, resp_data = make_request(
        internal_api_url,
        logger,
        "POST",
        f"/admin/api-key-requests/{request_id}/reject/",
        token=admin_token,
        data=rejection_data,
    )

    assert success, f"Reject request failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    rejected_request = resp_data.get("request")
    assert rejected_request.get("status") == "rejected", "Request was not rejected"

    logger.info(f"✓ Request rejected:")
    logger.info(f"  - Request ID: {request_id}")
    logger.info(f"  - User: {rejected_request.get('user')}")
    logger.info(f"  - Rejection Reason: {rejected_request.get('rejection_reason')}")
    logger.info(f"  - Rejected By: {rejected_request.get('rejected_by')}")


def test_12_rejected_user_cannot_create_key(internal_api_url, logger, test_data):
    """Test that rejected user cannot create API keys."""
    log_section(logger, "TEST: REJECTED USER CANNOT CREATE API KEY")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")

    # Check if user's current request is rejected
    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/api-key-requests/", token=token, params={"status": "rejected"})

    rejected_requests = resp_data.get("requests", []) if success else []

    if not rejected_requests:
        pytest.skip("No rejected requests available to test")

    # Try to create an API key (should fail)
    data = {"name": "Attempt API Key"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=token, data=data)

    # Should fail because user is not approved
    assert not success or response.status_code in [403, 400], f"Expected failure, got {response.status_code}"
    logger.info(f"✓ Rejected user correctly prevented from creating API key (status: {response.status_code})")


def test_13_unapproved_user_cannot_create_key(internal_api_url, logger, test_data):
    """Test that unapproved user cannot create API keys."""
    log_section(logger, "TEST: UNAPPROVED USER CANNOT CREATE API KEY")

    # Create a new user without approval
    username = f"newuser_{int(time.time())}"
    email = f"{username}@test.local"

    # Register new user
    reg_data = {
        "username": username,
        "email": email,
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "first_name": "New",
        "last_name": "User",
    }

    reg_success, reg_response, reg_resp_data = make_request(internal_api_url, logger, "POST", "/auth/register/", data=reg_data)

    if not reg_success or reg_response.status_code != 201:
        pytest.skip("Failed to create new user for test")

    # Login new user
    login_data = {"username": username, "password": "TestPass123!"}
    login_success, login_response, login_resp_data = make_request(internal_api_url, logger, "POST", "/auth/login/", data=login_data)

    if not login_success or login_response.status_code != 200:
        pytest.skip("Failed to login new user")

    token = login_resp_data.get("access")

    # Try to create API key (should fail)
    key_data = {"name": "Unapproved Key"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=token, data=key_data)

    assert not success or response.status_code in [403, 400], f"Expected failure, got {response.status_code}"
    logger.info(f"✓ Unapproved user correctly prevented from creating API key (status: {response.status_code})")


def test_14_user_can_submit_new_request_after_rejection(internal_api_url, logger, test_data):
    """Test that user can submit a new request after rejection."""
    log_section(logger, "TEST: SUBMIT NEW REQUEST AFTER REJECTION")

    # Create a new user
    username = f"newuser2_{int(time.time())}"
    email = f"{username}@test.local"

    # Register
    reg_data = {
        "username": username,
        "email": email,
        "password": "TestPass123!",
        "password2": "TestPass123!",
    }

    reg_success, reg_response, _ = make_request(internal_api_url, logger, "POST", "/auth/register/", data=reg_data)

    if not reg_success or reg_response.status_code != 201:
        pytest.skip("Failed to create new user")

    # Login
    login_data = {"username": username, "password": "TestPass123!"}
    login_success, login_response, login_resp_data = make_request(internal_api_url, logger, "POST", "/auth/login/", data=login_data)

    if not login_success or login_response.status_code != 200:
        pytest.skip("Failed to login new user")

    token = login_resp_data.get("access")

    # Submit first request
    req_data_1 = {
        "requested_key_name": "first-key",
        "reason": "First request reason",
        "requested_rate_limit_per_minute": 10,
        "requested_rate_limit_per_hour": 500,
        "requested_rate_limit_per_day": 5000,
        "requested_monthly_quota": 100000,
    }

    success1, response1, resp_data1 = make_request(internal_api_url, logger, "POST", "/api-key-requests/submit/", token=token, data=req_data_1)

    if not success1 or response1.status_code != 201:
        pytest.skip("Failed to submit first request")

    request_id_1 = resp_data1.get("request", {}).get("request_id")

    # Admin rejects the first request
    admin_username = "admin"
    admin_token = test_data["user_tokens"].get(admin_username, {}).get("access")

    if admin_token and request_id_1:
        reject_data = {
            "rejection_reason": "Test rejection",
            "admin_notes": "Testing resubmission",
        }
        make_request(
            internal_api_url,
            logger,
            "POST",
            f"/admin/api-key-requests/{request_id_1}/reject/",
            token=admin_token,
            data=reject_data,
        )

    # Wait a bit
    time.sleep(1)

    # Submit second request (should succeed because first was rejected)
    req_data_2 = {
        "requested_key_name": "second-key",
        "reason": "Second request reason",
        "requested_rate_limit_per_minute": 20,
        "requested_rate_limit_per_hour": 1000,
        "requested_rate_limit_per_day": 10000,
        "requested_monthly_quota": 200000,
    }

    success2, response2, resp_data2 = make_request(internal_api_url, logger, "POST", "/api-key-requests/submit/", token=token, data=req_data_2)

    assert success2, f"Resubmission failed with status {response2.status_code if response2 else 'unknown'}"
    assert response2.status_code == 201, f"Expected 201, got {response2.status_code}"

    logger.info(f"✓ User successfully submitted new request after rejection")
