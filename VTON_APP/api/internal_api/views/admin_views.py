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
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    AdminUserSuspendSerializer,
    AdminUserCreateSerializer,
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def list_all_users(request):
    """
    List all users in the system (Admin only).

    GET /internal/api/admin/users/

    Query Parameters:
        - user_type: string (optional) - Filter by user type (customer, store_owner, admin)
        - is_active: boolean (optional) - Filter by active status
        - is_suspended: boolean (optional) - Filter by suspension status
        - is_verified: boolean (optional) - Filter by verification status
        - is_premium: boolean (optional) - Filter by premium status
        - search: string (optional) - Search username, email, first/last name
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 20, max: 100)

    Response Codes:
        - LIST_FETCHED: Users list fetched successfully
        - AUT004: Access denied (not admin)
    """
    try:
        queryset = User.objects.select_related("userdata").all().order_by("-date_joined")

        # Search filter
        search_query = request.query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
            )

        # Filter by user_type
        user_type_filter = request.query_params.get("user_type")
        if user_type_filter:
            queryset = queryset.filter(userdata__user_type=user_type_filter)

        # Filter by is_active
        is_active_filter = request.query_params.get("is_active")
        if is_active_filter is not None:
            is_active = is_active_filter.lower() == "true"
            queryset = queryset.filter(is_active=is_active)

        # Filter by is_suspended
        is_suspended_filter = request.query_params.get("is_suspended")
        if is_suspended_filter is not None:
            is_suspended = is_suspended_filter.lower() == "true"
            queryset = queryset.filter(userdata__is_suspended=is_suspended)

        # Filter by is_verified
        is_verified_filter = request.query_params.get("is_verified")
        if is_verified_filter is not None:
            is_verified = is_verified_filter.lower() == "true"
            queryset = queryset.filter(userdata__is_verified=is_verified)

        # Filter by is_premium
        is_premium_filter = request.query_params.get("is_premium")
        if is_premium_filter is not None:
            is_premium = is_premium_filter.lower() == "true"
            queryset = queryset.filter(userdata__is_premium=is_premium)

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
        serializer = AdminUserListSerializer(users, many=True)

        return create_response(
            "LIST_FETCHED",
            {
                "users": serializer.data,
                "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit},
            },
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def get_user_by_id(request, user_id):
    """
    Get detailed information about a specific user by ID (Admin only).

    GET /internal/api/admin/users/id/<user_id>/

    Response Codes:
        - DATA_RETRIEVED: User details fetched successfully
        - USER_NOT_FOUND: User not found
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(id=user_id)
        serializer = AdminUserDetailSerializer(user)

        return create_response("DATA_RETRIEVED", {"user": serializer.data}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def create_user(request):
    """
    Create a new user (Admin only).

    POST /internal/api/admin/users/create/

    Request Body:
        - username: string (required)
        - email: string (required)
        - password: string (required, min 8 chars)
        - first_name: string (optional)
        - last_name: string (optional)
        - user_type: string (optional, default: customer)
        - is_staff: boolean (optional, default: false)
        - is_superuser: boolean (optional, default: false)
        - is_verified: boolean (optional, default: false)
        - phone_number: string (optional)

    Response Codes:
        - RESOURCE_CREATED: User created successfully
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    serializer = AdminUserCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

    try:
        user = serializer.save()

        # Log user creation
        AuditLog.objects.create(
            user=request.user,
            action="create",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} created user {user.username}",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} created user {user.username}")

        # Return created user
        result_serializer = AdminUserDetailSerializer(user)
        return create_response("RESOURCE_CREATED", {"user": result_serializer.data}, status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def update_user(request, username):
    """
    Update user information (Admin only).

    PUT/PATCH /internal/api/admin/users/<username>/update/

    Request Body:
        - email: string (optional)
        - first_name: string (optional)
        - last_name: string (optional)
        - is_active: boolean (optional)
        - is_staff: boolean (optional)
        - is_superuser: boolean (optional)
        - user_type: string (optional)
        - is_verified: boolean (optional)
        - is_premium: boolean (optional)
        - premium_expiry: datetime (optional)
        - phone_number: string (optional)
        - city: string (optional)
        - state: string (optional)
        - country: string (optional)
        - postal_code: string (optional)
        - metadata: object (optional)

    Response Codes:
        - RESOURCE_UPDATED: User updated successfully
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)

        serializer = AdminUserUpdateSerializer(instance=user, data=request.data, partial=True, context={"user": user})

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Log user update
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} updated user {username}",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} updated user {username}")

        # Return updated user
        result_serializer = AdminUserDetailSerializer(user)
        return create_response("RESOURCE_UPDATED", {"user": result_serializer.data}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def suspend_user(request, username):
    """
    Suspend or unsuspend a user (Admin only).

    POST /internal/api/admin/users/<username>/suspend/

    Request Body:
        - is_suspended: boolean (required) - True to suspend, False to unsuspend
        - suspension_reason: string (required if suspending)

    Response Codes:
        - RESOURCE_UPDATED: User suspension status updated
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        serializer = AdminUserSuspendSerializer(data=request.data)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        is_suspended = serializer.validated_data["is_suspended"]
        suspension_reason = serializer.validated_data.get("suspension_reason", "")

        # Update suspension status
        user_data.is_suspended = is_suspended
        if is_suspended:
            from django.utils import timezone

            user_data.suspension_reason = suspension_reason
            user_data.suspended_at = timezone.now()
            # Also deactivate user account
            user.is_active = False
            user.save()
        else:
            user_data.suspension_reason = ""
            user_data.suspended_at = None
            # Reactivate user account
            user.is_active = True
            user.save()

        user_data.save()

        # Log suspension action
        action_desc = f"suspended user {username}" if is_suspended else f"unsuspended user {username}"
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} {action_desc}",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} {action_desc}")

        return create_response(
            "RESOURCE_UPDATED",
            {
                "message": f"User {'suspended' if is_suspended else 'unsuspended'} successfully",
                "is_suspended": is_suspended,
                "suspension_reason": suspension_reason if is_suspended else None,
            },
            status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error suspending/unsuspending user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def delete_user(request, username):
    """
    Delete a user (soft delete - deactivate) (Admin only).

    DELETE /internal/api/admin/users/<username>/delete/

    Query Parameters:
        - hard_delete: boolean (optional, default: false) - True for permanent deletion

    Response Codes:
        - RESOURCE_DELETED: User deleted successfully
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Cannot delete yourself or other admins
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)

        # Prevent deleting yourself
        if user.id == request.user.id:
            return create_response(
                "VALIDATION_ERROR",
                {"error": "You cannot delete your own account"},
                status.HTTP_400_BAD_REQUEST,
            )

        # Prevent deleting other superusers (unless you are a superuser)
        if user.is_superuser and not request.user.is_superuser:
            return create_response(
                "ACCESS_DENIED",
                {"error": "Only superusers can delete other superuser accounts"},
                status.HTTP_403_FORBIDDEN,
            )

        hard_delete = request.query_params.get("hard_delete", "false").lower() == "true"

        if hard_delete and request.user.is_superuser:
            # Hard delete - permanent deletion
            username_deleted = user.username
            user_id = user.id
            user.delete()

            # Log deletion
            AuditLog.objects.create(
                user=request.user,
                action="delete",
                resource_type="User",
                resource_id=str(user_id),
                description=f"Admin {request.user.username} permanently deleted user {username_deleted}",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            logger.warning(f"Admin {request.user.username} permanently deleted user {username_deleted}")

            return create_response("RESOURCE_DELETED", {"message": "User permanently deleted"}, status.HTTP_200_OK)
        else:
            # Soft delete - deactivate
            user.is_active = False
            user.save()

            # Update UserData
            user_data, created = UserData.objects.get_or_create(user=user)
            user_data.is_suspended = True
            user_data.suspension_reason = f"Account deleted by admin {request.user.username}"
            from django.utils import timezone

            user_data.suspended_at = timezone.now()
            user_data.save()

            # Log deletion
            AuditLog.objects.create(
                user=request.user,
                action="delete",
                resource_type="User",
                resource_id=str(user.id),
                description=f"Admin {request.user.username} deactivated user {username}",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            logger.info(f"Admin {request.user.username} deactivated user {username}")

            return create_response("RESOURCE_DELETED", {"message": "User deactivated successfully"}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def change_user_password(request, username):
    """
    Change a user's password (Admin only).

    POST /internal/api/admin/users/<username>/change-password/

    Request Body:
        - new_password: string (required, min 8 chars)

    Response Codes:
        - RESOURCE_UPDATED: Password changed successfully
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid password
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)

        new_password = request.data.get("new_password")

        if not new_password:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"new_password": ["New password is required"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"new_password": ["Password must be at least 8 characters long"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Log password change
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} changed password for user {username}",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} changed password for user {username}")

        return create_response("RESOURCE_UPDATED", {"message": "Password changed successfully"}, status.HTTP_200_OK)

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error changing user password: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def verify_user(request, username):
    """
    Verify or unverify a user (Admin only).

    POST /internal/api/admin/users/<username>/verify/

    Request Body:
        - is_verified: boolean (required)

    Response Codes:
        - RESOURCE_UPDATED: Verification status updated
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        is_verified = request.data.get("is_verified")

        if is_verified is None:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"is_verified": ["This field is required"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        user_data.is_verified = is_verified
        user_data.save()

        # Log verification action
        action = "verified" if is_verified else "unverified"
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} {action} user {username}",
            new_values={"is_verified": is_verified},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} {action} user {username}")

        return create_response(
            "RESOURCE_UPDATED",
            {"message": f"User {action} successfully", "is_verified": is_verified},
            status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def set_user_premium(request, username):
    """
    Set or remove premium status for a user (Admin only).

    POST /internal/api/admin/users/<username>/premium/

    Request Body:
        - is_premium: boolean (required)
        - premium_expiry: datetime (optional) - Required if is_premium is True

    Response Codes:
        - RESOURCE_UPDATED: Premium status updated
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)
        user_data, created = UserData.objects.get_or_create(user=user)

        is_premium = request.data.get("is_premium")
        premium_expiry = request.data.get("premium_expiry")

        if is_premium is None:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"is_premium": ["This field is required"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        if is_premium and not premium_expiry:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"premium_expiry": ["Premium expiry date is required when setting premium status"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        user_data.is_premium = is_premium
        if is_premium:
            from django.utils.dateparse import parse_datetime

            user_data.premium_expiry = parse_datetime(premium_expiry) if isinstance(premium_expiry, str) else premium_expiry
        else:
            user_data.premium_expiry = None

        user_data.save()

        # Log premium status change
        action = "granted premium access to" if is_premium else "removed premium access from"
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} {action} user {username}",
            new_values={"is_premium": is_premium, "premium_expiry": str(premium_expiry) if premium_expiry else None},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} {action} user {username}")

        return create_response(
            "RESOURCE_UPDATED",
            {
                "message": f"Premium status {'granted' if is_premium else 'removed'} successfully",
                "is_premium": is_premium,
                "premium_expiry": user_data.premium_expiry,
            },
            status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error setting premium status: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def suspend_user_api_keys(request, username):
    """
    Suspend or activate all API keys for a user (Admin only).

    POST /internal/api/admin/users/<username>/api-keys/suspend/

    Request Body:
        - action: string (required) - "suspend" or "activate"
        - reason: string (optional) - Reason for suspension

    Response Codes:
        - RESOURCE_UPDATED: API keys status updated
        - USER_NOT_FOUND: User not found
        - VALIDATION_ERROR: Invalid data
        - AUT004: Access denied (not admin)
    """
    try:
        user = User.objects.get(username=username)

        action = request.data.get("action")
        reason = request.data.get("reason", "Suspended by admin")

        if action not in ["suspend", "activate"]:
            return create_response(
                "VALIDATION_ERROR",
                {"errors": {"action": ["Action must be 'suspend' or 'activate'"]}},
                status.HTTP_400_BAD_REQUEST,
            )

        # Update all user's API keys
        api_keys = APIKey.objects.filter(user=user)
        new_status = "suspended" if action == "suspend" else "active"
        updated_count = api_keys.update(status=new_status)

        # Log API key suspension
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="APIKey",
            resource_id=str(user.id),
            description=f"Admin {request.user.username} {action}d all API keys for user {username}. Reason: {reason}",
            new_values={"status": new_status, "count": updated_count},
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin {request.user.username} {action}d {updated_count} API keys for user {username}")

        return create_response(
            "RESOURCE_UPDATED",
            {
                "message": f"All API keys {action}d successfully",
                "keys_updated": updated_count,
                "new_status": new_status,
            },
            status.HTTP_200_OK,
        )

    except User.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error suspending user API keys: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@admin_required
@csrf_exempt
def get_user_statistics(request):
    """
    Get overall user statistics (Admin only).

    GET /internal/api/admin/users/statistics/

    Response:
        - total_users: Total number of users
        - active_users: Number of active users
        - suspended_users: Number of suspended users
        - verified_users: Number of verified users
        - premium_users: Number of premium users
        - users_by_type: Breakdown by user type
        - new_users_last_30_days: Users registered in last 30 days

    Response Codes:
        - DATA_RETRIEVED: Statistics fetched successfully
        - AUT004: Access denied (not admin)
    """
    try:
        from django.utils import timezone
        from datetime import timedelta

        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        # UserData statistics
        suspended_users = UserData.objects.filter(is_suspended=True).count()
        verified_users = UserData.objects.filter(is_verified=True).count()
        premium_users = UserData.objects.filter(is_premium=True).count()

        # Users by type
        users_by_type = {}
        for user_type, _ in UserData.USER_TYPE_CHOICES:
            users_by_type[user_type] = UserData.objects.filter(user_type=user_type).count()

        # New users in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        new_users_last_30_days = User.objects.filter(date_joined__gte=thirty_days_ago).count()

        # Total API keys
        total_api_keys = APIKey.objects.count()
        active_api_keys = APIKey.objects.filter(status="active").count()

        statistics = {
            "total_users": total_users,
            "active_users": active_users,
            "suspended_users": suspended_users,
            "verified_users": verified_users,
            "premium_users": premium_users,
            "users_by_type": users_by_type,
            "new_users_last_30_days": new_users_last_30_days,
            "total_api_keys": total_api_keys,
            "active_api_keys": active_api_keys,
        }

        return create_response("DATA_RETRIEVED", {"statistics": statistics}, status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error fetching user statistics: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
