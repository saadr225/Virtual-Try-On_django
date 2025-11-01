"""Authentication views for user registration, login, logout, and password management."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils import timezone
from api.internal_api.serializers.auth_serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer, UserSerializer, UserUpdateSerializer
from app.models import UserData, AuditLog
import logging

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
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

    Response:
        - 201: User created successfully
        - 400: Validation errors
    """
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
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

            return Response({"message": "User registered successfully", "user": user_serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({"error": "Registration failed", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def login_view(request):
    """
    Authenticate user and create session.

    POST /internal/api/auth/login

    Request Body:
        - username: string (required)
        - password: string (required)
        - remember_me: boolean (optional, default: false)

    Response:
        - 200: Login successful, returns user data
        - 400: Validation errors
        - 401: Invalid credentials
    """
    serializer = LoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]
    remember_me = serializer.validated_data.get("remember_me", False)

    # Authenticate user
    user = authenticate(request, username=username, password=password)

    if user is not None:
        if not user.is_active:
            return Response({"error": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)

        # Log in the user
        login(request, user)

        # Set session expiry
        if remember_me:
            request.session.set_expiry(1209600)  # 2 weeks
        else:
            request.session.set_expiry(0)  # Browser close

        # Update last login in UserData
        try:
            user_data = user.userdata
            user_data.last_login_at = timezone.now()
            user_data.save(update_fields=["last_login_at"])
        except UserData.DoesNotExist:
            # Create UserData if it doesn't exist
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

        # Return user data
        user_serializer = UserSerializer(user)

        return Response({"message": "Login successful", "user": user_serializer.data}, status=status.HTTP_200_OK)

    else:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout user and destroy session.

    POST /internal/api/auth/logout

    Response:
        - 200: Logout successful
    """
    user = request.user

    # Log logout
    AuditLog.objects.create(
        user=user,
        action="logout",
        resource_type="User",
        resource_id=str(user.id),
        description=f"User {user.username} logged out",
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

    logger.info(f"User logged out: {user.username}")

    # Logout
    logout(request)

    return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    Get current authenticated user information.

    GET /internal/api/auth/me

    Response:
        - 200: User data
        - 401: Not authenticated
    """
    user = request.user
    serializer = UserSerializer(user)

    return Response({"user": serializer.data}, status=status.HTTP_200_OK)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
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

    Response:
        - 200: Profile updated successfully
        - 400: Validation errors
    """
    user = request.user
    serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={"request": request})

    if serializer.is_valid():
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

            return Response({"message": "Profile updated successfully", "user": user_serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({"error": "Profile update failed", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password.

    POST /internal/api/auth/change-password

    Request Body:
        - old_password: string (required)
        - new_password: string (required, min 8 chars)
        - new_password2: string (required, must match new_password)

    Response:
        - 200: Password changed successfully
        - 400: Validation errors
        - 401: Invalid old password
    """
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Check old password
    if not user.check_password(serializer.validated_data["old_password"]):
        return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

    # Set new password
    user.set_password(serializer.validated_data["new_password"])
    user.save()

    # Update session to prevent logout
    update_session_auth_hash(request, user)

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

    return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Get CSRF token for subsequent requests.

    GET /internal/api/auth/csrf

    Response:
        - 200: CSRF token set in cookie
    """
    return Response({"message": "CSRF cookie set"}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    """
    Delete user account (soft delete - deactivate).

    POST /internal/api/auth/delete-account

    Request Body:
        - password: string (required for confirmation)
        - confirm: boolean (required, must be true)

    Response:
        - 200: Account deleted successfully
        - 400: Validation errors
        - 401: Invalid password
    """
    user = request.user
    password = request.data.get("password")
    confirm = request.data.get("confirm", False)

    if not confirm:
        return Response({"error": "Account deletion must be confirmed"}, status=status.HTTP_400_BAD_REQUEST)

    if not password:
        return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Verify password
    if not user.check_password(password):
        return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)

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
        pass

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

    # Logout user
    logout(request)

    return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)
