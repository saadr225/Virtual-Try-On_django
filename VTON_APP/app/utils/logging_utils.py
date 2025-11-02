"""
Logging utilities for consistent logging across the application.

This module provides helper functions for cleaner, more structured logging
that respects DEBUG_FLAGS settings.
"""

import logging
from django.conf import settings
from typing import Optional, Dict, Any


def get_debug_flag(flag_name: str, default: bool = False) -> bool:
    """
    Get a debug flag value from settings.

    Args:
        flag_name: Name of the debug flag
        default: Default value if flag not found

    Returns:
        Boolean value of the flag
    """
    debug_flags = getattr(settings, "DEBUG_FLAGS", {})
    return debug_flags.get(flag_name, default)


def log_request_summary(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    extra_info: Optional[Dict[str, Any]] = None,
):
    """
    Log a clean request summary.

    Args:
        logger: Logger instance to use
        method: HTTP method
        path: Request path
        status_code: Response status code (optional)
        duration_ms: Request duration in milliseconds (optional)
        extra_info: Additional information to log (optional)
    """
    parts = [method, path]

    if status_code is not None:
        parts.append(f"→ {status_code}")

    if duration_ms is not None:
        parts.append(f"({duration_ms:.0f}ms)")

    message = " ".join(parts)

    if extra_info:
        message += f" {extra_info}"

    # Choose log level based on status code
    if status_code:
        if status_code >= 500:
            logger.error(message)
        elif status_code >= 400:
            logger.warning(message)
        else:
            logger.info(message)
    else:
        logger.info(message)


def log_api_operation(logger: logging.Logger, operation: str, success: bool = True, **kwargs):
    """
    Log an API operation with consistent formatting.

    Args:
        logger: Logger instance to use
        operation: Description of the operation
        success: Whether the operation was successful
        **kwargs: Additional key-value pairs to log
    """
    status = "✓" if success else "✗"
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    message = f"{status} {operation}"
    if extra:
        message += f" | {extra}"

    if success:
        logger.info(message)
    else:
        logger.warning(message)


def log_error_with_context(logger: logging.Logger, error_msg: str, exc_info: bool = False, **context):
    """
    Log an error with additional context.

    Args:
        logger: Logger instance to use
        error_msg: Error message
        exc_info: Whether to include exception traceback
        **context: Additional context key-value pairs
    """
    context_str = " | ".join(f"{k}={v}" for k, v in context.items()) if context else ""
    message = error_msg
    if context_str:
        message += f" | {context_str}"

    logger.error(message, exc_info=exc_info)


def should_log_verbose(component: str) -> bool:
    """
    Check if verbose logging is enabled for a component.

    Args:
        component: Component name (e.g., 'requests', 'database', 'api_key')

    Returns:
        True if verbose logging is enabled
    """
    flag_mapping = {
        "requests": "LOG_REQUESTS",
        "responses": "LOG_RESPONSES",
        "headers": "LOG_REQUEST_HEADERS",
        "body": "LOG_REQUEST_BODY",
        "query": "LOG_QUERY_PARAMS",
        "database": "LOG_DATABASE_QUERIES",
        "api_key": "LOG_API_KEY_VALIDATION",
        "vton": "LOG_VTON_PROCESSING",
        "performance": "LOG_PERFORMANCE_METRICS",
    }

    flag_name = flag_mapping.get(component)
    if flag_name:
        return get_debug_flag(flag_name, False)

    return False


class PerformanceLogger:
    """
    Context manager for logging operation performance.

    Usage:
        with PerformanceLogger(logger, "Database query"):
            # perform operation
            pass
    """

    def __init__(self, logger: logging.Logger, operation: str, log_if_slower_than_ms: Optional[float] = None):
        """
        Initialize performance logger.

        Args:
            logger: Logger instance to use
            operation: Description of the operation
            log_if_slower_than_ms: Only log if operation takes longer than this (ms)
        """
        self.logger = logger
        self.operation = operation
        self.threshold_ms = log_if_slower_than_ms
        self.start_time = None
        self.enabled = get_debug_flag("LOG_PERFORMANCE_METRICS", False)

    def __enter__(self):
        if self.enabled:
            import time

            self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.enabled and self.start_time:
            import time

            duration_ms = (time.time() - self.start_time) * 1000

            # Only log if no threshold or duration exceeds threshold
            if self.threshold_ms is None or duration_ms > self.threshold_ms:
                if exc_type:
                    self.logger.warning(f"⏱ {self.operation} failed after {duration_ms:.0f}ms")
                else:
                    self.logger.info(f"⏱ {self.operation} completed in {duration_ms:.0f}ms")
