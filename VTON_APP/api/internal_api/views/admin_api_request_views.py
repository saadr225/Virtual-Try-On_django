"""Admin views for managing API key requests."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from app.models import APIKeyRequest, APIKey, AuditLog, UserData
from app.Controllers.ResponseCodesController import get_response_code
from api.internal_api.utils.permissions import IsStaffUser
from api.internal_api.serializers.api_request_serializers import (
    APIKeyRequestAdminListSerializer,
    APIKeyRequestAdminDetailSerializer,
    APIKeyRequestApprovalSerializer,
    APIKeyRequestRejectionSerializer,
)
from api.internal_api.serializers.client_api_management_seiralizers import (
    APIKeyCreateSerializer,
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


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStaffUser])
@csrf_exempt
def admin_list_api_key_requests(request):
    """
    List all API key requests (admin view).

    Only admin/staff users can access this endpoint.

    GET /internal/api/admin/api-key-requests/

    Query Parameters:
        - status: string (optional) - Filter by status: pending, approved, rejected, cancelled
        - user_id: integer (optional) - Filter by user ID
        - page: integer (optional, default: 1)
        - limit: integer (optional, default: 20, max: 100)

    Response Codes:
        - SUC002: Data retrieved successfully
        - SYS015: Invalid page number
        - SYS016: Invalid page size
    """
    try:
        queryset = APIKeyRequest.objects.all().select_related("user", "reviewed_by").order_by("-created_at")

        # Filter by status if provided
        status_filter = request.query_params.get("status")
        if status_filter:
            if status_filter in ["pending", "approved", "rejected", "cancelled"]:
                queryset = queryset.filter(status=status_filter)

        # Filter by user if provided
        user_id = request.query_params.get("user_id")
        if user_id:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except ValueError:
                return create_response("VALIDATION_ERROR", {"error": "user_id must be an integer"}, status.HTTP_400_BAD_REQUEST)

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

        requests = queryset[start:end]
        serializer = APIKeyRequestAdminListSerializer(requests, many=True)

        # Get summary statistics
        pending_count = APIKeyRequest.objects.filter(status="pending").count()
        approved_count = APIKeyRequest.objects.filter(status="approved").count()
        rejected_count = APIKeyRequest.objects.filter(status="rejected").count()

        return create_response(
            "DATA_RETRIEVED",
            {
                "requests": serializer.data,
                "pagination": {"page": page, "limit": limit, "total": total_count, "pages": (total_count + limit - 1) // limit},
                "summary": {
                    "pending": pending_count,
                    "approved": approved_count,
                    "rejected": rejected_count,
                },
            },
            status.HTTP_200_OK,
        )

    except ValueError:
        return create_response("INVALID_PAGE", {"error": "Page and limit must be integers"}, status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error listing API key requests: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStaffUser])
@csrf_exempt
def admin_get_api_key_request_detail(request, request_id):
    """
    Get detailed information about a specific API key request (admin view).

    GET /internal/api/admin/api-key-requests/{request_id}/

    Path Parameters:
        - request_id: UUID of the request

    Response Codes:
        - SUC002: Data retrieved successfully
        - USR006: Request not found
    """
    try:
        api_key_request = APIKeyRequest.objects.select_related("user", "reviewed_by", "generated_api_key").get(request_id=request_id)

        serializer = APIKeyRequestAdminDetailSerializer(api_key_request)

        return create_response("DATA_RETRIEVED", {"request": serializer.data}, status.HTTP_200_OK)

    except APIKeyRequest.DoesNotExist:
        logger.warning(f"API key request not found: {request_id}")
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStaffUser])
@csrf_exempt
def admin_approve_api_key_request(request, request_id):
    """
    Approve an API key request (does not create the actual API key; enables user to do so).

    POST /internal/api/admin/api-key-requests/{request_id}/approve/

    Path Parameters:
        - request_id: UUID of the request

    Request Body:
        - payment_date: date (required) - Date of payment
        - payment_amount: decimal (required) - Payment amount
        - payment_proof: file (optional) - Payment receipt/proof
        - admin_notes: string (optional) - Internal notes
        - approved_rate_limit_per_minute: integer (required)
        - approved_rate_limit_per_hour: integer (required)
        - approved_rate_limit_per_day: integer (required)
        - approved_monthly_quota: integer (required)
        - approved_expires_in_days: integer (optional, null = never expires)

    Response Codes:
        - API101: API key request approved, user may create API keys
        - USR006: Request not found
        - API008: Request cannot be approved (not pending)
        - SYS004: Validation error
    """
    try:
        api_key_request = APIKeyRequest.objects.select_related("user").get(request_id=request_id)

        if not api_key_request.can_be_approved():
            return create_response(
                "API_KEY_UPDATE_ERROR",
                {"error": f"Request cannot be approved (status: {api_key_request.status})"},
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = APIKeyRequestApprovalSerializer(data=request.data)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Update request with approval details
        api_key_request.status = "approved"
        api_key_request.reviewed_by = request.user
        api_key_request.reviewed_at = timezone.now()
        api_key_request.payment_date = validated_data["payment_date"]
        api_key_request.payment_amount = validated_data["payment_amount"]
        api_key_request.admin_notes = validated_data.get("admin_notes", "")
        api_key_request.approved_rate_limit_per_minute = validated_data["approved_rate_limit_per_minute"]
        api_key_request.approved_rate_limit_per_hour = validated_data["approved_rate_limit_per_hour"]
        api_key_request.approved_rate_limit_per_day = validated_data["approved_rate_limit_per_day"]
        api_key_request.approved_monthly_quota = validated_data["approved_monthly_quota"]
        api_key_request.approved_expires_in_days = validated_data.get("approved_expires_in_days")

        # Handle payment proof file upload
        if "payment_proof" in request.FILES:
            api_key_request.payment_proof = request.FILES["payment_proof"]

        api_key_request.save()

        # Enable API key creation for this user
        user_data, created = UserData.objects.get_or_create(user=api_key_request.user)
        user_data.is_api_approved = True
        user_data.api_key_generation_enabled = True
        user_data.approved_by = request.user
        user_data.approved_at = timezone.now()

        # Set approved quota/limits from the approval form
        user_data.max_api_keys = validated_data.get("max_api_keys", user_data.max_api_keys)
        user_data.user_monthly_quota = validated_data.get("user_monthly_quota", user_data.user_monthly_quota)
        user_data.default_rate_limit_per_minute = api_key_request.approved_rate_limit_per_minute
        user_data.default_rate_limit_per_hour = api_key_request.approved_rate_limit_per_hour
        user_data.default_rate_limit_per_day = api_key_request.approved_rate_limit_per_day
        user_data.default_monthly_quota = api_key_request.approved_monthly_quota
        user_data.save()

        # Log approval
        AuditLog.objects.create(
            user=request.user,
            action="approve",
            resource_type="APIKeyRequest",
            resource_id=str(api_key_request.request_id),
            description=(f"API key request approved for '{api_key_request.user.username}'. User may now create API keys."),
            new_values={
                "payment_amount": str(validated_data["payment_amount"]),
                "approved_quota": validated_data["approved_monthly_quota"],
            },
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key request approved: {api_key_request.requested_key_name} " f"for {api_key_request.user.username} by {request.user.username}")

        # Return the request details; no API key is generated at this step
        detail_serializer = APIKeyRequestAdminDetailSerializer(api_key_request)

        return create_response(
            "API_KEY_REQUEST_APPROVED",
            {"request": detail_serializer.data, "message": "API key request approved; user may now create API keys."},
            status.HTTP_200_OK,
        )

    except APIKeyRequest.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error approving API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStaffUser])
@csrf_exempt
def admin_reject_api_key_request(request, request_id):
    """
    Reject an API key request.

    POST /internal/api/admin/api-key-requests/{request_id}/reject/

    Path Parameters:
        - request_id: UUID of the request

    Request Body:
        - rejection_reason: string (required) - Reason for rejection
        - admin_notes: string (optional) - Internal notes

    Response Codes:
        - SUC003: Data updated successfully
        - USR006: Request not found
        - API008: Request cannot be rejected (not pending)
        - SYS004: Validation error
    """
    try:
        api_key_request = APIKeyRequest.objects.get(request_id=request_id)

        if not api_key_request.can_be_rejected():
            return create_response("API_KEY_UPDATE_ERROR", {"error": f"Request cannot be rejected (status: {api_key_request.status})"}, status.HTTP_400_BAD_REQUEST)

        serializer = APIKeyRequestRejectionSerializer(data=request.data)

        if not serializer.is_valid():
            return create_response("VALIDATION_ERROR", {"errors": serializer.errors}, status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Update request with rejection details
        api_key_request.status = "rejected"
        api_key_request.reviewed_by = request.user
        api_key_request.reviewed_at = timezone.now()
        api_key_request.rejection_reason = validated_data["rejection_reason"]
        api_key_request.admin_notes = validated_data.get("admin_notes", "")
        api_key_request.save()

        # Log rejection
        AuditLog.objects.create(
            user=request.user,
            action="reject",
            resource_type="APIKeyRequest",
            resource_id=str(api_key_request.request_id),
            description=(f"API key request rejected for '{api_key_request.user.username}'. " f"Reason: {validated_data['rejection_reason']}"),
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        logger.info(f"API key request rejected: {api_key_request.requested_key_name} " f"for {api_key_request.user.username} by {request.user.username}")

        detail_serializer = APIKeyRequestAdminDetailSerializer(api_key_request)

        return create_response("DATA_UPDATED", {"request": detail_serializer.data}, status.HTTP_200_OK)

    except APIKeyRequest.DoesNotExist:
        return create_response("USER_NOT_FOUND", http_status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error rejecting API key request: {str(e)}")
        return create_response("SERVER_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)
