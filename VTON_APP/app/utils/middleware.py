import logging
from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Collect all request details in a single log entry
        if settings.DEBUG:
            # Build comprehensive request info
            request_info = {
                "method": request.method,
                "path": request.path,
                "remote_addr": request.META.get("REMOTE_ADDR"),
                "origin": request.META.get("HTTP_ORIGIN", "None"),
                "content_type": request.META.get("CONTENT_TYPE", ""),
                "content_length": request.META.get("CONTENT_LENGTH", "0"),
            }

            # Add headers (only HTTP_* ones for brevity)
            headers = {k.replace("HTTP_", ""): v for k, v in request.META.items() if k.startswith("HTTP_")}
            if headers:
                request_info["headers"] = headers

            # Add query params if present
            if request.GET:
                request_info["query_params"] = dict(request.GET)

            # Add POST data if present (not files)
            if request.POST:
                request_info["post_data"] = dict(request.POST)

            # Add file info if present
            if request.FILES:
                request_info["files"] = {name: f"{file.size}B ({file.content_type})" for name, file in request.FILES.items()}

            # Add body content for small non-multipart requests
            if "multipart/form-data" not in request_info["content_type"]:
                try:
                    body_length = len(request.body) if request.body else 0
                    if body_length > 0 and body_length < 1000:
                        try:
                            request_info["body"] = request.body.decode("utf-8")
                        except:
                            request_info["body"] = f"<binary data: {body_length}B>"
                except:
                    pass

            # Log everything in one line (formatted for readability)
            logger.info(f"Request: {request_info}")
        else:
            # Production: minimal logging
            logger.info(f"Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')} | Origin: {request.META.get('HTTP_ORIGIN', 'None')}")

        # Handle OPTIONS requests
        if request.method == "OPTIONS":
            logger.info(
                f"CORS Preflight: {request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')} | Headers: {request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')}"
            )

        response = self.get_response(request)

        # Log response in same format
        logger.info(f"Response: {response.status_code} for {request.method} {request.path}")

        return response
