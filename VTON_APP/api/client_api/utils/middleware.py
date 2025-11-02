"""Lightweight API Key Authentication Middleware for Client API."""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework.response import Response
from rest_framework import status
from app.Controllers.ClientSideApiController import ClientSideApiController
from app.Controllers.ResponseCodesController import get_response_code
import logging

logger = logging.getLogger(__name__)


class APIKeyValidationMiddleware(MiddlewareMixin):
    """
    Lightweight middleware to validate API keys for Client API endpoints.

    Delegates all business logic to ClientSideApiController.
    """

    # Endpoints that don't require API key validation
    EXEMPT_PATHS = [
        "/internal/api/",
        "/health/",
        "/admin/",
        "/static/",
        "/media/",
    ]

    def process_request(self, request):
        """
        Process incoming request to validate API key.

        This middleware:
        1. Checks if endpoint requires API key
        2. Extracts API key from X-API-Key header
        3. Delegates validation to ClientSideApiController
        4. Attaches validated API key to request object
        """
        # Check if endpoint is exempt
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None

        # Only validate Client API endpoints
        if not request.path.startswith("/api/v1/"):
            return None

        # Get API key from header
        api_key_str = request.META.get("HTTP_X_API_KEY")

        # If no API key, allow public access (views can enforce API key if needed)
        if not api_key_str:
            request.api_key = None
            request.api_key_valid = False
            return None

        # Validate request using controller
        is_valid, result, http_status = ClientSideApiController.validate_request(api_key_str, request)

        if not is_valid:
            # Return error response
            return JsonResponse(
                {
                    "code": result["code"],
                    "message": result["message"],
                },
                status=http_status,
            )

        # Attach validated API key to request
        request.api_key = result
        request.api_key_valid = True

        # Update last used timestamp
        ClientSideApiController.update_last_used(result)

        return None

    def process_response(self, request, response):
        """
        Process response to log API usage.

        Delegates logging to ClientSideApiController.
        """
        # Only log for Client API endpoints
        if not request.path.startswith("/api/v1/"):
            return response

        # Log usage if API key was used
        if hasattr(request, "api_key") and request.api_key:
            ClientSideApiController.log_api_usage(request.api_key, request, response)

        return response


def validate_api_key(view_func):
    """
    Decorator to validate API key for specific views.

    Usage:
        @validate_api_key
        @api_view(['POST'])
        def my_view(request):
            ...
    """

    def wrapper(request, *args, **kwargs):
        # Check if API key is valid
        if not getattr(request, "api_key_valid", False):
            response_code = get_response_code("API_KEY_MISSING")
            return Response(
                {
                    "code": response_code["code"],
                    "message": response_code["message"],
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return view_func(request, *args, **kwargs)

    return wrapper


class APIKeyRequiredPermission:
    """
    Custom permission class for DRF views.

    Usage:
        class MyView(APIView):
            permission_classes = [APIKeyRequiredPermission]
    """

    def has_permission(self, request, view):
        """Check if request has valid API key."""
        return getattr(request, "api_key_valid", False)


def get_api_key_from_request(request):
    """
    Utility function to get API key object from request.

    Returns:
        APIKey object or None
    """
    return getattr(request, "api_key", None)
