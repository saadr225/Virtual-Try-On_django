"""API key management views for clients to manage their API keys."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q, Count
from app.models import APIKey, AuditLog, APIUsageLog, DailyUsageStats
from app.Controllers.ResponseCodesController import get_response_code
from api.internal_api.serializers.client_api_management_seiralizers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    APIKeyDetailSerializer,
    APIKeyUpdateSerializer,
    APIKeyRegenerateSerializer,
)
import logging

logger = logging.getLogger(__name__)


def create_response(code_key: str, data: dict = None, http_status: int = None):
    """
    Create standardized API response.

    Args:
        code_key (str): Response code key from ResponseCodesController
        data (dict): Additional data to include in response
        http_status (int): HTTP status code

    Returns:
        Response: DRF Response object
    """
    response_code = get_response_code(code_key)
    response_data = {
        "code": response_code["code"],
        "message": response_code["message"],
    }

    if data:
        response_data.update(data)

    # Determine HTTP status if not provided
    if http_status is None:
        code_prefix = response_code["code"][:3]
        if code_prefix == "SUC" or code_prefix == "API":
            http_status = status.HTTP_200_OK
        elif code_prefix == "AUT":
            http_status = status.HTTP_401_UNAUTHORIZED
        elif code_prefix in ["USR", "SYS"]:
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    return Response(response_data, status=http_status)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_api_key(request):
    """
    Create a new API key for the authenticated user.

    POST /internal/api/api-keys/create/

    Request Body:
        - name: string (required) - Unique name for the key
        - rate_limit_per_minute: integer (optional, default: 100)
        - rate_limit_per_hour: integer (optional, default: 1000)
        - rate_limit_per_day: integer (optional, default: 10000)
        - monthly_quota: integer (optional, default: 500)
        - allowed_domains: array (optional, empty = all allowed)
        - allowed_ips: array (optional, empty = all allowed)
        - expires_in_days: integer (optional, null = never expires)

    Response Codes:
        - API101: API key created successfully
        - API011: API key name is required
        - API012: API key name already exists
        - API006: Error creating API key
        - SYS004: Validation error
    """
    serializer = APIKeyCreateSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        errors = serializer.errors

        if "name" in errors:
            if "required" in str(errors["name"]).lower():
                return create_response("API_KEY_NAME_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)
            elif "exist" in str(errors["name"]).lower():
                return create_response("API_KEY_NAME_DUPLICATE", {"errors": errors}, status.HTTP_409_CONFLICT)

        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    try:
        api_key = serializer.save()

        # Log API key creation
        AuditLog.objects.create(
            user=request.user,
            action="create",
            resource_type="APIKey",
            resource_id=str(api_key.key_id),
            description=f"API key '{api_key.name}' created",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key created: {api_key.name} by {request.user.username}")

        # Return detailed serializer with full key (only shown once)
        detail_serializer = APIKeyDetailSerializer(api_key)

        return create_response("API_KEY_CREATED", {"api_key": detail_serializer.data}, status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}")
        return create_response("API_KEY_CREATE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def list_api_keys(request):
    """
    List all API keys for the authenticated user.

    GET /internal/api/api-keys/

    Query Parameters:
        - status: string (optional) - Filter by status: active, inactive, suspended
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 10, max: 100)

    Response Codes:
        - API104: API keys fetched successfully
        - SYS015: Invalid page number
        - SYS016: Invalid page size
    """
    try:
        user = request.user
        queryset = APIKey.objects.filter(user=user).order_by("-created_at")

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            if status_filter in ["active", "inactive", "suspended"]:
                queryset = queryset.filter(status=status_filter)

        # Pagination
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))

        if page < 1:
            return create_response("INVALID_PAGE", {"error": "Page must be >= 1"}, status.HTTP_400_BAD_REQUEST)
        if limit < 1 or limit > 100:
            return create_response("INVALID_PAGE_SIZE", {"error": "Limit must be between 1-100"}, status.HTTP_400_BAD_REQUEST)

        total_count = queryset.count()
        start = (page - 1) * limit
        end = start + limit

        api_keys = queryset[start:end]
        serializer = APIKeyListSerializer(api_keys, many=True)

        return create_response(
            "API_KEYS_FETCHED",
            {"api_keys": serializer.data, "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit}},
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing API keys: {str(e)}")
        return create_response("API_KEY_FETCH_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def get_api_key_detail(request, key_id):
    """
    Get detailed information about a specific API key.

    GET /internal/api/api-keys/{key_id}/

    Path Parameters:
        - key_id: UUID of the API key

    Response Codes:
        - API103: API key fetched successfully
        - API001: API key not found
    """
    try:
        api_key = APIKey.objects.get(user=request.user, key_id=key_id)
        serializer = APIKeyDetailSerializer(api_key)

        return create_response("API_KEY_FETCHED", {"api_key": serializer.data}, status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        logger.warning(f"API key not found: {key_id}")
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching API key: {str(e)}")
        return create_response("API_KEY_FETCH_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def update_api_key(request, key_id):
    """
    Update API key settings.

    PUT/PATCH /internal/api/api-keys/{key_id}/

    Request Body:
        - status: string (optional) - active, inactive, suspended
        - rate_limit_per_minute: integer (optional)
        - rate_limit_per_hour: integer (optional)
        - rate_limit_per_day: integer (optional)
        - monthly_quota: integer (optional)
        - allowed_domains: array (optional)
        - allowed_ips: array (optional)

    Response Codes:
        - API105: API key updated successfully
        - API001: API key not found
        - API008: Error updating API key
        - SYS004: Validation error
    """
    try:
        api_key = APIKey.objects.get(user=request.user, key_id=key_id)

        serializer = APIKeyUpdateSerializer(api_key, data=request.data, partial=True, context={"request": request})

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Log API key update
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="APIKey",
            resource_id=str(api_key.key_id),
            description=f"API key '{api_key.name}' updated",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key updated: {api_key.name} by {request.user.username}")

        detail_serializer = APIKeyDetailSerializer(api_key)

        return create_response("API_KEY_UPDATED", {"api_key": detail_serializer.data}, status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating API key: {str(e)}")
        return create_response("API_KEY_UPDATE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def delete_api_key(request, key_id):
    """
    Delete an API key (soft delete - marks as inactive).

    DELETE /internal/api/api-keys/{key_id}/

    Path Parameters:
        - key_id: UUID of the API key

    Response Codes:
        - API102: API key deleted successfully
        - API001: API key not found
        - API007: Error deleting API key
    """
    try:
        api_key = APIKey.objects.get(user=request.user, key_id=key_id)

        api_key_name = api_key.name
        api_key.delete()

        # Log API key deletion
        AuditLog.objects.create(
            user=request.user,
            action="delete",
            resource_type="APIKey",
            resource_id=str(key_id),
            description=f"API key '{api_key_name}' deleted",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key deleted: {api_key_name} by {request.user.username}")

        return create_response("API_KEY_DELETED", http_status=status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        return create_response("API_KEY_DELETE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def regenerate_api_key(request, key_id):
    """
    Regenerate/rotate an API key (invalidates old key).

    POST /internal/api/api-keys/{key_id}/regenerate/

    Request Body:
        - confirm: boolean (required, must be true)

    Response Codes:
        - API106: API key regenerated successfully
        - API001: API key not found
        - SYS004: Validation error (confirm not true)
    """
    try:
        serializer = APIKeyRegenerateSerializer(data=request.data)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        api_key = APIKey.objects.get(user=request.user, key_id=key_id)

        # Generate new API key
        old_key = api_key.api_key
        api_key.api_key = APIKeyCreateSerializer._generate_api_key()
        api_key.save(update_fields=["api_key"])

        # Log API key regeneration
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="APIKey",
            resource_id=str(api_key.key_id),
            description=f"API key '{api_key.name}' regenerated",
            old_values={"api_key": old_key[:10] + "..."},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key regenerated: {api_key.name} by {request.user.username}")

        # Return new key (only shown this time)
        detail_serializer = APIKeyDetailSerializer(api_key)

        return create_response("API_KEY_REGENERATED", {"api_key": detail_serializer.data}, status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error regenerating API key: {str(e)}")
        return create_response("API_KEY_UPDATE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def get_api_key_stats(request, key_id):
    """
    Get usage statistics for an API key.

    GET /internal/api/api-keys/{key_id}/stats/

    Path Parameters:
        - key_id: UUID of the API key

    Response:
        - total_requests: Total requests made with this key
        - requests_this_month: Requests in current month
        - requests_this_day: Requests in current day
        - quota_remaining: Monthly quota remaining
        - last_used_at: Last time key was used
        - status: Current key status

    Response Codes:
        - API112: Usage statistics fetched successfully
        - API001: API key not found
    """
    try:
        from app.Controllers.ClientSideApiController import ClientSideApiController

        api_key = APIKey.objects.get(user=request.user, key_id=key_id)

        # Get statistics using controller
        stats = ClientSideApiController.get_usage_statistics(api_key)

        # Add key identification
        stats["key_id"] = str(api_key.key_id)
        stats["name"] = api_key.name
        stats["rate_limits"] = {
            "per_minute": api_key.rate_limit_per_minute,
            "per_hour": api_key.rate_limit_per_hour,
            "per_day": api_key.rate_limit_per_day,
            "per_month": api_key.monthly_quota,
        }

        return create_response("USAGE_STATS_FETCHED", {"stats": stats}, status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching API key stats: {str(e)}")
        return create_response("USAGE_STATS_FETCH_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
