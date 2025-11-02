"""
Admin views for managing users and their API key quotas.
Only accessible by admin users.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Q
from app.models import UserData, APIKey, AuditLog
from app.Controllers.ResponseCodesController import get_response_code
from api.internal_api.utils.permissions import admin_required, is_admin_user
from api.internal_api.serializers.admin_serializers import (
    UserQuotaSerializer,
    UserQuotaUpdateSerializer,
    AdminAPIKeyListSerializer,
    AdminAPIKeyUpdateSerializer,
)
import logging

logger = logging.getLogger(__name__)


def create_response(code_key: str, data: dict = None, http_status: int = None):
    """Create standardized API response."""
    response_code = get_response_code(code_key)
    response_data = {
        "code": response_code["code"],
        "message": response_code["message"],
    }

    if data:
        response_data.update(data)

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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def list_all_users_quotas(request):
    """
    List all users and their API key quotas (Admin only).

    GET /internal/api/admin/users/quotas/

    Query Parameters:
        - user_type: string (optional) - Filter by user type
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 20)

    Response Codes:
        - API113: List fetched successfully
        - AUT004: Access denied (not admin)
    """
    try:
        queryset = UserData.objects.select_related("user").all().order_by("-created_at")

        # Filter by user type if provided
        user_type_filter = request.query_params.get("user_type")
        if user_type_filter:
            queryset = queryset.filter(user_type=user_type_filter)

        # Pagination
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))

        if page < 1:
            return create_response("INVALID_PAGE", {"error": "Page must be >= 1"}, status.HTTP_400_BAD_REQUEST)
        if limit < 1 or limit > 100:
            return create_response("INVALID_PAGE_SIZE", {"error": "Limit must be between 1-100"}, status.HTTP_400_BAD_REQUEST)

        total_count = queryset.count()
        start = (page - 1) * limit
        end = start + limit

        users = queryset[start:end]
        serializer = UserQuotaSerializer(users, many=True)

        return create_response(
            "LIST_FETCHED",
            {"users": serializer.data, "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit}},
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing user quotas: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def get_user_quota(request, username):
    """
    Get specific user's API key quota settings (Admin only).

    GET /internal/api/admin/users/<username>/quota/

    Response Codes:
        - SUC002: Data retrieved successfully
        - USR001: User not found
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        serializer = UserQuotaSerializer(user_data)

        return create_response("DATA_RETRIEVED", {"user_quota": serializer.data}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching user quota: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def update_user_quota(request, username):
    """
    Update user's API key quota settings (Admin only).

    PUT/PATCH /internal/api/admin/users/<username>/quota/

    Request Body:
        - max_api_keys: integer (optional)
        - api_key_generation_enabled: boolean (optional)
        - user_monthly_quota: integer (optional)
        - default_rate_limit_per_minute: integer (optional)
        - default_rate_limit_per_hour: integer (optional)
        - default_rate_limit_per_day: integer (optional)
        - default_monthly_quota: integer (optional)

    Response Codes:
        - SUC004: Resource updated successfully
        - USR001: User not found
        - SYS004: Validation error
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        serializer = UserQuotaUpdateSerializer(user_data, data=request.data, partial=True)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Log the update
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="UserQuota",
            resource_id=str(user.id),
            description=f"Updated quota settings for user {username}",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} updated quota for user {username}")

        # Return updated data
        result_serializer = UserQuotaSerializer(user_data)

        return create_response("RESOURCE_UPDATED", {"user_quota": result_serializer.data}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating user quota: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def list_all_api_keys(request):
    """
    List all API keys across all users (Admin only).

    GET /internal/api/admin/api-keys/

    Query Parameters:
        - username: string (optional) - Filter by username
        - status: string (optional) - Filter by status
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 20)

    Response Codes:
        - API104: API keys fetched successfully
        - AUT004: Access denied (not admin)
    """
    try:
        queryset = APIKey.objects.select_related("user").all().order_by("-created_at")

        # Filter by username if provided
        username_filter = request.query_params.get("username")
        if username_filter:
            queryset = queryset.filter(user__username=username_filter)

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter and status_filter in ["active", "inactive", "suspended"]:
            queryset = queryset.filter(status=status_filter)

        # Pagination
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))

        if page < 1:
            return create_response("INVALID_PAGE", {"error": "Page must be >= 1"}, status.HTTP_400_BAD_REQUEST)
        if limit < 1 or limit > 100:
            return create_response("INVALID_PAGE_SIZE", {"error": "Limit must be between 1-100"}, status.HTTP_400_BAD_REQUEST)

        total_count = queryset.count()
        start = (page - 1) * limit
        end = start + limit

        api_keys = queryset[start:end]
        serializer = AdminAPIKeyListSerializer(api_keys, many=True)

        return create_response(
            "API_KEYS_FETCHED",
            {"api_keys": serializer.data, "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit}},
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing all API keys: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def admin_update_api_key(request, key_id):
    """
    Update any API key with full control (Admin only).

    PUT/PATCH /internal/api/admin/api-keys/<key_id>/

    Request Body:
        - name: string (optional)
        - status: string (optional)
        - rate_limit_per_minute: integer (optional)
        - rate_limit_per_hour: integer (optional)
        - rate_limit_per_day: integer (optional)
        - monthly_quota: integer (optional)
        - allowed_domains: array (optional)
        - allowed_ips: array (optional)

    Response Codes:
        - API105: API key updated successfully
        - API001: API key not found
        - SYS004: Validation error
        - AUT004: Access denied (not admin)
    """
    try:
        api_key = APIKey.objects.select_related("user").get(key_id=key_id)

        serializer = AdminAPIKeyUpdateSerializer(api_key, data=request.data, partial=True)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Log the update
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="APIKey",
            resource_id=str(api_key.key_id),
            description=f"Admin updated API key '{api_key.name}' for user {api_key.user.username}",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} updated API key {api_key.key_id}")

        # Return updated data
        result_serializer = AdminAPIKeyListSerializer(api_key)

        return create_response("API_KEY_UPDATED", {"api_key": result_serializer.data}, status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating API key: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def admin_delete_api_key(request, key_id):
    """
    Delete any API key (Admin only).

    DELETE /internal/api/admin/api-keys/<key_id>/

    Response Codes:
        - API102: API key deleted successfully
        - API001: API key not found
        - AUT004: Access denied (not admin)
    """
    try:
        api_key = APIKey.objects.select_related("user").get(key_id=key_id)

        api_key_name = api_key.name
        api_key_user = api_key.user.username
        api_key.delete()

        # Log the deletion
        AuditLog.objects.create(
            user=request.user,
            action="delete",
            resource_type="APIKey",
            resource_id=str(key_id),
            description=f"Admin deleted API key '{api_key_name}' for user {api_key_user}",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} deleted API key {key_id}")

        return create_response("API_KEY_DELETED", http_status=status.HTTP_200_OK)

    except APIKey.DoesNotExist:
        return create_response("API_KEY_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting API key: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def search_users(request):
    """
    Search for users by username or email (Admin only).

    GET /internal/api/admin/users/search/

    Query Parameters:
        - q: string (required) - Search query (searches username and email)
        - user_type: string (optional) - Filter by user type
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 20)

    Response Codes:
        - LIST_FETCHED: Search results fetched successfully
        - VALIDATION_ERROR: Search query is required
        - AUT004: Access denied (not admin)
    """
    try:
        search_query = request.query_params.get("q", "").strip()

        if not search_query:
            return create_response("VALIDATION_ERROR", {"error": "Search query parameter 'q' is required"}, status.HTTP_400_BAD_REQUEST)

        # Search in username and email (case-insensitive)
        queryset = (
            UserData.objects.select_related("user")
            .filter(
                Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
            )
            .order_by("-created_at")
        )

        # Filter by user type if provided
        user_type_filter = request.query_params.get("user_type")
        if user_type_filter:
            queryset = queryset.filter(user_type=user_type_filter)

        # Pagination
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 20))

        if page < 1:
            return create_response("INVALID_PAGE", {"error": "Page must be >= 1"}, status.HTTP_400_BAD_REQUEST)
        if limit < 1 or limit > 100:
            return create_response("INVALID_PAGE_SIZE", {"error": "Limit must be between 1-100"}, status.HTTP_400_BAD_REQUEST)

        total_count = queryset.count()
        start = (page - 1) * limit
        end = start + limit

        users = queryset[start:end]
        serializer = UserQuotaSerializer(users, many=True)

        return create_response(
            "LIST_FETCHED",
            {
                "search_query": search_query,
                "users": serializer.data,
                "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit},
            },
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error searching users: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def get_user_details(request, username):
    """
    Get comprehensive details about a specific user including all their API keys (Admin only).

    GET /internal/api/admin/users/<username>/details/

    Response:
        - user_info: User profile information
        - quota_info: Quota settings and usage
        - api_keys: List of all user's API keys with stats
        - activity_summary: Recent activity stats

    Response Codes:
        - DATA_RETRIEVED: User details fetched successfully
        - USER_NOT_FOUND: User not found
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        # Get quota information
        quota_serializer = UserQuotaSerializer(user_data)

        # Get all API keys
        api_keys = APIKey.objects.filter(user=user).order_by("-created_at")
        api_keys_serializer = AdminAPIKeyListSerializer(api_keys, many=True)

        # Get activity summary
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        month_ago = now - timedelta(days=30)
        week_ago = now - timedelta(days=7)

        from app.models import APIUsageLog

        activity_summary = {
            "total_api_keys": api_keys.count(),
            "active_api_keys": api_keys.filter(status="active").count(),
            "requests_last_30_days": APIUsageLog.objects.filter(api_key__user=user, timestamp__gte=month_ago).count(),
            "requests_last_7_days": APIUsageLog.objects.filter(api_key__user=user, timestamp__gte=week_ago).count(),
            "last_api_call": None,
        }

        # Get last API call
        last_log = APIUsageLog.objects.filter(api_key__user=user).order_by("-timestamp").first()
        if last_log:
            activity_summary["last_api_call"] = last_log.timestamp

        user_details = {
            "user_info": {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "user_type": user_data.user_type,
            },
            "quota_info": quota_serializer.data,
            "api_keys": api_keys_serializer.data,
            "activity_summary": activity_summary,
        }

        return create_response("DATA_RETRIEVED", {"user_details": user_details}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching user details: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
