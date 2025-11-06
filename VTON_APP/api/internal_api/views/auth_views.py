"""Authentication views for user registration, login, logout, and password management."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from api.internal_api.serializers.auth_serializers import (
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from app.models import UserData, AuditLog
from app.Controllers.ResponseCodesController import get_response_code
import logging

logger = logging.getLogger(__name__)


def create_response(code_key: str, data: dict = None, http_status: int = None):
    """
    Create standardized API response.

    Args:
        code_key (str): Response code key from ResponseCodesController
        data (dict): Additional data to include in response
        http_status (int): HTTP status code (optional, will use appropriate default)

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
        if code_prefix == "SUC":
            http_status = status.HTTP_200_OK
        elif code_prefix == "AUT":
            http_status = status.HTTP_401_UNAUTHORIZED
        elif code_prefix == "USR":
            http_status = status.HTTP_400_BAD_REQUEST
        elif code_prefix == "SYS":
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    return Response(response_data, status=http_status)  # Changed from http_status=http_status


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def register(request):
    """
    Register a new user account.

    POST /internal/api/auth/register

    Request Body:
        - username: string (required)
        - email: string (required)
        - password: string (required, min 8 chars)
        - password2: string (required, must match password)
        - first_name: string (required)
        - last_name: string (required)
        - phone_number: string (optional)
        - user_type: string (optional, default: 'customer')

    Response Codes:
        - SUC003: User created successfully
        - USR008: Username is required
        - USR007: Email is required
        - USR009: Password is required
        - USR010: Passwords do not match
        - USR006: Email already in use
        - USR019: Invalid phone number format
        - USR014: Invalid user type specified
        - USR002: Error creating user account
        - SYS004: Validation error
    """
    serializer = RegisterSerializer(data=request.data)

    if not serializer.is_valid():
        # Check for specific validation errors
        errors = serializer.errors

        if "username" in errors:
            if "required" in str(errors["username"]).lower():
                return create_response("USERNAME_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)
            elif "exist" in str(errors["username"]).lower():
                return create_response("RESOURCE_ALREADY_EXISTS", {"errors": errors, "field": "username"}, status.HTTP_409_CONFLICT)

        if "email" in errors:
            if "required" in str(errors["email"]).lower():
                return create_response("EMAIL_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)
            elif "exist" in str(errors["email"]).lower() or "use" in str(errors["email"]).lower():
                return create_response("EMAIL_ALREADY_IN_USE", {"errors": errors}, status.HTTP_409_CONFLICT)
            elif "invalid" in str(errors["email"]).lower():
                return create_response("INVALID_DATA_FORMAT", {"errors": errors, "field": "email"}, status.HTTP_400_BAD_REQUEST)

        if "password" in errors:
            if "required" in str(errors["password"]).lower():
                return create_response("PASSWORD_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        if "password2" in errors or "non_field_errors" in errors:
            if "match" in str(errors).lower():
                return create_response("PASSWORDS_DONT_MATCH", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        if "phone_number" in errors:
            return create_response("INVALID_PHONE_NUMBER", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        if "user_type" in errors:
            return create_response("INVALID_USER_TYPE", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        # Generic validation error
        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    try:
        user = serializer.save()

        # Log registration
        AuditLog.objects.create(
            user=user,
            action="create",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} registered",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"New user registered: {user.username} ({user.email})")

        # Return user data
        user_serializer = UserSerializer(user)

        return create_response("RESOURCE_CREATED", {"user": user_serializer.data}, status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return create_response("USER_CREATION_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def login_view(request):
    """
    Authenticate non-admin users and return JWT tokens.

    This endpoint is for regular users (customer, store_owner).
    Admin users should use the /admin-login endpoint.

    POST /internal/api/auth/login

    Request Body:
        - username: string (required)
        - password: string (required)

    Response:
        - user: User data object (includes user_type field)
        - access: JWT access token (30 minutes validity)
        - refresh: JWT refresh token (7 days validity)

    Response Codes:
        - SUC006: Login successful
        - USR008: Username is required
        - USR009: Password is required
        - AUT003: Invalid credentials
        - AUT004: Access denied (admin user attempting to login via non-admin endpoint)
        - USR015: User account is inactive
        - AUT006: Account suspended
        - SYS004: Validation error

    Security Features:
        - Prevents admin users from logging in (redirects to admin endpoint)
        - JWT tokens with automatic rotation on refresh
        - Token blacklisting after logout
        - Account suspension check
        - Audit logging
        - Custom claims (user_type, is_verified, is_premium)
    """
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        errors = serializer.errors

        if "username" in errors:
            return create_response("USERNAME_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        if "password" in errors:
            return create_response("PASSWORD_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]

    # Authenticate user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        # Check if account is active
        if not user.is_active:
            return create_response("USER_ACCOUNT_INACTIVE", http_status=status.HTTP_403_FORBIDDEN)

        # Check if account is suspended
        try:
            user_data = user.userdata
            if user_data.is_suspended:
                return create_response(
                    "ACCOUNT_SUSPENDED", {"suspension_reason": user_data.suspension_reason, "suspended_at": user_data.suspended_at}, status.HTTP_403_FORBIDDEN
                )
        except UserData.DoesNotExist:
            # Create UserData if it doesn't exist
            UserData.objects.create(user=user)

        # ADMIN CHECK - Reject admin users from this endpoint
        is_admin = False

        # Check Django admin status
        if user.is_staff or user.is_superuser:
            is_admin = True

        # Check user_type in UserData
        try:
            if user.userdata.user_type == "admin":
                is_admin = True
        except UserData.DoesNotExist:
            pass

        if is_admin:
            # Log admin login attempt via non-admin endpoint
            AuditLog.objects.create(
                user=user,
                action="login_denied",
                resource_type="User",
                resource_id=str(user.id),
                description=f"Admin user {username} attempted to login via non-admin endpoint",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            logger.warning(f"Admin user attempted non-admin login: {username}")

            return create_response("ACCESS_DENIED", {"detail": "Admin users must use the /admin-login endpoint."}, http_status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Add custom claims to JWT
        refresh["username"] = user.username
        refresh["email"] = user.email
        refresh["is_staff"] = user.is_staff

        try:
            user_data = user.userdata
            refresh["user_type"] = user_data.user_type
            refresh["is_verified"] = user_data.is_verified
            refresh["is_premium"] = user_data.is_premium
        except UserData.DoesNotExist:
            refresh["user_type"] = "customer"
            refresh["is_verified"] = False
            refresh["is_premium"] = False

        # Update last login in UserData
        try:
            user_data = user.userdata
            user_data.last_login_at = timezone.now()
            user_data.save(update_fields=["last_login_at"])
        except UserData.DoesNotExist:
            UserData.objects.create(user=user, last_login_at=timezone.now())

        # Log login
        AuditLog.objects.create(
            user=user,
            action="login",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} logged in",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"User logged in: {user.username}")

        # Return user data with JWT tokens
        user_serializer = UserSerializer(user)

        return create_response(
            "LOGIN_SUCCESS",
            {
                "user": user_serializer.data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status.HTTP_200_OK,
        )
    else:
        # Log failed login attempt
        try:
            failed_user = User.objects.filter(username=username).first()
            if failed_user:
                AuditLog.objects.create(
                    user=failed_user,
                    action="login_failed",
                    resource_type="User",
                    resource_id=str(failed_user.id),
                    description=f"Failed login attempt for user {username}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
        except Exception as e:
            logger.error(f"Error logging failed login: {str(e)}")

        return create_response("INVALID_CREDENTIALS", http_status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def admin_login_view(request):
    """
    Authenticate admin users ONLY and return JWT tokens.

    This endpoint is specifically for admin users (staff, superuser, or user_type='admin').
    Regular users will be rejected even with valid credentials.

    POST /internal/api/auth/admin-login

    Request Body:
        - username: string (required)
        - password: string (required)

    Response:
        - user: User data object
        - access: JWT access token (30 minutes validity)
        - refresh: JWT refresh token (7 days validity)

    Response Codes:
        - SUC006: Login successful (admin user)
        - USR008: Username is required
        - USR009: Password is required
        - AUT003: Invalid credentials
        - AUT001: Access denied (valid user but not admin)
        - USR015: User account is inactive
        - AUT006: Account suspended
        - SYS004: Validation error

    Security Features:
        - Admin-only authentication (rejects non-admin users)
        - JWT tokens with automatic rotation on refresh
        - Token blacklisting after logout
        - Account suspension check
        - Audit logging
        - Custom claims (user_type, is_verified, is_premium)
    """
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        errors = serializer.errors

        if "username" in errors:
            return create_response("USERNAME_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        if "password" in errors:
            return create_response("PASSWORD_REQUIRED", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]

    # Authenticate user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        # Check if account is active
        if not user.is_active:
            return create_response("USER_ACCOUNT_INACTIVE", http_status=status.HTTP_403_FORBIDDEN)

        # Check if account is suspended
        try:
            user_data = user.userdata
            if user_data.is_suspended:
                return create_response(
                    "ACCOUNT_SUSPENDED", {"suspension_reason": user_data.suspension_reason, "suspended_at": user_data.suspended_at}, status.HTTP_403_FORBIDDEN
                )
        except UserData.DoesNotExist:
            # Create UserData if it doesn't exist
            UserData.objects.create(user=user)

        # ADMIN CHECK - Reject non-admin users
        is_admin = False

        # Check Django admin status
        if user.is_staff or user.is_superuser:
            is_admin = True

        # Check user_type in UserData
        try:
            if user.userdata.user_type == "admin":
                is_admin = True
        except UserData.DoesNotExist:
            pass

        if not is_admin:
            # Log failed admin login attempt (valid user but not admin)
            AuditLog.objects.create(
                user=user,
                action="admin_login_denied",
                resource_type="User",
                resource_id=str(user.id),
                description=f"Non-admin user {username} attempted to login via admin endpoint",
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

            logger.warning(f"Non-admin user attempted admin login: {username}")

            return create_response(
                "ACCESS_DENIED", {"detail": "This endpoint is for admin users only. Please use the regular login endpoint."}, http_status=status.HTTP_403_FORBIDDEN
            )

        # Generate JWT tokens for admin user
        refresh = RefreshToken.for_user(user)

        # Add custom claims to JWT
        refresh["username"] = user.username
        refresh["email"] = user.email
        refresh["is_staff"] = user.is_staff
        refresh["is_admin"] = True  # Explicitly mark as admin in token

        try:
            user_data = user.userdata
            refresh["user_type"] = user_data.user_type
            refresh["is_verified"] = user_data.is_verified
            refresh["is_premium"] = user_data.is_premium
        except UserData.DoesNotExist:
            refresh["user_type"] = "customer"
            refresh["is_verified"] = False
            refresh["is_premium"] = False

        # Update last login in UserData
        try:
            user_data = user.userdata
            user_data.last_login_at = timezone.now()
            user_data.save(update_fields=["last_login_at"])
        except UserData.DoesNotExist:
            UserData.objects.create(user=user, last_login_at=timezone.now())

        # Log admin login
        AuditLog.objects.create(
            user=user,
            action="admin_login",
            resource_type="User",
            resource_id=str(user.id),
            description=f"Admin user {user.username} logged in via admin endpoint",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Admin user logged in: {user.username}")

        # Return user data with JWT tokens
        user_serializer = UserSerializer(user)

        return create_response(
            "LOGIN_SUCCESS",
            {
                "user": user_serializer.data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status.HTTP_200_OK,
        )
    else:
        # Log failed login attempt
        try:
            failed_user = User.objects.filter(username=username).first()
            if failed_user:
                AuditLog.objects.create(
                    user=failed_user,
                    action="admin_login_failed",
                    resource_type="User",
                    resource_id=str(failed_user.id),
                    description=f"Failed admin login attempt for user {username}",
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
        except Exception as e:
            logger.error(f"Error logging failed admin login: {str(e)}")

        return create_response("INVALID_CREDENTIALS", http_status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def logout_view(request):
    """
    Logout user and blacklist JWT refresh token.

    POST /internal/api/auth/logout

    Request Body:
        - refresh: string (required) - JWT refresh token to blacklist

    Response Codes:
        - SUC007: Logout successful
        - AUT002: Login required (if not authenticated)
        - SYS004: Validation error (invalid/expired token)

    Note:
        - Refresh token will be blacklisted to prevent reuse
        - Access tokens expire naturally after 30 minutes
        - Once logged out, user must login again to get new tokens
    """
    user = request.user

    # Get refresh token from request
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return create_response("VALIDATION_ERROR", {"errors": {"refresh": ["Refresh token is required for logout"]}}, status.HTTP_400_BAD_REQUEST)

    try:
        # Blacklist the refresh token
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info(f"JWT refresh token blacklisted for user: {user.username}")
    except TokenError as e:
        logger.warning(f"Failed to blacklist token during logout: {str(e)}")
        return create_response("VALIDATION_ERROR", {"detail": "Invalid or expired refresh token"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error blacklisting token: {str(e)}")
        return create_response("SYSTEM_ERROR", {"detail": "An error occurred during logout"}, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Log logout
    try:
        AuditLog.objects.create(
            user=user,
            action="logout",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} logged out",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except Exception as e:
        logger.error(f"Error logging logout: {str(e)}")

    logger.info(f"User logged out: {user.username}")

    return create_response("LOGOUT_SUCCESS", http_status=status.HTTP_200_OK)  # Changed 'status' to 'http_status'


@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def token_refresh_view(request):
    """
    Refresh JWT access token using refresh token.

    POST /internal/api/auth/token/refresh

    Request Body:
        - refresh: string (required) - The refresh token

    Response:
        - access: New JWT access token
        - refresh: New refresh token (old one is blacklisted)

    Response Codes:
        - SUC002: Token refreshed successfully
        - SYS004: Validation error (invalid/expired token)

    Security Features:
        - Automatic token rotation (old refresh token is blacklisted)
        - Token blacklist verification
        - Prevents use of expired or invalid tokens
    """
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return create_response("VALIDATION_ERROR", {"errors": {"refresh": ["Refresh token is required"]}}, status.HTTP_400_BAD_REQUEST)

    try:
        # Create RefreshToken instance
        refresh = RefreshToken(refresh_token)

        # Get user from token
        user_id = refresh.get("user_id")

        # Generate new access token
        access_token = str(refresh.access_token)

        # Token rotation: blacklist old token and create new one
        refresh.blacklist()

        # Create new refresh token
        new_refresh = RefreshToken.for_user(User.objects.get(id=user_id))

        # Add custom claims to new refresh token
        try:
            user = User.objects.get(id=user_id)
            new_refresh["username"] = user.username
            new_refresh["email"] = user.email
            new_refresh["is_staff"] = user.is_staff

            try:
                user_data = user.userdata
                new_refresh["user_type"] = user_data.user_type
                new_refresh["is_verified"] = user_data.is_verified
                new_refresh["is_premium"] = user_data.is_premium
            except UserData.DoesNotExist:
                new_refresh["user_type"] = "customer"
                new_refresh["is_verified"] = False
                new_refresh["is_premium"] = False
        except User.DoesNotExist:
            pass

        logger.info(f"Token refreshed for user ID: {user_id}")

        return create_response(
            "DATA_RETRIEVED",
            {
                "access": access_token,
                "refresh": str(new_refresh),
            },
            status.HTTP_200_OK,
        )

    except TokenError as e:
        logger.error(f"Token refresh error: {str(e)}")
        return create_response("VALIDATION_ERROR", {"detail": "Invalid or expired refresh token"}, status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        logger.error(f"User not found during token refresh")
        return create_response("VALIDATION_ERROR", {"detail": "User not found"}, status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        return create_response("SYSTEM_ERROR", {"detail": "An error occurred while refreshing token"}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def user_info(request):
    """
    Get current authenticated user information.

    GET /internal/api/auth/me

    Response Codes:
        - SUC002: Data retrieved successfully
        - AUT002: Login required (if not authenticated)
        - USR011: User profile data not found
    """
    user = request.user

    try:
        # Ensure UserData exists
        if not hasattr(user, "userdata"):
            UserData.objects.create(user=user)

        serializer = UserSerializer(user)
        return create_response("DATA_RETRIEVED", {"user": serializer.data}, status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error fetching user info: {str(e)}")
        return create_response("USER_DATA_NOT_FOUND", {"detail": str(e)}, status.HTTP_404_NOT_FOUND)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def update_profile(request):
    """
    Update user profile information.

    PUT/PATCH /internal/api/auth/profile

    Request Body:
        - first_name: string (optional)
        - last_name: string (optional)
        - email: string (optional)
        - phone_number: string (optional)
        - company_name: string (optional)
        - address_line1: string (optional)
        - address_line2: string (optional)
        - city: string (optional)
        - state: string (optional)
        - country: string (optional)
        - postal_code: string (optional)

    Response Codes:
        - SUC004: Profile updated successfully
        - USR006: Email already in use
        - USR019: Invalid phone number format
        - USR020: Error updating user profile
        - USR021: Error updating address information
        - SYS004: Validation error
    """
    user = request.user
    serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={"request": request})

    if not serializer.is_valid():
        errors = serializer.errors

        if "email" in errors:
            if "exist" in str(errors["email"]).lower() or "use" in str(errors["email"]).lower():
                return create_response("EMAIL_ALREADY_IN_USE", {"errors": errors}, status.HTTP_409_CONFLICT)
            elif "invalid" in str(errors["email"]).lower():
                return create_response("INVALID_DATA_FORMAT", {"errors": errors, "field": "email"}, status.HTTP_400_BAD_REQUEST)

        if "phone_number" in errors:
            return create_response("INVALID_PHONE_NUMBER", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        # Check for address-related errors
        address_fields = ["address_line1", "address_line2", "city", "state", "country", "postal_code"]
        if any(field in errors for field in address_fields):
            return create_response("ADDRESS_UPDATE_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    try:
        serializer.save()

        # Log profile update
        AuditLog.objects.create(
            user=user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} updated profile",
            new_values=request.data,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Profile updated: {user.username}")

        # Return updated user data
        user_serializer = UserSerializer(user)

        return create_response("RESOURCE_UPDATED", {"user": user_serializer.data}, status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        return create_response("PROFILE_UPDATE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def change_password(request):
    """
    Change user password.

    POST /internal/api/auth/change-password

    Request Body:
        - old_password: string (required)
        - new_password: string (required, min 8 chars)
        - new_password2: string (required, must match new_password)

    Response Codes:
        - SUC010: Password changed successfully
        - USR009: Password is required
        - USR010: Passwords do not match
        - USR004: Current password is incorrect
        - USR003: Error changing password
        - SYS004: Validation error
    """
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if not serializer.is_valid():
        errors = serializer.errors

        if "old_password" in errors:
            return create_response("PASSWORD_REQUIRED", {"errors": errors, "field": "old_password"}, status.HTTP_400_BAD_REQUEST)

        if "new_password" in errors:
            return create_response("PASSWORD_REQUIRED", {"errors": errors, "field": "new_password"}, status.HTTP_400_BAD_REQUEST)

        if "new_password2" in errors or "non_field_errors" in errors:
            if "match" in str(errors).lower():
                return create_response("PASSWORDS_DONT_MATCH", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

        return create_response("VALIDATION_ERROR", {"errors": errors}, status.HTTP_400_BAD_REQUEST)

    # Check old password
    if not user.check_password(serializer.validated_data["old_password"]):
        return create_response("OLD_PASSWORD_INCORRECT", {"errors": {"old_password": ["Current password is incorrect."]}}, status.HTTP_400_BAD_REQUEST)

    try:
        # Set new password
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        # Log password change
        AuditLog.objects.create(
            user=user,
            action="update",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} changed password",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Password changed: {user.username}")

        return create_response("PASSWORD_RESET_SUCCESS", http_status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return create_response("PASSWORD_CHANGE_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_exempt
def delete_account(request):
    """
    Delete user account (soft delete - deactivate).

    POST /internal/api/auth/delete-account

    Request Body:
        - password: string (required for confirmation)
        - confirm: boolean (required, must be true)

    Response Codes:
        - SUC005: Account deleted successfully
        - USR009: Password is required
        - AUT003: Invalid password
        - SYS003: Required field is missing (confirm)
        - USR011: User profile data not found
    """
    user = request.user
    password = request.data.get("password")
    confirm = request.data.get("confirm", False)

    # Validation
    if not confirm:
        return create_response(
            "MISSING_REQUIRED_FIELD", {"errors": {"confirm": ["Account deletion must be confirmed with confirm=true"]}}, status.HTTP_400_BAD_REQUEST
        )

    if not password:
        return create_response("PASSWORD_REQUIRED", {"errors": {"password": ["Password is required to confirm account deletion"]}}, status.HTTP_400_BAD_REQUEST)

    # Verify password
    if not user.check_password(password):
        return create_response("INVALID_CREDENTIALS", {"errors": {"password": ["Invalid password"]}}, status.HTTP_401_UNAUTHORIZED)

    try:
        # Soft delete - deactivate account
        user.is_active = False
        user.save()

        # Update UserData
        try:
            user_data = user.userdata
            user_data.is_suspended = True
            user_data.suspension_reason = "User requested account deletion"
            user_data.suspended_at = timezone.now()
            user_data.save()
        except UserData.DoesNotExist:
            # Create UserData with suspension info
            UserData.objects.create(user=user, is_suspended=True, suspension_reason="User requested account deletion", suspended_at=timezone.now())

        # Log account deletion
        AuditLog.objects.create(
            user=user,
            action="delete",
            resource_type="User",
            resource_id=str(user.id),
            description=f"User {user.username} deleted account",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"Account deleted: {user.username}")

        return create_response("RESOURCE_DELETED", http_status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Account deletion error: {str(e)}")
        return create_response("SERVER_ERROR", data={"detail": str(e)}, http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)
