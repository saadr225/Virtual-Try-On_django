"""
Admin User Management endpoint tests.
Tests: /admin/users/, /admin/users/create/, /admin/users/statistics/, /admin/users/id/{user_id}/, /admin/users/{username}/, /admin/users/{username}/update/, /admin/users/{username}/suspend/, /admin/users/{username}/verify/, /admin/users/{username}/premium/, /admin/users/{username}/change-password/, /admin/users/{username}/delete/, /admin/users/{username}/api-keys/suspend/, /admin/users/quotas/, /admin/users/search/, /admin/users/{username}/quota/, /admin/users/{username}/quota/update/
"""

import pytest
from conftest import make_request, log_section


def test_01_list_all_users(internal_api_url, logger, test_data):
    """Test admin listing all users."""
    log_section(logger, "TEST: ADMIN - LIST ALL USERS (/admin/users/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"page": 1, "limit": 20}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/", token=token, params=params)

    assert success, f"List all users failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "users" in resp_data, "Users list not found in response"

    users = resp_data["users"]
    pagination = resp_data.get("pagination", {})
    logger.info(f"✓ Listed all users:")
    logger.info(f"  - Fetched: {len(users)}")
    logger.info(f"  - Total: {pagination.get('total')}")
    logger.info(f"  - Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")
    for user in users[:3]:
        logger.info(f"    • {user.get('username')} ({user.get('email')})")


def test_02_admin_create_user(internal_api_url, logger, test_data):
    """Test admin creating a new user."""
    log_section(logger, "TEST: ADMIN - CREATE USER (/admin/users/create/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    import time

    new_username = f"admin_created_{int(time.time())}"
    new_email = f"{new_username}@test.local"

    data = {
        "username": new_username,
        "email": new_email,
        "password": "AdminCreated123!",
        "first_name": "Admin",
        "last_name": "Created",
        "user_type": "customer",
    }

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/admin/users/create/", token=token, data=data)

    assert success, f"Create user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "user" in resp_data, "User data not found in response"

    user = resp_data["user"]
    logger.info(f"✓ User created by admin:")
    logger.info(f"  - Username: {user.get('username')}")
    logger.info(f"  - Email: {user.get('email')}")
    logger.info(f"  - ID: {user.get('id')}")


def test_03_admin_get_user_statistics(internal_api_url, logger, test_data):
    """Test admin getting user statistics."""
    log_section(logger, "TEST: ADMIN - GET USER STATISTICS (/admin/users/statistics/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/statistics/", token=token)

    assert success, f"Get statistics failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "statistics" in resp_data, "Statistics not found in response"

    stats = resp_data["statistics"]
    logger.info(f"✓ Retrieved user statistics:")
    logger.info(f"  - Total Users: {stats.get('total_users')}")
    logger.info(f"  - Active Users: {stats.get('active_users')}")
    logger.info(f"  - Suspended Users: {stats.get('suspended_users')}")
    logger.info(f"  - Verified Users: {stats.get('verified_users')}")
    logger.info(f"  - Premium Users: {stats.get('premium_users')}")
    logger.info(f"  - New Users (Last 30 days): {stats.get('new_users_last_30_days')}")


def test_04_admin_get_user_by_id(internal_api_url, logger, test_data):
    """Test admin getting user by ID."""
    log_section(logger, "TEST: ADMIN - GET USER BY ID (/admin/users/id/{user_id}/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    # Use first regular user's id (get from /admin/users/ first)
    params = {"page": 1, "limit": 1}
    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/", token=token, params=params)

    if not (success and resp_data and "users" in resp_data and len(resp_data["users"]) > 0):
        pytest.skip("Could not get any users")

    user_id = resp_data["users"][0].get("id")

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/users/id/{user_id}/", token=token)

    assert success, f"Get user by ID failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "user" in resp_data, "User not found in response"

    user = resp_data["user"]
    logger.info(f"✓ Retrieved user by ID:")
    logger.info(f"  - Username: {user.get('username')}")
    logger.info(f"  - Email: {user.get('email')}")
    logger.info(f"  - User Type: {user.get('user_type')}")


def test_05_admin_get_user_by_username(internal_api_url, logger, test_data):
    """Test admin getting user by username."""
    log_section(logger, "TEST: ADMIN - GET USER BY USERNAME (/admin/users/{username}/)")

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

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/users/{target_username}/", token=token)

    assert success, f"Get user by username failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "user_details" in resp_data, "User details not found in response"

    user_details = resp_data["user_details"]
    user_info = user_details.get("user_info", {})
    logger.info(f"✓ Retrieved user by username:")
    logger.info(f"  - Username: {user_info.get('username')}")
    logger.info(f"  - Email: {user_info.get('email')}")
    logger.info(f"  - User Type: {user_info.get('user_type')}")


def test_06_admin_update_user(internal_api_url, logger, test_data):
    """Test admin updating user details."""
    log_section(logger, "TEST: ADMIN - UPDATE USER (/admin/users/{username}/update/)")

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

    data = {
        "first_name": "Admin Updated",
        "last_name": "User",
        "phone_number": "+9876543210",
    }

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/users/{target_username}/update/", token=token, data=data)

    assert success, f"Update user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User updated successfully")


def test_07_admin_verify_user(internal_api_url, logger, test_data):
    """Test admin verifying a user account."""
    log_section(logger, "TEST: ADMIN - VERIFY USER (/admin/users/{username}/verify/)")

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

    data = {"is_verified": True}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/verify/", token=token, data=data)

    assert success, f"Verify user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User verified successfully")


def test_08_admin_set_premium_status(internal_api_url, logger, test_data):
    """Test admin setting user premium status."""
    log_section(logger, "TEST: ADMIN - SET PREMIUM STATUS (/admin/users/{username}/premium/)")

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

    data = {"is_premium": True, "premium_expiry": "2025-12-31T23:59:59Z"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/premium/", token=token, data=data)

    assert success, f"Set premium status failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ Premium status granted successfully")


def test_09_admin_suspend_user(internal_api_url, logger, test_data):
    """Test admin suspending a user."""
    log_section(logger, "TEST: ADMIN - SUSPEND USER (/admin/users/{username}/suspend/)")

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

    data = {"is_suspended": True, "suspension_reason": "Violation of terms"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/suspend/", token=token, data=data)

    assert success, f"Suspend user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User suspended successfully")


def test_10_admin_unsuspend_user(internal_api_url, logger, test_data):
    """Test admin unsuspending a user."""
    log_section(logger, "TEST: ADMIN - UNSUSPEND USER (/admin/users/{username}/suspend/)")

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

    data = {"is_suspended": False}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/suspend/", token=token, data=data)

    assert success, f"Unsuspend user failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User unsuspended successfully")


def test_11_admin_change_user_password(internal_api_url, logger, test_data):
    """Test admin changing user password."""
    log_section(logger, "TEST: ADMIN - CHANGE USER PASSWORD (/admin/users/{username}/change-password/)")

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

    data = {"new_password": "AdminChanged123!"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/change-password/", token=token, data=data)

    assert success, f"Change password failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User password changed by admin")


def test_12_admin_list_user_quotas(internal_api_url, logger, test_data):
    """Test admin listing all users with quotas."""
    log_section(logger, "TEST: ADMIN - LIST ALL USERS QUOTAS (/admin/users/quotas/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"page": 1, "limit": 10}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/quotas/", token=token, params=params)

    assert success, f"List user quotas failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "users" in resp_data, "Users list not found"

    users = resp_data["users"]
    pagination = resp_data.get("pagination", {})
    logger.info(f"✓ Listed users with quotas:")
    logger.info(f"  - Fetched: {len(users)}")
    logger.info(f"  - Total: {pagination.get('total')}")
    for user in users[:2]:
        logger.info(f"    • {user.get('username')}: {user.get('current_api_keys')}/{user.get('max_api_keys')} keys")


def test_13_admin_search_users(internal_api_url, logger, test_data):
    """Test admin searching for users."""
    log_section(logger, "TEST: ADMIN - SEARCH USERS (/admin/users/search/)")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    search_query = "test"
    params = {"q": search_query, "page": 1, "limit": 10}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/search/", token=token, params=params)

    assert success, f"Search users failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "users" in resp_data, "Users search results not found"

    users = resp_data["users"]
    logger.info(f"✓ Search results for '{search_query}':")
    logger.info(f"  - Found: {len(users)} user(s)")
    for user in users[:3]:
        logger.info(f"    • {user.get('username')} ({user.get('email')})")


def test_14_admin_get_user_quota(internal_api_url, logger, test_data):
    """Test admin getting specific user quota."""
    log_section(logger, "TEST: ADMIN - GET USER QUOTA (/admin/users/{username}/quota/)")

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

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/users/{target_username}/quota/", token=token)

    assert success, f"Get quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "user_quota" in resp_data, "User quota not found"

    quota = resp_data["user_quota"]
    logger.info(f"✓ Retrieved user quota:")
    logger.info(f"  - Max API Keys: {quota.get('max_api_keys')}")
    logger.info(f"  - Current API Keys: {quota.get('current_api_keys')}")
    logger.info(f"  - Monthly Quota: {quota.get('user_monthly_quota')}")
    logger.info(f"  - Quota Remaining: {quota.get('quota_remaining')}")


def test_15_admin_update_user_quota(internal_api_url, logger, test_data):
    """Test admin updating user quotas."""
    log_section(logger, "TEST: ADMIN - UPDATE USER QUOTA (/admin/users/{username}/quota/update/)")

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

    data = {
        "max_api_keys": 15,
        "user_monthly_quota": 2000,
        "default_rate_limit_per_minute": 120,
        "default_rate_limit_per_hour": 1200,
        "default_rate_limit_per_day": 12000,
        "default_monthly_quota": 600,
    }

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/users/{target_username}/quota/update/", token=token, data=data)

    assert success, f"Update quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ User quota updated:")
    logger.info(f"  - Max API Keys: 15")
    logger.info(f"  - Monthly Quota: 2000")


def test_16_admin_suspend_user_api_keys(internal_api_url, logger, test_data):
    """Test admin suspending all user API keys."""
    log_section(logger, "TEST: ADMIN - SUSPEND USER API KEYS (/admin/users/{username}/api-keys/suspend/)")

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

    data = {"action": "suspend", "reason": "Account under review"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/api-keys/suspend/", token=token, data=data)

    assert success, f"Suspend API keys failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ All user API keys suspended")


def test_17_admin_activate_user_api_keys(internal_api_url, logger, test_data):
    """Test admin activating all user API keys."""
    log_section(logger, "TEST: ADMIN - ACTIVATE USER API KEYS (/admin/users/{username}/api-keys/suspend/)")

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

    data = {"action": "activate", "reason": "Account review complete"}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/admin/users/{target_username}/api-keys/suspend/", token=token, data=data)

    assert success, f"Activate API keys failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info(f"✓ All user API keys activated")
