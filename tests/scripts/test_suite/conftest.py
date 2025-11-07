"""
Shared pytest configuration and fixtures for the test suite.
"""

import pytest
import requests
import json
import logging
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
        RED = GREEN = CYAN = YELLOW = WHITE = BLACK = BLUE = ""

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
    if hasattr(console_handler.stream, "reconfigure"):
        console_handler.stream.reconfigure(encoding="utf-8")

    formatter = ColoredFormatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler for logs
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.FileHandler(os.path.join(log_dir, "api_test_results.log"), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)-8s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def _log_request(logger, method: str, endpoint: str, data: Any = None, headers: Dict = None):
    """Log outgoing request details."""
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


def _log_response(logger, response: requests.Response, endpoint: str):
    """Log incoming response details."""
    status_color = Fore.GREEN if 200 <= response.status_code < 300 else Fore.RED
    status_str = f"{status_color}{response.status_code}{Style.RESET_ALL}" if COLORS_AVAILABLE else str(response.status_code)

    logger.debug(f"<< {status_str} from {endpoint}")
    try:
        response_data = response.json()
        if logger.isEnabledFor(logging.DEBUG) and response_data:
            logger.debug(f"  Response: {json.dumps(response_data, indent=2)}")
        return response_data
    except:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"  Response: {response.text}")
        return None


def make_request(
    internal_api_url: str,
    logger,
    method: str,
    endpoint: str,
    token: Optional[str] = None,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
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


@pytest.fixture(scope="session")
def base_url(request):
    """Fixture for base URL."""
    return request.config.getoption("--base-url", default="http://localhost:8000")


@pytest.fixture(scope="session")
def logger(request):
    """Fixture for logger."""
    # Use pytest's built-in verbose setting (-v flag)
    verbose = request.config.option.verbose > 0
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


# Note: pytest_configure and pytest_addoption hooks are handled by the __init__.py plugin
# to avoid duplicate option registration errors when pytest loads multiple conftest.py files
