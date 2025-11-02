import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware for logging HTTP requests and responses.

    Always logs: "{METHOD} {PATH} HTTP/{VERSION}" {STATUS_CODE} {RESPONSE_SIZE}

    Additional verbosity controlled by DEBUG_FLAGS in settings:
    - LOG_REQUESTS: Include detailed request information
    - LOG_RESPONSES: Include detailed response information
    - LOG_REQUEST_HEADERS: Include headers in request logs
    - LOG_REQUEST_BODY: Include body in request logs
    - LOG_QUERY_PARAMS: Include query parameters in logs
    - LOG_PERFORMANCE_METRICS: Include response time
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Cache debug flags for performance
        self.debug_flags = getattr(settings, "DEBUG_FLAGS", {})
        self.log_requests = self.debug_flags.get("LOG_REQUESTS", False)
        self.log_responses = self.debug_flags.get("LOG_RESPONSES", False)
        self.log_headers = self.debug_flags.get("LOG_REQUEST_HEADERS", False)
        self.log_body = self.debug_flags.get("LOG_REQUEST_BODY", False)
        self.log_query_params = self.debug_flags.get("LOG_QUERY_PARAMS", False)
        self.log_performance = self.debug_flags.get("LOG_PERFORMANCE_METRICS", False)

    def __call__(self, request):
        start_time = time.time() if self.log_performance else None

        # Log verbose request details if enabled
        if self.log_requests:
            self._log_request_details(request)

        # Process request
        response = self.get_response(request)

        # Calculate duration if performance logging enabled
        duration_ms = None
        if start_time:
            duration_ms = (time.time() - start_time) * 1000

        # Always log the basic request summary (like Django's server log)
        self._log_request_summary(request, response, duration_ms)

        # Log verbose response details if enabled
        if self.log_responses:
            self._log_response_details(request, response)

        return response

    def _log_request_summary(self, request, response, duration_ms=None):
        """
        Log basic request info in Django server format.
        Example: "GET /api/vton/status/123 HTTP/1.1" 200 1234
        """
        # Get HTTP version
        http_version = request.META.get("SERVER_PROTOCOL", "HTTP/1.1").split("/")[1]

        # Get response size
        response_size = len(response.content) if hasattr(response, "content") else 0

        # Build log message
        parts = [f'"{request.method} {request.path} HTTP/{http_version}"', str(response.status_code), str(response_size)]

        # Add duration if available
        if duration_ms is not None:
            parts.append(f"({duration_ms:.0f}ms)")

        message = " ".join(parts)

        # Choose log level based on status code
        if response.status_code >= 500:
            logger.error(message)
        elif response.status_code >= 400:
            logger.warning(message)
        else:
            logger.info(message)

    def _log_request_details(self, request):
        """Log detailed incoming request information."""
        request_info = {
            "method": request.method,
            "path": request.path,
            "ip": request.META.get("REMOTE_ADDR"),
        }

        # Add headers if enabled
        if self.log_headers:
            headers = {k.replace("HTTP_", ""): v for k, v in request.META.items() if k.startswith("HTTP_") and k not in ["HTTP_COOKIE", "HTTP_AUTHORIZATION"]}
            if headers:
                request_info["headers"] = headers

        # Add query params if enabled
        if self.log_query_params and request.GET:
            request_info["query"] = dict(request.GET)

        # Add body if enabled and not too large
        if self.log_body and "multipart/form-data" not in request.META.get("CONTENT_TYPE", ""):
            try:
                body_length = len(request.body) if request.body else 0
                if 0 < body_length < 1000:  # Only log small bodies
                    try:
                        request_info["body"] = request.body.decode("utf-8")
                    except:
                        request_info["body"] = f"<binary: {body_length}B>"
            except:
                pass

        # Add file info if present
        if request.FILES:
            request_info["files"] = {name: f"{file.size}B ({file.content_type})" for name, file in request.FILES.items()}

        logger.debug(f"→ Request Details: {request_info}")

    def _log_response_details(self, request, response):
        """Log detailed outgoing response information."""
        response_info = {
            "status": response.status_code,
            "content_type": response.get("Content-Type", "unknown"),
        }

        # Add response size if available
        if hasattr(response, "content"):
            response_info["size"] = f"{len(response.content)}B"

        logger.debug(f"← Response Details: {response_info}")
