"""
Permission utilities for API key management.
Provides decorators and permission classes for role-based access control.
"""

from functools import wraps
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from app.Controllers.ResponseCodesController import get_response_code


def is_admin_user(user):
    """
    Check if user is an admin.

    Args:
        user: Django User object

    Returns:
        bool: True if user is admin
    """
    if not user or not user.is_authenticated:
        return False

    # Check Django admin/superuser status
    if user.is_superuser:
        return True

    # Check user_type in UserData
    try:
        if hasattr(user, "userdata") and user.userdata.user_type == "admin":
            return True
    except Exception:
        pass

    return False


def is_staff_user(user):
    """
    Check if user is a staff member (can manage API key requests).

    Args:
        user: Django User object

    Returns:
        bool: True if user is staff or admin
    """
    if not user or not user.is_authenticated:
        return False

    # Superusers and admins are staff
    if user.is_superuser or is_admin_user(user):
        return True

    # Check Django staff status
    if user.is_staff:
        return True

    return False


def admin_required(view_func):
    """
    Decorator to require admin permissions for a view.

    Usage:
        @admin_required
        @api_view(['POST'])
        @permission_classes([IsAuthenticated])
        def my_admin_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            response_code = get_response_code("ACCESS_DENIED")
            return Response(
                {"code": response_code["code"], "message": response_code["message"], "detail": "Admin privileges required for this action"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return view_func(request, *args, **kwargs)

    return wrapper


def can_modify_quotas(user):
    """
    Check if user can modify rate limits and quotas.
    Only admins can modify these settings.

    Args:
        user: Django User object

    Returns:
        bool: True if user can modify quotas
    """
    return is_admin_user(user)


def can_manage_all_keys(user):
    """
    Check if user can manage all API keys across all users.
    Only admins have this permission.

    Args:
        user: Django User object

    Returns:
        bool: True if user can manage all keys
    """
    return is_admin_user(user)


def can_manage_user_quotas(user):
    """
    Check if user can manage user-level quotas.
    Only admins have this permission.

    Args:
        user: Django User object

    Returns:
        bool: True if user can manage user quotas
    """
    return is_admin_user(user)


class IsAdminUser(BasePermission):
    """
    DRF Permission class: Only admin users are allowed.

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsAdminUser]
    """

    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsStaffUser(BasePermission):
    """
    DRF Permission class: Only staff users (including admins) are allowed.

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsStaffUser]
    """

    def has_permission(self, request, view):
        return is_staff_user(request.user)


class IsNotAdminUser(BasePermission):
    """
    DRF Permission class: Only non-admin users are allowed.
    Prevents admin users from accessing regular user endpoints.

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsNotAdminUser]
    """

    def has_permission(self, request, view):
        return not is_admin_user(request.user)


class CanModifyQuotas(BasePermission):
    """
    DRF Permission class: Only users who can modify quotas are allowed.

    Usage:
        class QuotaView(APIView):
            permission_classes = [IsAuthenticated, CanModifyQuotas]
    """

    def has_permission(self, request, view):
        return can_modify_quotas(request.user)


class CanManageAllKeys(BasePermission):
    """
    DRF Permission class: Only users who can manage all keys are allowed.

    Usage:
        class AllKeysView(APIView):
            permission_classes = [IsAuthenticated, CanManageAllKeys]
    """

    def has_permission(self, request, view):
        return can_manage_all_keys(request.user)


def get_user_permissions(user):
    """
    Get a dictionary of user permissions for API key management.

    Args:
        user: Django User object

    Returns:
        dict: Dictionary of permissions
    """
    return {
        "is_admin": is_admin_user(user),
        "is_staff": is_staff_user(user),
        "can_modify_quotas": can_modify_quotas(user),
        "can_manage_all_keys": can_manage_all_keys(user),
        "can_manage_user_quotas": can_manage_user_quotas(user),
    }


def validate_quota_modification(request, field_name):
    """
    Validate if user can modify a quota-related field.

    Args:
        request: Django request object
        field_name: Name of the field being modified

    Returns:
        tuple: (is_valid: bool, error_response: Response or None)
    """
    quota_fields = [
        "rate_limit_per_minute",
        "rate_limit_per_hour",
        "rate_limit_per_day",
        "monthly_quota",
        "user_monthly_quota",
        "default_rate_limit_per_minute",
        "default_rate_limit_per_hour",
        "default_rate_limit_per_day",
        "default_monthly_quota",
        "max_api_keys",
    ]

    if field_name in quota_fields and not can_modify_quotas(request.user):
        response_code = get_response_code("ACCESS_DENIED")
        error_response = Response(
            {"code": response_code["code"], "message": response_code["message"], "detail": f"Only admins can modify {field_name}"}, status=status.HTTP_403_FORBIDDEN
        )
        return False, error_response

    return True, None


def filter_quota_fields(data, user):
    """
    Filter out quota-related fields from data if user is not admin.

    Args:
        data: Dictionary of data
        user: Django User object

    Returns:
        dict: Filtered data dictionary
    """
    if can_modify_quotas(user):
        return data

    # Remove quota fields if user is not admin
    quota_fields = [
        "rate_limit_per_minute",
        "rate_limit_per_hour",
        "rate_limit_per_day",
        "monthly_quota",
    ]

    filtered_data = data.copy()
    for field in quota_fields:
        filtered_data.pop(field, None)

    return filtered_data
