#!/usr/bin/env python
"""
Comprehensive API Endpoint Test Suite
=====================================
Tests all endpoints for the API Key Management System including:
- User authentication and registration
- User API key CRUD operations
- User quota management
- Admin user management
- Admin API key management
- Permission-based access control

Usage:
    pytest test_endpoints.py -v
    pytest test_endpoints.py --base-url http://localhost:8000 -v

Requirements:
    pip install requests colorama pytest
"""

import pytest
import requests
import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

try:
    from colorama import Fore, Back, Style, init

    COLORS_AVAILABLE = True
    init(autoreset=True)
except ImportError:
    COLORS_AVAILABLE = False

    class Fore:
        RED = GREEN = CYAN = YELLOW = WHITE = BLACK = ""

    class Back:
        RED = BLACK = ""

    class Style:
        RESET_ALL = ""


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored logging output."""

    COLORS = (
        {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Back.RED + Fore.WHITE,
        }
        if COLORS_AVAILABLE
        else {}
    )

    def format(self, record):
        if COLORS_AVAILABLE and record.levelname in self.COLORS:
            log_color = self.COLORS.get(record.levelname, Fore.WHITE)
            record.levelname = f"{log_color}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Set up colored logger for the test suite."""
    logger = logging.getLogger("APITestSuite")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    # Set encoding to handle Unicode on Windows
    if hasattr(console_handler.stream, "reconfigure"):
        console_handler.stream.reconfigure(encoding="utf-8")

    formatter = ColoredFormatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler for logs - with better structure
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(os.path.join(log_dir, "api_test_results.log"), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    # Simpler format for file with better readability
    file_formatter = logging.Formatter(fmt="%(message)s")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


@pytest.fixture(scope="session")
def base_url(request):
    """Fixture for base URL."""
    return request.config.getoption("--base-url", default="http://localhost:8000")


@pytest.fixture(scope="session")
def verbose(request):
    """Fixture for verbose logging."""
    return request.config.getoption("--verbose", default=False)


@pytest.fixture(scope="session")
def logger(verbose):
    """Fixture for logger."""
    return setup_logger(verbose)


@pytest.fixture(scope="session")
def test_data():
    """Fixture for shared test data."""
    return {
        "user_tokens": {},
        "test_users": {},
        "api_keys": {},
    }


@pytest.fixture(scope="session")
def internal_api_url(base_url):
    """Fixture for internal API URL."""
    return f"{base_url}/internal/api"


def _log_request(logger, method: str, endpoint: str, data: Any = None, headers: Dict = None):
    """Log outgoing request details."""
    # Console debug logging (verbose)
    auth_indicator = ""
    if headers and "Authorization" in headers:
        token = headers["Authorization"]
        if "Bearer" in token:
            auth_indicator = f" [Auth: {token[:30]}...]"

    if COLORS_AVAILABLE:
        logger.debug(f">> {Fore.BLUE}{method} {endpoint}{auth_indicator}{Style.RESET_ALL}")
    else:
        logger.debug(f">> {method} {endpoint}{auth_indicator}")

    if data:
        logger.debug(f"  Request Data: {json.dumps(data, indent=2)}")

    # File logging - more structured
    file_logger = logging.getLogger("APITestSuite")
    # Only log to file if not in debug mode (to keep it clean)
    if not logger.isEnabledFor(logging.DEBUG):
        for handler in file_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_logger.info(f"  [REQ] {method:6s} {endpoint}")
                break


def _log_response(logger, response: requests.Response, endpoint: str):
    """Log incoming response details."""
    status_color = Fore.GREEN if 200 <= response.status_code < 300 else Fore.RED
    status_str = f"{status_color}{response.status_code}{Style.RESET_ALL}" if COLORS_AVAILABLE else str(response.status_code)

    logger.debug(f"<< {status_str} from {endpoint}")
    try:
        response_data = response.json()
        if logger.isEnabledFor(logging.DEBUG) and response_data:
            logger.debug(f"  Response: {json.dumps(response_data, indent=2)}")

        # File logging - structured response info
        if not logger.isEnabledFor(logging.DEBUG):
            for handler in logging.getLogger("APITestSuite").handlers:
                if isinstance(handler, logging.FileHandler):
                    resp_code = response_data.get("code", "UNKNOWN") if response_data else "N/A"
                    logging.getLogger("APITestSuite").info(f"  [RES] {response.status_code} - {resp_code}")
                    break

        return response_data
    except:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"  Response: {response.text}")
        return None


def make_request(
    internal_api_url: str, logger, method: str, endpoint: str, token: Optional[str] = None, data: Optional[Dict] = None, params: Optional[Dict] = None
) -> Tuple[bool, Optional[requests.Response], Optional[Dict]]:
    """Make HTTP request and return success status, response object, and parsed JSON."""
    url = f"{internal_api_url}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    _log_request(logger, method, endpoint, data, headers)

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response_data = _log_response(logger, response, endpoint)
        success = 200 <= response.status_code < 300

        return success, response, response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return False, None, None


def log_section(logger, title: str):
    """Print a formatted section header."""
    if COLORS_AVAILABLE:
        logger.info(f"\n{Fore.CYAN}{Back.BLACK}{'='*70}")
        logger.info(f"{title.center(70)}")
        logger.info(f"{'='*70}{Style.RESET_ALL}\n")
    else:
        logger.info(f"\n{'='*70}")
        logger.info(f"{title.center(70)}")
        logger.info(f"{'='*70}\n")

    # Also log section to file
    logging.getLogger("APITestSuite").info(f"\n[SECTION] {title}")
    logging.getLogger("APITestSuite").info("-" * 60)


# ==================== AUTHENTICATION TESTS ====================


def test_user_registration(internal_api_url, logger, test_data):
    """Test user registration."""
    log_section(logger, "USER REGISTRATION TEST")

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

    test_data["test_users"][username] = {"email": email, "password": "TestPass123!", "username": username}
    logger.info(f"  User email: {email}")


def test_admin_login(internal_api_url, logger, test_data):
    """Test admin user login."""
    log_section(logger, "ADMIN LOGIN TEST")

    # Login with admin credentials
    admin_username = "admin"
    admin_password = "admin"

    data = {"username": admin_username, "password": admin_password}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/login/", data=data)

    # Store admin credentials even if login fails (for later tests to skip appropriately)
    if success and response.status_code == 200 and resp_data and "access" in resp_data:
        test_data["user_tokens"][admin_username] = {
            "access": resp_data["access"],
            "refresh": resp_data.get("refresh"),
            "user_type": resp_data.get("user_type", "admin"),
        }
        logger.info(f"  Admin user type: {test_data['user_tokens'][admin_username].get('user_type')}")
        logger.info("  Admin access token obtained")
    else:
        logger.warning("  Admin login failed - admin tests will be skipped")


def test_user_login(internal_api_url, logger, test_data):
    """Test user login and token retrieval."""
    log_section(logger, "USER LOGIN TEST")

    # Get the first test user
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
    logger.info(f"  User type: {test_data['user_tokens'][username].get('user_type')}")
    logger.info("  Access token obtained")


def test_token_refresh(internal_api_url, logger, test_data):
    """Test JWT token refresh."""
    log_section(logger, "TOKEN REFRESH TEST")

    username = list(test_data["user_tokens"].keys())[0]
    token = test_data["user_tokens"][username].get("refresh")
    assert token, f"No refresh token found for user {username}"

    data = {"refresh": token}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/token/refresh/", data=data)

    assert success, f"Token refresh failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "access" in resp_data, "New access token not found in response"

    # Update stored tokens
    test_data["user_tokens"][username]["access"] = resp_data["access"]
    test_data["user_tokens"][username]["refresh"] = resp_data.get("refresh", token)
    logger.info("  New access token obtained")


def test_get_user_info(internal_api_url, logger, test_data):
    """Test getting current user information."""
    log_section(logger, "GET USER INFO TEST")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info(f"  Username: {user_info.get('username')}")
    logger.info(f"  Email: {user_info.get('email')}")
    logger.info(f"  User type: {user_info.get('user_type')}")


def test_update_user_profile(internal_api_url, logger, test_data):
    """Test updating user profile."""
    log_section(logger, "UPDATE USER PROFILE TEST")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info("  Profile updated successfully")


def test_change_password(internal_api_url, logger, test_data):
    """Test changing user password."""
    log_section(logger, "CHANGE PASSWORD TEST")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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

    # Update stored password for future tests
    test_data["test_users"][username]["password"] = new_password
    logger.info("  Password changed successfully")


def test_user_logout(internal_api_url, logger, test_data):
    """Test user logout."""
    log_section(logger, "USER LOGOUT TEST")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info("  User logged out successfully")


# ==================== USER QUOTA TESTS ====================


def test_get_user_quota(internal_api_url, logger, test_data):
    """Test retrieving user's quota information."""
    log_section(logger, "GET USER QUOTA")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info(f"  Max API Keys: {quota.get('max_api_keys')}")
    logger.info(f"  Current API Keys: {quota.get('current_api_keys')}")
    logger.info(f"  Can Create More: {quota.get('can_create_more')}")
    logger.info(f"  Monthly Quota Remaining: {quota.get('quota_remaining')}")
    logger.info(f"  API key generation enabled: {quota.get('api_key_generation_enabled')}")


# ==================== API KEY MANAGEMENT TESTS ====================


@pytest.mark.parametrize("key_name", ["production-key", "staging-key"])
def test_create_api_key(internal_api_url, logger, test_data, key_name):
    """Test creating a new API key."""
    log_section(logger, f"CREATE API KEY - {key_name}")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    data = {"name": key_name, "rate_limit_per_minute": 100, "rate_limit_per_hour": 1000, "rate_limit_per_day": 10000, "monthly_quota": 500}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=token, data=data)

    assert success, f"Create API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 201, f"Expected 201, got {response.status_code}"
    assert resp_data and "api_key" in resp_data, "API key data not found in response"

    key_id = resp_data["api_key"].get("key_id")
    test_data["api_keys"][key_name] = key_id
    logger.info(f"  Key ID: {key_id}")
    logger.info(f"  Name: {resp_data['api_key'].get('name')}")
    logger.info(f"  Status: {resp_data['api_key'].get('status')}")

    time.sleep(0.5)  # Small delay to avoid conflicts


def test_list_api_keys(internal_api_url, logger, test_data):
    """Test listing user's API keys."""
    log_section(logger, "LIST API KEYS")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info(f"  Total API Keys: {len(keys)}")
    pagination = resp_data.get("pagination", {})
    logger.info(f"  Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")
    for key in keys[:5]:
        logger.info(f"    - {key.get('name')}: {key.get('status')}")


def test_get_api_key_detail(internal_api_url, logger, test_data):
    """Test getting detailed information about an API key."""
    log_section(logger, "GET API KEY DETAIL")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info(f"  Name: {key.get('name')}")
    logger.info(f"  Status: {key.get('status')}")
    logger.info(f"  Rate Limits: {key.get('rate_limit_per_minute')}/min, {key.get('rate_limit_per_hour')}/hr, {key.get('rate_limit_per_day')}/day")
    logger.info(f"  Monthly Quota: {key.get('monthly_quota')}")
    logger.info(f"  Created: {key.get('created_at')}")


def test_update_api_key(internal_api_url, logger, test_data):
    """Test updating an API key."""
    log_section(logger, "UPDATE API KEY")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info("  Status updated to: inactive")


def test_regenerate_api_key(internal_api_url, logger, test_data):
    """Test regenerating an API key."""
    log_section(logger, "REGENERATE API KEY")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
            username = user
            break

    if not username:
        pytest.skip("No regular test user available")

    token = test_data["user_tokens"][username].get("access")
    key_name = "production-key"
    key_id = test_data["api_keys"].get(key_name)
    assert token, f"No token found for user {username}"
    assert key_id, f"No key_id found for {key_name}"

    data = {"confirm": True}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", f"/api-keys/{key_id}/regenerate/", token=token, data=data)

    assert success, f"Regenerate API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("  New API key generated (shown once)")


def test_get_api_key_stats(internal_api_url, logger, test_data):
    """Test getting API key usage statistics."""
    log_section(logger, "GET API KEY STATS")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info(f"  Total Requests: {stats.get('total_requests', 0)}")
    logger.info(f"  Requests This Month: {stats.get('requests_this_month', 0)}")
    logger.info(f"  Requests Today: {stats.get('requests_today', 0)}")
    logger.info(f"  Quota Remaining: {stats.get('quota_remaining', 0)}")


@pytest.mark.parametrize("key_name", ["production-key", "staging-key"])
def test_delete_api_key(internal_api_url, logger, test_data, key_name):
    """Test deleting an API key."""
    log_section(logger, f"DELETE API KEY - {key_name}")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
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
    logger.info("  API key deleted successfully")


# ==================== ADMIN TESTS ====================


def test_list_all_users_quotas(internal_api_url, logger, test_data):
    """Test admin listing all users with quotas."""
    log_section(logger, "ADMIN: LIST ALL USERS QUOTAS")

    # Try to find admin user in test_data, if not, skip
    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"page": 1, "limit": 10}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/quotas/", token=token, params=params)

    assert success, f"List all users quotas failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "users" in resp_data, "Users list not found in response"

    users = resp_data["users"]
    logger.info(f"  Total Users Fetched: {len(users)}")
    for user in users[:3]:
        logger.info(f"    - {user.get('username')}: {user.get('current_api_keys')}/{user.get('max_api_keys')} keys")


def test_search_users(internal_api_url, logger, test_data):
    """Test admin searching for users."""
    log_section(logger, "ADMIN: SEARCH USERS")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    search_query = list(test_data["test_users"].keys())[0]  # Search for the test user
    params = {"q": search_query, "page": 1, "limit": 10}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/search/", token=token, params=params)

    assert success, f"Search users failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "users" in resp_data, "Users search results not found in response"

    users = resp_data["users"]
    logger.info(f"  Search Results: {len(users)} user(s) found")
    for user in users[:5]:
        logger.info(f"    - {user.get('username')} ({user.get('email')})")


def test_get_user_details(internal_api_url, logger, test_data):
    """Test admin getting comprehensive user details."""
    log_section(logger, "ADMIN: GET USER DETAILS")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    target_username = list(test_data["test_users"].keys())[0]

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/users/{target_username}/details/", token=token)

    assert success, f"Get user details failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "user_details" in resp_data, "User details not found in response"

    details = resp_data["user_details"]
    user_info = details.get("user_info", {})
    quota_info = details.get("quota_info", {})
    activity = details.get("activity_summary", {})

    logger.info("  User Info:")
    logger.info(f"    - Username: {user_info.get('username')}")
    logger.info(f"    - Email: {user_info.get('email')}")
    logger.info(f"    - Type: {user_info.get('user_type')}")

    logger.info("  Quota Info:")
    logger.info(f"    - Max API Keys: {quota_info.get('max_api_keys')}")
    logger.info(f"    - Monthly Quota: {quota_info.get('user_monthly_quota')}")

    logger.info("  Activity Summary:")
    logger.info(f"    - Total API Keys: {activity.get('total_api_keys')}")
    logger.info(f"    - Requests (Last 30 days): {activity.get('requests_last_30_days')}")


def test_admin_get_user_quota(internal_api_url, logger, test_data):
    """Test admin getting specific user quota."""
    log_section(logger, "ADMIN: GET USER QUOTA")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    target_username = list(test_data["test_users"].keys())[0]

    success, response, resp_data = make_request(internal_api_url, logger, "GET", f"/admin/users/{target_username}/quota/", token=token)

    assert success, f"Admin get quota failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # The response has "user_quota" not "quota_info"
    assert resp_data and "user_quota" in resp_data, "User quota not found in response"

    quota = resp_data["user_quota"]
    logger.info(f"  Max API Keys: {quota.get('max_api_keys')}")
    logger.info(f"  Current API Keys: {quota.get('current_api_keys')}")
    logger.info(f"  Monthly Quota: {quota.get('user_monthly_quota')}")
    logger.info(f"  Quota Remaining: {quota.get('quota_remaining')}")


def test_update_user_quota(internal_api_url, logger, test_data):
    """Test admin updating user quotas."""
    log_section(logger, "ADMIN: UPDATE USER QUOTA")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    target_username = list(test_data["test_users"].keys())[0]

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
    logger.info("  Max API Keys: 15")
    logger.info("  Monthly Quota: 2000")
    logger.info("  Default Rate Limits: 120/min, 1200/hr, 12000/day")


def test_list_all_api_keys(internal_api_url, logger, test_data):
    """Test admin listing all API keys across all users."""
    log_section(logger, "ADMIN: LIST ALL API KEYS")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    token = test_data["user_tokens"][admin_username].get("access")
    assert token, f"No token found for admin {admin_username}"

    params = {"page": 1, "limit": 10}

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/api-keys/", token=token, params=params)

    assert success, f"List all API keys failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "api_keys" in resp_data, "API keys list not found in response"

    keys = resp_data["api_keys"]
    logger.info(f"  Total API Keys: {len(keys)}")
    for key in keys[:3]:
        logger.info(f"    - {key.get('name')} (User: {key.get('username')}): {key.get('status')}")


def test_admin_create_api_key_for_testing(internal_api_url, logger, test_data):
    """Test admin creating API keys for testing admin update/delete operations."""
    log_section(logger, "ADMIN: CREATE API KEY FOR ADMIN TESTS")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    # Get a regular test user to create API keys for
    regular_username = None
    for user in test_data["test_users"].keys():
        regular_username = user
        break

    if not regular_username:
        pytest.skip("No regular user available to create API keys for")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    regular_token = test_data["user_tokens"][regular_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"
    assert regular_token, f"No token found for user {regular_username}"

    # Create API keys using the regular user's token (to ensure they exist for admin operations)
    for key_name in ["admin-test-key-1", "admin-test-key-2"]:
        data = {"name": key_name, "rate_limit_per_minute": 100, "rate_limit_per_hour": 1000, "rate_limit_per_day": 10000, "monthly_quota": 500}

        success, response, resp_data = make_request(internal_api_url, logger, "POST", "/api-keys/create/", token=regular_token, data=data)

        if success and response.status_code == 201 and resp_data and "api_key" in resp_data:
            key_id = resp_data["api_key"].get("key_id")
            test_data["api_keys"][key_name] = key_id
            logger.info(f"  Created {key_name}: {key_id}")
        else:
            logger.warning(f"  Failed to create {key_name}")

    logger.info(f"  Total API keys available for admin tests: {len(test_data['api_keys'])}")


def test_admin_update_api_key(internal_api_url, logger, test_data):
    """Test admin updating any user's API key."""
    log_section(logger, "ADMIN: UPDATE ANY API KEY")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"

    # Find any API key to update (prioritize admin-test keys)
    key_name = None
    for name in ["admin-test-key-1", "admin-test-key-2"]:
        if name in test_data["api_keys"]:
            key_name = name
            break

    if not key_name and test_data["api_keys"]:
        key_name = list(test_data["api_keys"].keys())[0]

    if not key_name:
        pytest.skip("No API keys available for admin update test")

    key_id = test_data["api_keys"][key_name]

    data = {"status": "active", "rate_limit_per_minute": 200}

    success, response, resp_data = make_request(internal_api_url, logger, "PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

    assert success, f"Admin update API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("  Status: active")
    logger.info("  Rate limit: 200/min")


def test_admin_delete_api_key(internal_api_url, logger, test_data):
    """Test admin deleting any user's API key."""
    log_section(logger, "ADMIN: DELETE ANY API KEY")

    admin_username = None
    for username, token_data in test_data["user_tokens"].items():
        if token_data.get("user_type") in ["admin", "staff"]:
            admin_username = username
            break

    if not admin_username:
        pytest.skip("No admin user available for admin tests")

    admin_token = test_data["user_tokens"][admin_username].get("access")
    assert admin_token, f"No token found for admin {admin_username}"

    # Find any API key to delete (prioritize admin-test keys)
    key_name = None
    for name in ["admin-test-key-2"]:  # Use the second test key for deletion
        if name in test_data["api_keys"]:
            key_name = name
            break

    if not key_name and test_data["api_keys"]:
        # Find any remaining key
        for name in list(test_data["api_keys"].keys()):
            if name.startswith("admin-test-"):
                key_name = name
                break

    if not key_name:
        pytest.skip("No API keys available for admin delete test")

    key_id = test_data["api_keys"][key_name]

    success, response, resp_data = make_request(internal_api_url, logger, "DELETE", f"/admin/api-keys/{key_id}/delete/", token=admin_token)

    assert success, f"Admin delete API key failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    if key_name in test_data["api_keys"]:
        del test_data["api_keys"][key_name]
    logger.info("  API key deleted successfully")


# ==================== PERMISSION TESTS ====================


def test_non_admin_cannot_access_admin_endpoints(internal_api_url, logger, test_data):
    """Test that non-admin users cannot access admin endpoints."""
    log_section(logger, "PERMISSION TEST: Non-admin access denied")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
            username = user
            break

    if not username:
        pytest.skip("No regular test user available for permission test")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    success, response, resp_data = make_request(internal_api_url, logger, "GET", "/admin/users/quotas/", token=token)

    assert response is not None, "Request failed - no response object"

    # Note: If the server is not properly restricting access, this test will fail
    # The expected behavior is 403 Forbidden for non-admin users
    if response.status_code == 200:
        logger.warning(f"⚠ WARNING: Non-admin user '{username}' was able to access admin endpoint!")
        logger.warning("  This is a security issue - admin endpoints should be restricted")
        pytest.fail("Non-admin user should not access admin endpoint (got 200 instead of 403)")

    assert response.status_code == 403, f"Non-admin should not access admin endpoint (got {response.status_code})"
    logger.info("✓ Non-admin access denied to admin endpoint (403 Forbidden)")


# ==================== GENERAL ENDPOINTS TESTS ====================


def test_healthcheck(base_url, logger):
    """Test healthcheck endpoint."""
    log_section(logger, "HEALTHCHECK TEST")

    # Based on URL patterns, healthcheck is at /api/v1/ not /api/v1/health/
    success, response, resp_data = make_request(base_url, logger, "GET", "/api/v1/")

    assert success, f"Healthcheck failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ Healthcheck passed")


def test_homepage(base_url, logger):
    """Test homepage endpoint."""
    log_section(logger, "HOMEPAGE TEST")

    success, response, resp_data = make_request(base_url, logger, "GET", "/")

    assert success, f"Homepage failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("✓ Homepage accessible")


# ==================== VTON ENDPOINTS TESTS ====================


def test_vton_list_requests(internal_api_url, logger):
    """Test listing VTON requests."""
    log_section(logger, "VTON LIST REQUESTS TEST")

    success, response, resp_data = make_request(internal_api_url.replace("/internal/api", "/api/v1"), logger, "GET", "/virtual-tryon/requests/")

    assert success, f"List VTON requests failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert resp_data and "requests" in resp_data, "Requests list not found in response"

    requests_list = resp_data["requests"]
    logger.info(f"  Total Requests: {len(requests_list)}")
    logger.info(f"  Count: {resp_data.get('count', 'N/A')}")


def test_vton_get_request_status(internal_api_url, logger):
    """Test getting VTON request status."""
    log_section(logger, "VTON GET REQUEST STATUS TEST")

    # Use a dummy UUID to test the endpoint
    dummy_request_id = "12345678-1234-5678-9012-123456789012"

    success, response, resp_data = make_request(internal_api_url.replace("/internal/api", "/api/v1"), logger, "GET", f"/virtual-tryon/{dummy_request_id}/status/")

    # We expect this to return 404 for non-existent request
    assert response is not None, "Request failed - no response object"
    assert response.status_code == 404, f"Expected 404 for non-existent request, got {response.status_code}"
    logger.info("✓ Endpoint correctly returned 404 for non-existent request")


# Commented out VTON virtual tryon process test as requested
# def test_vton_virtual_tryon(internal_api_url, logger):
#     """Test virtual try-on processing (requires image files)."""
#     log_section(logger, "VTON VIRTUAL TRY-ON TEST")
#
#     # Note: This test requires actual image files to work properly
#     # For now, we'll test the endpoint structure and error handling
#     logger.info("  Note: This test requires person_image and clothing_image files")
#     logger.info("  Skipping actual file upload test - would need test images")
#
#     # Test with missing files to verify error handling
#     success, response, resp_data = make_request(internal_api_url.replace("/internal/api", "/api/v1"), logger, "POST", "/virtual-tryon/process/")
#
#     # We expect this to fail due to missing files
#     assert response is not None, "Request failed - no response object"
#     assert response.status_code in [400, 415], f"Expected 400 or 415 for missing files, got {response.status_code}"
#     logger.info(f"✓ Endpoint responded correctly to missing files (status: {response.status_code})")


# ==================== CLEANUP ====================


def test_delete_account(internal_api_url, logger, test_data):
    """Test account deletion (soft delete)."""
    log_section(logger, "DELETE ACCOUNT TEST")

    # Get a non-admin user for this test
    username = None
    for user, token_data in test_data["user_tokens"].items():
        if user in test_data["test_users"]:  # Only test users, not admin
            username = user
            break

    if not username:
        pytest.skip("No regular test user available for account deletion test")

    token = test_data["user_tokens"][username].get("access")
    assert token, f"No token found for user {username}"

    password = test_data["test_users"][username]["password"]
    data = {"password": password, "confirm": True}

    success, response, resp_data = make_request(internal_api_url, logger, "POST", "/auth/delete-account/", token=token, data=data)

    assert success, f"Delete account failed with status {response.status_code if response else 'unknown'}"
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    logger.info("  Account deleted successfully (soft delete)")


# Add pytest configuration
def pytest_configure(config):
    """Add custom markers."""
    config.addinivalue_line("markers", "admin: marks tests that require admin privileges")


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption("--base-url", action="store", default="http://localhost:8000", help="Base URL of the API")
    parser.addoption("--verbose", action="store_true", help="Enable verbose logging")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
