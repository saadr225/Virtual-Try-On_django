"""
Authentication endpoint tests.
Tests: /auth/register, /auth/login, /auth/me, /auth/profile, /auth/change-password, /auth/logout, /auth/token/refresh, /auth/delete-account
"""

import pytest
import time
from conftest import make_request, log_section


def test_01_user_registration(internal_api_url, logger, test_data):
    """Test user registration."""
    log_section(logger, "TEST: USER REGISTRATION")

    username = f"testuser_{int(time.time())}"
    email = f"{username}@test.local"

    data = {
        "username": username,
        "email": email,
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    }

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/register/", data=data)

    assert success, f"Registration failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "user" in resp_data, "User data not found in response"

    test_data["test_users"][username] = {"email": email, "password": "TestPass123!", "username": username}
    logger.info(f"✓ User registered: {email}")


def test_02_admin_login(internal_api_url, logger, test_data):
    """Test admin user login."""
    log_section(logger, "TEST: ADMIN LOGIN")

    admin_username = "admin"
    admin_password = "admin"

    data = {"username": admin_username, "password": admin_password}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/admin-login/", data=data)

    if success and response.status_code == 200 and resp_data and "access" in resp_data:
        test_data["user_tokens"][admin_username] = {
            "access": resp_data["access"],
            "refresh": resp_data.get("refresh"),
            "user_type": resp_data.get("user_type", "admin"),
        }
        logger.info(f"✓ Admin logged in (user_type: {test_data['user_tokens'][admin_username].get('user_type')})")
    else:
        logger.warning("⚠ Admin login failed - attempting to create admin user")
        
        # Try to create admin user
        admin_data = {
            "username": admin_username,
            "email": "admin@test.local",
            "password": admin_password,
            "password2": admin_password,
            "first_name": "Admin",
            "last_name": "User",
            "user_type": "admin",
        }
        
        create_success, create_response, create_resp_data = make_request(internal_api_url, logger, "POST", "/auth/register/", data=admin_data)
        
        if create_success and create_response.status_code == 201:
            logger.info("✓ Admin user created successfully")
            
            # Now try login again
            success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/admin-login/", data=data)
            
            if success and response.status_code == 200 and resp_data and "access" in resp_data:
                test_data["user_tokens"][admin_username] = {
                    "access": resp_data["access"],
                    "refresh": resp_data.get("refresh"),
                    "user_type": resp_data.get("user_type", "admin"),
                }
                logger.info(f"✓ Admin logged in after creation (user_type: {test_data['user_tokens'][admin_username].get('user_type')})")
            else:
                logger.error("✗ Admin login failed even after creating user")
        else:
            logger.error("✗ Failed to create admin user - admin tests will be skipped")


def test_03_user_login(internal_api_url, logger, test_data):
    """Test user login and token retrieval."""
    log_section(logger, "TEST: USER LOGIN")

    username = list(test_data["test_users"].keys())[0]
    password = test_data["test_users"][username]["password"]

    data = {"username": username, "password": password}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/login/", data=data)

    assert success, f"Login failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "access" in resp_data, "Access token not found in response"

    test_data["user_tokens"][username] = {
        "access": resp_data["access"],
        "refresh": resp_data.get("refresh"),
        "user_type": resp_data.get("user_type", "customer"),
    }
    logger.info(f"✓ User logged in (user_type: {test_data['user_tokens'][username].get('user_type')})")


def test_04_token_refresh(internal_api_url, logger, test_data):
    """Test JWT token refresh."""
    log_section(logger, "TEST: TOKEN REFRESH")

    username = list(test_data["user_tokens"].keys())[0]
    token = test_data["user_tokens"][username].get("refresh")
    assert token, f"No refresh token found for user {username}"

    data = {"refresh": token}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/token/refresh/", data=data)

    assert success, f"Token refresh failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "access" in resp_data, "New access token not found in response"

    test_data["user_tokens"][username]["access"] = resp_data["access"]
    test_data["user_tokens"][username]["refresh"] = resp_data.get("refresh", token)
    logger.info("✓ Token refreshed successfully")


def test_05_get_user_info(internal_api_url, logger, test_data):
    """Test getting current user information."""
    log_section(logger, "TEST: GET USER INFO (/auth/me/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        username = list(test_data["user_tokens"].keys())[0]

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/auth/me/", token=token)

    assert success, f"Get user info failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "user" in resp_data, "User data not found in response"

    user_info = resp_data["user"]
    logger.info(f"✓ Retrieved user info:")
    logger.info(f"  - Username: {user_info.get('username')}")
    logger.info(f"  - Email: {user_info.get('email')}")
    logger.info(f"  - User type: {user_info.get('user_type')}")


def test_06_update_user_profile(internal_api_url, logger, test_data):
    """Test updating user profile."""
    log_section(logger, "TEST: UPDATE USER PROFILE (/auth/profile/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    data = {"first_name": "Updated", "last_name": "TestUser", "phone_number": "+1234567890"}

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", "/auth/profile/", token=token, data=data)

    assert success, f"Update profile failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ Profile updated successfully")


def test_07_change_password(internal_api_url, logger, test_data):
    """Test changing user password."""
    log_section(logger, "TEST: CHANGE PASSWORD (/auth/change-password/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    old_password = test_data["test_users"][username]["password"]
    new_password = "NewTestPass123!"

    data = {"old_password": old_password, "new_password": new_password, "new_password2": new_password}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/change-password/", token=token, data=data)

    assert success, f"Change password failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    test_data["test_users"][username]["password"] = new_password
    logger.info("✓ Password changed successfully")


def test_08_user_logout(internal_api_url, logger, test_data):
    """Test user logout."""
    log_section(logger, "TEST: USER LOGOUT (/auth/logout/)")

    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    refresh_token = test_data["user_tokens"][username].get("refresh")
    access_token = test_data["user_tokens"][username].get("access")
    assert refresh_token, f"No refresh token found for user {username}"

    data = {"refresh": refresh_token}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/logout/", token=access_token, data=data)

    assert success, f"Logout failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ User logged out successfully")
