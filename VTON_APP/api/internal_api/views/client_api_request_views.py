"""Client views for API key request submission and management."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from app.models import APIKeyRequest, AuditLog
from app.Controllers.ResponseCodesController import get_response_code
from api.internal_api.utils.permissions import IsNotAdminUser
from api.internal_api.serializers.api_request_serializers import (
    APIKeyRequestCreateSerializer,
    APIKeyRequestListSerializer,
    APIKeyRequestDetailSerializer,
    APIKeyRequestCancellationSerializer,
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
@permission_classes([IsAuthenticated, IsNotAdminUser])
@csrf_exempt
def submit_api_key_request(request):
    """
    Submit a new API key request (ticket).

    Regular users can submit requests to get API keys.
    Admin users cannot use this endpoint.

    POST /internal/api/api-key-requests/submit/

    Request Body:
        - requested_key_name: string (required) - Name for the API key
        - reason: string (required) - Reason for requesting the key
        - intended_use: string (optional) - How the key will be used
        - requested_rate_limit_per_minute: integer (optional) - Suggested limit
        - requested_rate_limit_per_hour: integer (optional) - Suggested limit
        - requested_rate_limit_per_day: integer (optional) - Suggested limit
        - requested_monthly_quota: integer (optional) - Suggested quota

    Response Codes:
        - SUC001: Request submitted successfully
        - SYS004: Validation error
    """
    serializer = APIKeyRequestCreateSerializer(data=request.data, context={"request": request})

    if not serializer.is_valid():
        return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

    try:
        api_key_request = serializer.save()

        # Log request submission
        AuditLog.objects.create(
            user=request.user,
            action="create",
            resource_type="APIKeyRequest",
            resource_id=str(api_key_request.request_id),
            description=f"API key request submitted: '{api_key_request.requested_key_name}'",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key request submitted: {api_key_request.requested_key_name} " f"by {request.user.username}")

        detail_serializer = APIKeyRequestDetailSerializer(api_key_request)

        return create_response("DATA_CREATED", {"request": detail_serializer.data}, status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error submitting API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotAdminUser])
@csrf_exempt
def list_my_api_key_requests(request):
    """
    List all API key requests for the authenticated user.

    GET /internal/api/api-key-requests/

    Query Parameters:
        - status: string (optional) - Filter by status: pending, approved, rejected, cancelled
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 10, max: 100)

    Response Codes:
        - SUC002: Data retrieved successfully
        - SYS015: Invalid page number
        - SYS016: Invalid page size
    """
    try:
        user = request.user
        queryset = APIKeyRequest.objects.filter(user=user).order_by("-created_at")

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            if status_filter in ["pending", "approved", "rejected", "cancelled"]:
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

        requests = queryset[start:end]
        serializer = APIKeyRequestListSerializer(requests, many=True)

        return create_response(
            "DATA_RETRIEVED",
            {"requests": serializer.data, "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit}},
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing API key requests: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsNotAdminUser])
@csrf_exempt
def get_api_key_request_detail(request, request_id):
    """
    Get detailed information about a specific API key request.

    GET /internal/api/api-key-requests/{request_id}/

    Path Parameters:
        - request_id: UUID of the request

    Response Codes:
        - SUC002: Data retrieved successfully
        - USR006: Request not found
    """
    try:
        api_key_request = APIKeyRequest.objects.get(user=request.user, request_id=request_id)
        serializer = APIKeyRequestDetailSerializer(api_key_request)

        return create_response("DATA_RETRIEVED", {"request": serializer.data}, status.HTTP_200_OK)

    except APIKeyRequest.DoesNotExist:
        logger.warning(f"API key request not found: {request_id}")
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsNotAdminUser])
@csrf_exempt
def cancel_api_key_request(request, request_id):
    """
    Cancel a pending API key request.

    POST /internal/api/api-key-requests/{request_id}/cancel/

    Path Parameters:
        - request_id: UUID of the request

    Request Body:
        - confirm: boolean (required, must be true)

    Response Codes:
        - SUC003: Data updated successfully
        - USR006: Request not found
        - SYS004: Validation error
        - API008: Request cannot be cancelled (not pending)
    """
    serializer = APIKeyRequestCancellationSerializer(data=request.data)

    if not serializer.is_valid():
        return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

    try:
        api_key_request = APIKeyRequest.objects.get(user=request.user, request_id=request_id)

        if not api_key_request.can_be_cancelled():
            return create_response("API_KEY_UPDATE_ERROR", {"error": "Only pending requests can be cancelled"}, status.HTTP_400_BAD_REQUEST)

        api_key_request.status = "cancelled"
        api_key_request.save()

        # Log cancellation
        AuditLog.objects.create(
            user=request.user,
            action="update",
            resource_type="APIKeyRequest",
            resource_id=str(api_key_request.request_id),
            description=f"API key request cancelled: '{api_key_request.requested_key_name}'",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key request cancelled: {api_key_request.requested_key_name} " f"by {request.user.username}")

        detail_serializer = APIKeyRequestDetailSerializer(api_key_request)

        return create_response("DATA_UPDATED", {"request": detail_serializer.data}, status.HTTP_200_OK)

    except APIKeyRequest.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error cancelling API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
