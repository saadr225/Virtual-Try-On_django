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
    python test_endpoints.py [--base-url http://localhost:8000] [--verbose]

Requirements:
    pip install requests colorama
"""

import requests
import json
import logging
import argparse
import time
import sys
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


class APITestSuite:
    """Main test suite class for API endpoint testing."""

    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip("/")
        self.internal_api_url = f"{self.base_url}/internal/api"
        self.logger = setup_logger(verbose)
        self.verbose = verbose

        # Storage for test data
        self.user_tokens: Dict[str, Dict] = {}
        self.test_users: Dict[str, Dict] = {}
        self.api_keys: Dict[str, str] = {}
        self.test_results = {"passed": 0, "failed": 0, "errors": []}

        self.logger.info(f"{'='*70}")
        self.logger.info(f"API Test Suite Initialized")
        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"{'='*70}\n")

    def _print_section(self, title: str):
        """Print a formatted section header."""
        if COLORS_AVAILABLE:
            self.logger.info(f"\n{Fore.CYAN}{Back.BLACK}{'='*70}")
            self.logger.info(f"{title.center(70)}")
            self.logger.info(f"{'='*70}{Style.RESET_ALL}\n")
        else:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"{title.center(70)}")
            self.logger.info(f"{'='*70}\n")

        # Also log section to file
        logging.getLogger("APITestSuite").info(f"\n[SECTION] {title}")
        logging.getLogger("APITestSuite").info("-" * 60)

    def _log_request(self, method: str, endpoint: str, data: Any = None, headers: Dict = None):
        """Log outgoing request details."""
        full_url = f"{self.internal_api_url}{endpoint}"

        # Console debug logging (verbose)
        auth_indicator = ""
        if headers and "Authorization" in headers:
            token = headers["Authorization"]
            if "Bearer" in token:
                auth_indicator = f" [Auth: {token[:30]}...]"

        if COLORS_AVAILABLE:
            self.logger.debug(f">> {Fore.BLUE}{method} {endpoint}{auth_indicator}{Style.RESET_ALL}")
        else:
            self.logger.debug(f">> {method} {endpoint}{auth_indicator}")

        if data:
            self.logger.debug(f"  Request Data: {json.dumps(data, indent=2)}")

        # File logging - more structured
        file_logger = logging.getLogger("APITestSuite")
        # Only log to file if not in debug mode (to keep it clean)
        if not self.verbose:
            for handler in file_logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    file_logger.info(f"  [REQ] {method:6s} {full_url}")
                    break

    def _log_response(self, response: requests.Response, endpoint: str):
        """Log incoming response details."""
        status_color = Fore.GREEN if 200 <= response.status_code < 300 else Fore.RED
        status_str = f"{status_color}{response.status_code}{Style.RESET_ALL}" if COLORS_AVAILABLE else str(response.status_code)

        self.logger.debug(f"<< {status_str} from {endpoint}")
        try:
            response_data = response.json()
            if self.verbose and response_data:
                self.logger.debug(f"  Response: {json.dumps(response_data, indent=2)}")

            # File logging - structured response info
            if not self.verbose:
                for handler in logging.getLogger("APITestSuite").handlers:
                    if isinstance(handler, logging.FileHandler):
                        resp_code = response_data.get("code", "UNKNOWN") if response_data else "N/A"
                        logging.getLogger("APITestSuite").info(f"  [RES] {response.status_code} - {resp_code}")
                        break

            return response_data
        except:
            if self.verbose:
                self.logger.debug(f"  Response: {response.text}")
            return None

    def _make_request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Tuple[bool, Optional[requests.Response], Optional[Dict]]:
        """Make HTTP request and return success status, response object, and parsed JSON."""
        url = f"{self.internal_api_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._log_request(method, endpoint, data, headers)

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

            response_data = self._log_response(response, endpoint)
            success = 200 <= response.status_code < 300

            return success, response, response_data

        except requests.exceptions.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            self.logger.error(error_msg)
            self.test_results["errors"].append(error_msg)
            return False, None, None

    def _assert_success(self, success: bool, response: requests.Response, test_name: str, expected_status: int = None) -> bool:
        """Assert that a request was successful."""
        if not success or response is None:
            self.logger.error(f"✗ {test_name} FAILED - Request failed")
            self.test_results["failed"] += 1
            return False

        if expected_status and response.status_code != expected_status:
            self.logger.error(f"✗ {test_name} FAILED - Expected {expected_status}, got {response.status_code}")
            self.test_results["failed"] += 1
            # Also log to file
            logging.getLogger("APITestSuite").info(f"  [FAIL] {test_name}")
            return False

        self.logger.info(f"✓ {test_name} PASSED")
        self.test_results["passed"] += 1
        # Also log to file
        logging.getLogger("APITestSuite").info(f"  [PASS] {test_name}")
        return True

    def _assert_failure(self, success: bool, response: requests.Response, test_name: str, expected_status: int) -> bool:
        """Assert that a request failed as expected."""
        if not response:
            self.logger.error(f"✗ {test_name} FAILED - Request failed unexpectedly")
            self.test_results["failed"] += 1
            return False

        if response.status_code == expected_status:
            self.logger.info(f"✓ {test_name} PASSED (correctly got {expected_status})")
            self.test_results["passed"] += 1
            return True
        else:
            self.logger.error(f"✗ {test_name} FAILED - Expected {expected_status}, got {response.status_code}")
            self.test_results["failed"] += 1
            return False

    # ==================== AUTHENTICATION TESTS ====================

    def test_user_registration(self, username: str, email: str, password: str = "TestPass123!") -> bool:
        """Test user registration."""
        self._print_section(f"USER REGISTRATION TEST")

        data = {
            "username": username,
            "email": email,
            "password": password,
            "password2": password,  # Changed from password_confirm to password2
            "first_name": "Test",
            "last_name": "User",
        }

        success, response, resp_data = self._make_request("POST", "/auth/register/", data=data)

        if self._assert_success(success, response, f"Register user '{username}'", 201):
            self.test_users[username] = {"email": email, "password": password, "username": username}
            self.logger.info(f"  User email: {email}")
            return True

        return False

    def test_user_login(self, username: str, password: str) -> bool:
        """Test user login and token retrieval."""
        self._print_section(f"USER LOGIN TEST - {username}")

        data = {"username": username, "password": password}

        success, response, resp_data = self._make_request("POST", "/auth/login/", data=data)

        if self._assert_success(success, response, f"Login user '{username}'", 200):
            if resp_data and "access" in resp_data:
                self.user_tokens[username] = {
                    "access": resp_data["access"],
                    "refresh": resp_data.get("refresh"),
                    "user_type": resp_data.get("user_type", "customer"),
                }
                self.logger.info(f"  User type: {self.user_tokens[username].get('user_type')}")
                self.logger.info(f"  Access token obtained")
                return True

        return False

    def test_user_logout(self, username: str) -> bool:
        """Test user logout."""
        self._print_section(f"USER LOGOUT TEST - {username}")

        token = self.user_tokens.get(username, {}).get("refresh")
        if not token:
            self.logger.error(f"No refresh token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"refresh": token}

        success, response, resp_data = self._make_request("POST", "/auth/logout/", data=data)

        if self._assert_success(success, response, f"Logout user '{username}'", 200):
            self.logger.info(f"  User logged out successfully")
            return True

        return False

    def test_token_refresh(self, username: str) -> bool:
        """Test JWT token refresh."""
        self._print_section(f"TOKEN REFRESH TEST - {username}")

        token = self.user_tokens.get(username, {}).get("refresh")
        if not token:
            self.logger.error(f"No refresh token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"refresh": token}

        success, response, resp_data = self._make_request("POST", "/auth/token/refresh/", data=data)

        if self._assert_success(success, response, f"Refresh token for '{username}'", 200):
            if resp_data and "access" in resp_data:
                # Update stored tokens
                self.user_tokens[username]["access"] = resp_data["access"]
                self.user_tokens[username]["refresh"] = resp_data.get("refresh", token)
                self.logger.info(f"  New access token obtained")
                return True

        return False

    def test_get_user_info(self, username: str) -> bool:
        """Test getting current user information."""
        self._print_section(f"GET USER INFO TEST - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", "/auth/me/", token=token)

        if self._assert_success(success, response, f"Get user info for '{username}'", 200):
            if resp_data and "user" in resp_data:
                user_info = resp_data["user"]
                self.logger.info(f"  Username: {user_info.get('username')}")
                self.logger.info(f"  Email: {user_info.get('email')}")
                self.logger.info(f"  User type: {user_info.get('user_type')}")
                return True

        return False

    def test_update_user_profile(self, username: str) -> bool:
        """Test updating user profile."""
        self._print_section(f"UPDATE USER PROFILE TEST - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"first_name": "Updated", "last_name": "TestUser", "phone_number": "+1234567890"}

        success, response, resp_data = self._make_request("PUT", "/auth/profile/", token=token, data=data)

        if self._assert_success(success, response, f"Update profile for '{username}'", 200):
            self.logger.info(f"  Profile updated successfully")
            return True

        return False

    def test_change_password(self, username: str) -> bool:
        """Test changing user password."""
        self._print_section(f"CHANGE PASSWORD TEST - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"old_password": "TestPass123!", "new_password": "NewTestPass123!", "new_password2": "NewTestPass123!"}

        success, response, resp_data = self._make_request("POST", "/auth/change-password/", token=token, data=data)

        if self._assert_success(success, response, f"Change password for '{username}'", 200):
            self.logger.info(f"  Password changed successfully")
            # Update stored password for future tests
            if username in self.test_users:
                self.test_users[username]["password"] = "NewTestPass123!"
            return True

        return False

    def test_delete_account(self, username: str) -> bool:
        """Test account deletion (soft delete)."""
        self._print_section(f"DELETE ACCOUNT TEST - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"password": self.test_users.get(username, {}).get("password", "TestPass123!"), "confirm": True}

        success, response, resp_data = self._make_request("POST", "/auth/delete-account/", token=token, data=data)

        if self._assert_success(success, response, f"Delete account for '{username}'", 200):
            self.logger.info(f"  Account deleted successfully (soft delete)")
            return True

        return False

    # ==================== USER QUOTA TESTS ====================

    def test_get_user_quota(self, username: str) -> bool:
        """Test retrieving user's quota information."""
        self._print_section(f"GET USER QUOTA - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", "/quota/me/", token=token)

        if self._assert_success(success, response, f"Get quota for '{username}'", 200):
            if resp_data and "quota_info" in resp_data:
                quota = resp_data["quota_info"]
                self.logger.info(f"  Max API Keys: {quota.get('max_api_keys')}")
                self.logger.info(f"  Current API Keys: {quota.get('current_api_keys')}")
                self.logger.info(f"  Can Create More: {quota.get('can_create_more')}")
                self.logger.info(f"  Monthly Quota Remaining: {quota.get('quota_remaining')}")
                self.logger.info(f"  API key generation enabled: {quota.get('api_key_generation_enabled')}")
                return True

        return False

    # ==================== API KEY MANAGEMENT TESTS ====================

    def test_create_api_key(self, username: str, key_name: str) -> bool:
        """Test creating a new API key."""
        self._print_section(f"CREATE API KEY - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        data = {"name": key_name, "rate_limit_per_minute": 100, "rate_limit_per_hour": 1000, "rate_limit_per_day": 10000, "monthly_quota": 500}

        success, response, resp_data = self._make_request("POST", "/api-keys/create/", token=token, data=data)

        if self._assert_success(success, response, f"Create API key '{key_name}'", 201):
            if resp_data and "api_key" in resp_data:
                key_id = resp_data["api_key"].get("key_id")
                self.api_keys[key_name] = key_id
                self.logger.info(f"  Key ID: {key_id}")
                self.logger.info(f"  Name: {resp_data['api_key'].get('name')}")
                self.logger.info(f"  Status: {resp_data['api_key'].get('status')}")
                return True

        return False

    def test_list_api_keys(self, username: str) -> bool:
        """Test listing user's API keys."""
        self._print_section(f"LIST API KEYS - {username}")

        token = self.user_tokens.get(username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {username}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", "/api-keys/", token=token)

        if self._assert_success(success, response, f"List API keys for '{username}'", 200):
            if resp_data and "api_keys" in resp_data:
                keys = resp_data["api_keys"]
                self.logger.info(f"  Total API Keys: {len(keys)}")
                pagination = resp_data.get("pagination", {})
                self.logger.info(f"  Pagination: Page {pagination.get('page')}/{pagination.get('pages')}")
                for key in keys[:5]:
                    self.logger.info(f"    - {key.get('name')}: {key.get('status')}")
                return True

        return False

    def test_get_api_key_detail(self, username: str, key_name: str) -> bool:
        """Test getting detailed information about an API key."""
        self._print_section(f"GET API KEY DETAIL - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not token or not key_id:
            self.logger.error(f"Missing token or key_id")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", f"/api-keys/{key_id}/", token=token)

        if self._assert_success(success, response, f"Get details for API key '{key_name}'", 200):
            if resp_data and "api_key" in resp_data:
                key = resp_data["api_key"]
                self.logger.info(f"  Name: {key.get('name')}")
                self.logger.info(f"  Status: {key.get('status')}")
                self.logger.info(f"  Rate Limits: {key.get('rate_limit_per_minute')}/min, {key.get('rate_limit_per_hour')}/hr, {key.get('rate_limit_per_day')}/day")
                self.logger.info(f"  Monthly Quota: {key.get('monthly_quota')}")
                self.logger.info(f"  Created: {key.get('created_at')}")
                return True

        return False

    def test_update_api_key(self, username: str, key_name: str, new_status: str = "inactive") -> bool:
        """Test updating an API key."""
        self._print_section(f"UPDATE API KEY - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not token or not key_id:
            self.logger.error(f"Missing token or key_id")
            self.test_results["failed"] += 1
            return False

        data = {"status": new_status}

        success, response, resp_data = self._make_request("PUT", f"/api-keys/{key_id}/update/", token=token, data=data)

        if self._assert_success(success, response, f"Update API key '{key_name}'", 200):
            self.logger.info(f"  Status updated to: {new_status}")
            return True

        return False

    def test_regenerate_api_key(self, username: str, key_name: str) -> bool:
        """Test regenerating an API key."""
        self._print_section(f"REGENERATE API KEY - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not token or not key_id:
            self.logger.error(f"Missing token or key_id")
            self.test_results["failed"] += 1
            return False

        data = {"confirm": True}

        success, response, resp_data = self._make_request("POST", f"/api-keys/{key_id}/regenerate/", token=token, data=data)

        if self._assert_success(success, response, f"Regenerate API key '{key_name}'", 200):
            self.logger.info(f"  New API key generated (shown once)")
            return True

        return False

    def test_get_api_key_stats(self, username: str, key_name: str) -> bool:
        """Test getting API key usage statistics."""
        self._print_section(f"GET API KEY STATS - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not token or not key_id:
            self.logger.error(f"Missing token or key_id")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", f"/api-keys/{key_id}/stats/", token=token)

        if self._assert_success(success, response, f"Get stats for API key '{key_name}'", 200):
            if resp_data and "stats" in resp_data:
                stats = resp_data["stats"]
                self.logger.info(f"  Total Requests: {stats.get('total_requests', 0)}")
                self.logger.info(f"  Requests This Month: {stats.get('requests_this_month', 0)}")
                self.logger.info(f"  Requests Today: {stats.get('requests_today', 0)}")
                self.logger.info(f"  Quota Remaining: {stats.get('quota_remaining', 0)}")
                return True

        return False

    def test_delete_api_key(self, username: str, key_name: str) -> bool:
        """Test deleting an API key."""
        self._print_section(f"DELETE API KEY - {key_name}")

        token = self.user_tokens.get(username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not token or not key_id:
            self.logger.error(f"Missing token or key_id")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("DELETE", f"/api-keys/{key_id}/delete/", token=token)

        if self._assert_success(success, response, f"Delete API key '{key_name}'", 200):
            if key_name in self.api_keys:
                del self.api_keys[key_name]
            self.logger.info(f"  API key deleted successfully")
            return True

        return False

    # ==================== ADMIN TESTS ====================

    def test_list_all_users_quotas(self, admin_username: str) -> bool:
        """Test admin listing all users with quotas."""
        self._print_section(f"ADMIN: LIST ALL USERS QUOTAS")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        params = {"page": 1, "limit": 10}

        success, response, resp_data = self._make_request("GET", "/admin/users/quotas/", token=token, params=params)

        if self._assert_success(success, response, f"List all users quotas", 200):
            if resp_data and "users" in resp_data:
                users = resp_data["users"]
                self.logger.info(f"  Total Users Fetched: {len(users)}")
                for user in users[:3]:
                    self.logger.info(f"    - {user.get('username')}: {user.get('current_api_keys')}/{user.get('max_api_keys')} keys")
                return True

        return False

    def test_search_users(self, admin_username: str, search_query: str) -> bool:
        """Test admin searching for users."""
        self._print_section(f"ADMIN: SEARCH USERS")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        params = {"q": search_query, "page": 1, "limit": 10}

        success, response, resp_data = self._make_request("GET", "/admin/users/search/", token=token, params=params)

        if self._assert_success(success, response, f"Search users for '{search_query}'", 200):
            if resp_data and "users" in resp_data:
                users = resp_data["users"]
                self.logger.info(f"  Search Results: {len(users)} user(s) found")
                for user in users[:5]:
                    self.logger.info(f"    - {user.get('username')} ({user.get('email')})")
                return True

        return False

    def test_get_user_details(self, admin_username: str, target_username: str) -> bool:
        """Test admin getting comprehensive user details."""
        self._print_section(f"ADMIN: GET USER DETAILS - {target_username}")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", f"/admin/users/{target_username}/details/", token=token)

        if self._assert_success(success, response, f"Get details for user '{target_username}'", 200):
            if resp_data and "user_details" in resp_data:
                details = resp_data["user_details"]
                user_info = details.get("user_info", {})
                quota_info = details.get("quota_info", {})
                activity = details.get("activity_summary", {})

                self.logger.info(f"  User Info:")
                self.logger.info(f"    - Username: {user_info.get('username')}")
                self.logger.info(f"    - Email: {user_info.get('email')}")
                self.logger.info(f"    - Type: {user_info.get('user_type')}")

                self.logger.info(f"  Quota Info:")
                self.logger.info(f"    - Max API Keys: {quota_info.get('max_api_keys')}")
                self.logger.info(f"    - Monthly Quota: {quota_info.get('user_monthly_quota')}")

                self.logger.info(f"  Activity Summary:")
                self.logger.info(f"    - Total API Keys: {activity.get('total_api_keys')}")
                self.logger.info(f"    - Requests (Last 30 days): {activity.get('requests_last_30_days')}")

                return True

        return False

    def test_admin_get_user_quota(self, admin_username: str, target_username: str) -> bool:
        """Test admin getting specific user quota (different from get_user_details)."""
        self._print_section(f"ADMIN: GET USER QUOTA - {target_username}")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", f"/admin/users/{target_username}/quota/", token=token)

        if self._assert_success(success, response, f"Admin get quota for user '{target_username}'", 200):
            if resp_data and "quota_info" in resp_data:
                quota = resp_data["quota_info"]
                self.logger.info(f"  Max API Keys: {quota.get('max_api_keys')}")
                self.logger.info(f"  Current API Keys: {quota.get('current_api_keys')}")
                self.logger.info(f"  Monthly Quota: {quota.get('user_monthly_quota')}")
                self.logger.info(f"  Can Create More: {quota.get('can_create_more')}")
                return True

        return False

    def test_update_user_quota(self, admin_username: str, target_username: str) -> bool:
        """Test admin updating user quotas."""
        self._print_section(f"ADMIN: UPDATE USER QUOTA - {target_username}")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        data = {
            "max_api_keys": 15,
            "user_monthly_quota": 2000,
            "default_rate_limit_per_minute": 120,
            "default_rate_limit_per_hour": 1200,
            "default_rate_limit_per_day": 12000,
            "default_monthly_quota": 600,
        }

        success, response, resp_data = self._make_request("PUT", f"/admin/users/{target_username}/quota/update/", token=token, data=data)

        if self._assert_success(success, response, f"Update quota for user '{target_username}'", 200):
            self.logger.info(f"  Max API Keys: 15")
            self.logger.info(f"  Monthly Quota: 2000")
            self.logger.info(f"  Default Rate Limits: 120/min, 1200/hr, 12000/day")
            return True

        return False

    def test_list_all_api_keys(self, admin_username: str) -> bool:
        """Test admin listing all API keys across all users."""
        self._print_section(f"ADMIN: LIST ALL API KEYS")

        token = self.user_tokens.get(admin_username, {}).get("access")
        if not token:
            self.logger.error(f"No token found for admin {admin_username}")
            self.test_results["failed"] += 1
            return False

        params = {"page": 1, "limit": 10}

        success, response, resp_data = self._make_request("GET", "/admin/api-keys/", token=token, params=params)

        if self._assert_success(success, response, f"List all API keys", 200):
            if resp_data and "api_keys" in resp_data:
                keys = resp_data["api_keys"]
                self.logger.info(f"  Total API Keys: {len(keys)}")
                for key in keys[:3]:
                    self.logger.info(f"    - {key.get('name')} (User: {key.get('username')}): {key.get('status')}")
                return True

        return False

    def test_admin_update_api_key(self, admin_username: str, key_name: str) -> bool:
        """Test admin updating any user's API key."""
        self._print_section(f"ADMIN: UPDATE ANY API KEY - {key_name}")

        admin_token = self.user_tokens.get(admin_username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not admin_token or not key_id:
            self.logger.error(f"Missing admin token or key_id")
            self.test_results["failed"] += 1
            return False

        data = {"status": "active", "rate_limit_per_minute": 200}

        success, response, resp_data = self._make_request("PUT", f"/admin/api-keys/{key_id}/update/", token=admin_token, data=data)

        if self._assert_success(success, response, f"Admin update API key '{key_name}'", 200):
            self.logger.info(f"  Status: active")
            self.logger.info(f"  Rate limit: 200/min")
            return True

        return False

    def test_vton_virtual_tryon(self) -> bool:
        """Test virtual try-on processing (requires image files)."""
        self._print_section("VTON VIRTUAL TRY-ON TEST")

        # Note: This test requires actual image files to work properly
        # For now, we'll test the endpoint structure and error handling
        self.logger.info("  Note: This test requires person_image and clothing_image files")
        self.logger.info("  Skipping actual file upload test - would need test images")

        # Test with missing files to verify error handling
        success, response, resp_data = self._make_request("POST", "/virtual-tryon/process/", base_url=f"{self.base_url}/api/v1")

        # We expect this to fail due to missing files
        if response and response.status_code in [400, 415]:
            self.logger.info(f"  ✓ Endpoint responded correctly to missing files (status: {response.status_code})")
            self.test_results["passed"] += 1
            return True
        else:
            self.logger.error(f"  ✗ Unexpected response for missing files: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
            return False

    def test_vton_get_request_status(self) -> bool:
        """Test getting VTON request status."""
        self._print_section("VTON GET REQUEST STATUS TEST")

        # Use a dummy UUID to test the endpoint
        dummy_request_id = "12345678-1234-5678-9012-123456789012"

        success, response, resp_data = self._make_request("GET", f"/virtual-tryon/{dummy_request_id}/status/", base_url=f"{self.base_url}/api/v1")

        # We expect this to return 404 for non-existent request
        if response and response.status_code == 404:
            self.logger.info(f"  ✓ Endpoint correctly returned 404 for non-existent request")
            self.test_results["passed"] += 1
            return True
        else:
            self.logger.error(f"  ✗ Unexpected response: {response.status_code if response else 'No response'}")
            self.test_results["failed"] += 1
            return False

    def test_vton_list_requests(self) -> bool:
        """Test listing VTON requests."""
        self._print_section("VTON LIST REQUESTS TEST")

        success, response, resp_data = self._make_request("GET", "/virtual-tryon/requests/", base_url=f"{self.base_url}/api/v1")

        if self._assert_success(success, response, "List VTON requests", 200):
            if resp_data and "requests" in resp_data:
                requests_list = resp_data["requests"]
                self.logger.info(f"  Total Requests: {len(requests_list)}")
                self.logger.info(f"  Count: {resp_data.get('count', 'N/A')}")
                return True

        return False

    def test_admin_delete_api_key(self, admin_username: str, key_name: str) -> bool:
        """Test admin deleting any user's API key."""
        self._print_section(f"ADMIN: DELETE ANY API KEY - {key_name}")

        admin_token = self.user_tokens.get(admin_username, {}).get("access")
        key_id = self.api_keys.get(key_name)

        if not admin_token or not key_id:
            self.logger.error(f"Missing admin token or key_id")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("DELETE", f"/admin/api-keys/{key_id}/delete/", token=admin_token)

        if self._assert_success(success, response, f"Admin delete API key '{key_name}'", 200):
            if key_name in self.api_keys:
                del self.api_keys[key_name]
            self.logger.info(f"  API key deleted successfully")
            return True

        return False

    # ==================== PERMISSION TESTS ====================

    def test_non_admin_cannot_access_admin_endpoints(self, regular_user: str) -> bool:
        """Test that non-admin users cannot access admin endpoints."""
        self._print_section(f"PERMISSION TEST: Non-admin access denied")

        token = self.user_tokens.get(regular_user, {}).get("access")
        if not token:
            self.logger.error(f"No token found for user {regular_user}")
            self.test_results["failed"] += 1
            return False

        success, response, resp_data = self._make_request("GET", "/admin/users/quotas/", token=token)

        # We expect this to fail with 403 Forbidden
        if response is not None:
            if response.status_code == 403:
                self.logger.info(f"✓ Non-admin access denied to admin endpoint (403 Forbidden)")
                self.test_results["passed"] += 1
                return True
            else:
                self.logger.error(f"✗ Non-admin should not access admin endpoint (got {response.status_code})")
                self.test_results["failed"] += 1
                return False
        else:
            self.logger.error(f"✗ Request failed - no response object")
            self.test_results["failed"] += 1
            return False

    # ==================== TEST EXECUTION ====================

    def run_full_test_suite(self):
        """Run the complete test suite."""
        self.logger.info(f"{Fore.CYAN}{'='*70}")
        self.logger.info(f"{'STARTING FULL TEST SUITE':^70}")
        self.logger.info(f"{'='*70}{Style.RESET_ALL}\n")

        # Test users
        test_user = f"testuser_{int(time.time())}"
        test_user_email = f"{test_user}@test.local"

        # ==================== AUTHENTICATION TESTS ====================
        self._print_section("AUTHENTICATION TESTS")

        # User registration and login
        if not self.test_user_registration(test_user, test_user_email):
            self.logger.warning("User registration failed, cannot continue with user flow tests")
            self.logger.warning("Note: Check if server is running: python manage.py runserver")
        else:
            # User login
            if self.test_user_login(test_user, "TestPass123!"):
                # Get user info
                self.test_get_user_info(test_user)

                # Update profile
                self.test_update_user_profile(test_user)

                # Change password
                self.test_change_password(test_user)

                # Test token refresh
                self.test_token_refresh(test_user)

                # Get user quota
                self.test_get_user_quota(test_user)

                # Create multiple API keys
                self.logger.info("\n--- Creating multiple API keys ---\n")
                self.test_create_api_key(test_user, "production-key")
                time.sleep(0.5)  # Small delay to avoid conflicts
                self.test_create_api_key(test_user, "staging-key")

                # List API keys
                self.test_list_api_keys(test_user)

                # Get API key details
                if "production-key" in self.api_keys:
                    self.logger.info("\n--- Testing production-key operations ---\n")
                    self.test_get_api_key_detail(test_user, "production-key")

                    # Update API key
                    self.test_update_api_key(test_user, "production-key", "inactive")

                    # Get API key stats
                    self.test_get_api_key_stats(test_user, "production-key")

                    # Regenerate API key
                    self.test_regenerate_api_key(test_user, "production-key")

                # Cleanup
                self.logger.info("\n--- Cleanup: Deleting test API keys ---\n")
                if "production-key" in self.api_keys:
                    self.test_delete_api_key(test_user, "production-key")
                if "staging-key" in self.api_keys:
                    self.test_delete_api_key(test_user, "staging-key")

                # Test logout
                self.test_user_logout(test_user)

                # Test account deletion (commented out to avoid deleting test user)
                # self.test_delete_account(test_user)

        # ==================== PERMISSION TESTS ====================
        self._print_section("PERMISSION TESTS")

        if test_user in self.user_tokens:
            self.test_non_admin_cannot_access_admin_endpoints(test_user)

        # ==================== ADMIN FLOW ====================
        # Note: These tests require actual admin user (superuser)
        # You can create one with: python manage.py createsuperuser
        admin_user = "admin"  # Default Django admin
        admin_password = "admin"  # Change this to your actual admin password

        self._print_section("ADMIN FLOW - Testing admin endpoints")
        self.logger.info("NOTE: To properly test admin endpoints, create a superuser:")
        self.logger.info("  python manage.py createsuperuser")
        self.logger.info("  Then update the admin credentials in this script")
        self.logger.info("  Current test will skip admin tests if superuser not available\n")

        # Try to login as admin (this might fail if superuser doesn't exist)
        if self.test_user_login(admin_user, admin_password):
            admin_token = self.user_tokens.get(admin_user, {})
            if admin_token.get("user_type") in ["admin", "staff"]:
                self.test_list_all_users_quotas(admin_user)
                if test_user in self.test_users:
                    self.test_search_users(admin_user, test_user)
                    self.test_get_user_details(admin_user, test_user)
                    self.test_admin_get_user_quota(admin_user, test_user)
                    self.test_update_user_quota(admin_user, test_user)
                self.test_list_all_api_keys(admin_user)
            else:
                self.logger.warning(f"Logged in as {admin_user} but user is not admin (type: {admin_token.get('user_type')})")
        else:
            self.logger.info("Skipping admin tests - admin user login failed")

        # ==================== GENERAL ENDPOINTS TESTS ====================
        self._print_section("GENERAL ENDPOINTS TESTS")

        self.test_healthcheck()
        self.test_homepage()

        # ==================== VTON ENDPOINTS TESTS ====================
        self._print_section("VTON ENDPOINTS TESTS")

        self.test_vton_list_requests()
        self.test_vton_get_request_status()
        self.test_vton_virtual_tryon()

        # ==================== SUMMARY ====================
        self._print_section("TEST SUMMARY")
        self._print_summary()

    def _print_summary(self):
        """Print test execution summary."""
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        pass_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0

        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {Fore.GREEN}{self.test_results['passed']}{Style.RESET_ALL}")
        self.logger.info(f"Failed: {Fore.RED}{self.test_results['failed']}{Style.RESET_ALL}")
        self.logger.info(f"Pass Rate: {pass_rate:.1f}%\n")

        if self.test_results["errors"]:
            self.logger.warning(f"Errors encountered ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"][:5]:
                self.logger.warning(f"  - {error}")
            if len(self.test_results["errors"]) > 5:
                self.logger.warning(f"  ... and {len(self.test_results['errors']) - 5} more")

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Test execution completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_file = os.path.join(os.path.dirname(__file__), "..", "logs", "api_test_results.log")
        self.logger.info(f"Full results logged to: {log_file}")
        self.logger.info(f"{'='*70}\n")

        # Also log summary to file with better formatting
        file_logger = logging.getLogger("APITestSuite")
        file_logger.info("\n" + "=" * 60)
        file_logger.info("TEST SUMMARY")
        file_logger.info("=" * 60)
        file_logger.info(f"Total Tests: {total_tests}")
        file_logger.info(f"Passed:      {self.test_results['passed']}")
        file_logger.info(f"Failed:      {self.test_results['failed']}")
        file_logger.info(f"Pass Rate:   {pass_rate:.1f}%")
        file_logger.info(f"Completed:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_logger.info("=" * 60)


def main():
    """Main entry point for the test suite."""
    parser = argparse.ArgumentParser(
        description="API Endpoint Test Suite for API Key Management System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_endpoints.py
  python test_endpoints.py --base-url http://localhost:8000 --verbose
  python test_endpoints.py -v
        """,
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Verify API is reachable
    try:
        response = requests.get(f"{args.base_url}/internal/api/auth/me/", timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}Error: Cannot connect to API at {args.base_url}")
        print(f"Make sure the Django development server is running:{Style.RESET_ALL}")
        print(f"  cd VTON_APP")
        print(f"  python manage.py runserver\n")
        sys.exit(1)

    # Run test suite
    suite = APITestSuite(base_url=args.base_url, verbose=args.verbose)
    suite.run_full_test_suite()


if __name__ == "__main__":
    main()
