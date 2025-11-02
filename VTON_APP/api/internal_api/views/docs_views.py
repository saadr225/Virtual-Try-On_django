"""
API Documentation views for serving OpenAPI specification files.
Provides endpoints to serve both public (client) and internal API specifications.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse, Http404
from django.conf import settings
from api.internal_api.utils.permissions import admin_required, IsAdminUser
from app.Controllers.ResponseCodesController import get_response_code
import os
import yaml
import logging

logger = logging.getLogger(__name__)

# Define the base path to the OpenAPI spec files
# settings.BASE_DIR points to VTON_APP directory, we need to go up one level to project root
PROJECT_ROOT = os.path.dirname(settings.BASE_DIR)
SPEC_DIR = os.path.join(PROJECT_ROOT, "docs", "api", "openapi")
CLIENT_SPEC_PATH = os.path.join(SPEC_DIR, "client_api.yaml")
INTERNAL_SPEC_PATH = os.path.join(SPEC_DIR, "internal_api.yaml")


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def client_api_spec(request):
    """
    Serve the Client API OpenAPI specification file.

    This endpoint is public and accessible without authentication.
    Returns the OpenAPI spec for the external-facing VTON client API.

    Query Parameters:
        format (optional): 'json' or 'yaml' (default: yaml)

    Returns:
        Response: OpenAPI specification in requested format
    """
    try:
        # Check if the spec file exists
        if not os.path.exists(CLIENT_SPEC_PATH):
            logger.error(f"Client API spec file not found at: {CLIENT_SPEC_PATH}")
            response_code = get_response_code("RESOURCE_NOT_FOUND")
            return Response(
                {"code": response_code["code"], "message": response_code["message"], "detail": "Client API specification file not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get format preference from query params
        format_type = request.GET.get("format", "yaml").lower()

        # Read the YAML file
        with open(CLIENT_SPEC_PATH, "r", encoding="utf-8") as f:
            spec_content = yaml.safe_load(f)

        # Return in requested format
        if format_type == "json":
            return Response(spec_content, status=status.HTTP_200_OK)
        else:
            # Return YAML as plain text
            with open(CLIENT_SPEC_PATH, "r", encoding="utf-8") as f:
                yaml_content = f.read()
            return Response(yaml_content, status=status.HTTP_200_OK, content_type="application/x-yaml")

    except yaml.YAMLError as e:
        logger.error(f"Error parsing Client API spec YAML: {str(e)}")
        response_code = get_response_code("INTERNAL_SERVER_ERROR")
        return Response(
            {"code": response_code["code"], "message": response_code["message"], "detail": "Error parsing specification file"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    except Exception as e:
        logger.error(f"Unexpected error serving Client API spec: {str(e)}")
        response_code = get_response_code("INTERNAL_SERVER_ERROR")
        return Response(
            {"code": response_code["code"], "message": response_code["message"], "detail": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
@admin_required
def internal_api_spec(request):
    """
    Serve the Internal API OpenAPI specification file.

    This endpoint is protected and only accessible to admin users.
    Returns the OpenAPI spec for the internal API (authentication, user management, admin operations).

    Query Parameters:
        format (optional): 'json' or 'yaml' (default: yaml)

    Returns:
        Response: OpenAPI specification in requested format

    Permissions:
        - Requires authentication (JWT token)
        - Requires admin privileges
    """
    try:
        # Check if the spec file exists
        if not os.path.exists(INTERNAL_SPEC_PATH):
            logger.error(f"Internal API spec file not found at: {INTERNAL_SPEC_PATH}")
            response_code = get_response_code("RESOURCE_NOT_FOUND")
            return Response(
                {"code": response_code["code"], "message": response_code["message"], "detail": "Internal API specification file not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get format preference from query params
        format_type = request.GET.get("format", "yaml").lower()

        # Read the YAML file
        with open(INTERNAL_SPEC_PATH, "r", encoding="utf-8") as f:
            spec_content = yaml.safe_load(f)

        # Return in requested format
        if format_type == "json":
            return Response(spec_content, status=status.HTTP_200_OK)
        else:
            # Return YAML as plain text
            with open(INTERNAL_SPEC_PATH, "r", encoding="utf-8") as f:
                yaml_content = f.read()
            return Response(yaml_content, status=status.HTTP_200_OK, content_type="application/x-yaml")

    except yaml.YAMLError as e:
        logger.error(f"Error parsing Internal API spec YAML: {str(e)}")
        response_code = get_response_code("INTERNAL_SERVER_ERROR")
        return Response(
            {"code": response_code["code"], "message": response_code["message"], "detail": "Error parsing specification file"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    except Exception as e:
        logger.error(f"Unexpected error serving Internal API spec: {str(e)}")
        response_code = get_response_code("INTERNAL_SERVER_ERROR")
        return Response(
            {"code": response_code["code"], "message": response_code["message"], "detail": "An unexpected error occurred"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
def api_docs_info(request):
    """
    Get information about available API documentation endpoints.

    Returns a list of available API spec endpoints and their access requirements.
    This is a public endpoint to help users discover the documentation.

    Returns:
        Response: Information about available documentation endpoints
    """
    docs_info = {
        "code": "SUCCESS",
        "message": "API documentation endpoints",
        "endpoints": [
            {
                "name": "Client API Specification",
                "path": "/api/internal/docs/client-api-spec/",
                "description": "OpenAPI specification for the external-facing VTON Client API",
                "access": "public",
                "formats": ["yaml", "json"],
                "usage": "Add ?format=json or ?format=yaml query parameter",
            },
            {
                "name": "Internal API Specification",
                "path": "/api/internal/docs/internal-api-spec/",
                "description": "OpenAPI specification for the Internal API (authentication, admin, user management)",
                "access": "admin only",
                "authentication": "JWT Bearer token required",
                "formats": ["yaml", "json"],
                "usage": "Add ?format=json or ?format=yaml query parameter",
            },
        ],
    }

    return Response(docs_info, status=status.HTTP_200_OK)
