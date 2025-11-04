"Views for handling Virtual Try-On (VTON) requests and responses."

from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.http import HttpResponse, Http404
from rest_framework.response import Response
from api.client_api.serializers import VTONSerializer, VTONResponseSerializer
from app.models.vton_models import VTONRequest
from app.models.audit_models import AuditLog
from app.models.analytics_models import APIUsageLog
from app.Controllers.HelpersController import FileController
from app.Controllers.VTONController import VTONController
from app.Controllers.ResponseCodesController import get_response_code
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import os
import logging
import time

# Setup logging
logger = logging.getLogger(__name__)


vton_controller = VTONController(os.getenv("VERTEX_AI_API_KEY"))


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
        if code_prefix == "SUC" or code_prefix == "API" and response_code["code"][3] == "1":
            http_status = status.HTTP_200_OK
        elif code_prefix == "AUT":
            http_status = status.HTTP_401_UNAUTHORIZED
        elif code_prefix == "USR" or code_prefix == "VTN" or code_prefix == "FIL":
            http_status = status.HTTP_400_BAD_REQUEST
        elif code_prefix == "SYS":
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    return Response(response_data, status=http_status)


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# Create your views here.
@api_view(["POST"])
@permission_classes([AllowAny])  # Middleware handles API key validation
@csrf_exempt
def virtual_tryon(request):
    """
    Handle virtual try-on requests by processing uploaded images and generating the output.

    This endpoint:
    1. Validates API key via middleware (X-API-Key header)
    2. Validates and saves uploaded images to the uploads/ directory
    3. Creates a database record to track the request
    4. Processes the images through the VTON controller
    5. Saves the result to the output/ directory
    6. Logs the request for analytics and audit purposes
    7. Returns public URLs for all images with status

    POST /api/v1/virtual-tryon/process/

    Request Headers:
        - X-API-Key: string (required) - Your API key for authentication

    Request Body (multipart/form-data):
        - person_image: File (required) - Image of the person
        - clothing_image: File (required) - Image of the clothing item
        - instructions: string (optional) - Additional instructions for the VTON process

    Response Codes:
        - API107: VTON request submitted successfully
        - VTN010: Invalid VTON request parameters
        - FIL001: File upload error
        - VTN009: VTON processing error
        - API010: API key missing
        - API002: Invalid API key
    """
    start_time = time.time()
    request_start = timezone.now()

    # Extract request metadata
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    referer = request.META.get("HTTP_REFERER", "")

    # Get API key from middleware (if validated)
    api_key = getattr(request, "api_key", None)
    user = api_key.user if api_key else None

    # Validate input data
    vton_serializer = VTONSerializer(data=request.data)
    if not vton_serializer.is_valid():
        logger.warning(f"VTON request validation failed from IP {ip_address}: {vton_serializer.errors}")
        return create_response("VTN010", {"errors": vton_serializer.errors}, status.HTTP_400_BAD_REQUEST)

    person_image_file = vton_serializer.validated_data.get("person_image")
    clothing_image_file = vton_serializer.validated_data.get("clothing_image")
    instructions = vton_serializer.validated_data.get("instructions", "")

    # Validate required files
    if not person_image_file or not clothing_image_file:
        error_detail = {}
        if not person_image_file:
            error_detail["person_image"] = ["Person image is required."]
        if not clothing_image_file:
            error_detail["clothing_image"] = ["Clothing image is required."]

        logger.warning(f"Missing required images from IP {ip_address}")
        return create_response("VTN010", {"errors": error_detail}, status.HTTP_400_BAD_REQUEST)

    # Get file sizes
    person_image_size = person_image_file.size
    clothing_image_size = clothing_image_file.size

    # Create database record with metadata
    vton_request = VTONRequest(
        user=user,
        api_key=api_key,
        source="api",
        ip_address=ip_address,
        user_agent=user_agent,
        referer=referer,
        status="pending",
        person_image_size=person_image_size,
        clothing_image_size=clothing_image_size,
        metadata={
            "instructions": instructions,
            "request_time": request_start.isoformat(),
        },
    )

    try:
        # Save uploaded images with unique filenames
        logger.info(f"Processing VTON request from IP {ip_address}")
        person_image_path, person_original_name = FileController.save_uploaded_image(person_image_file, subfolder="vton/uploads", prefix="person")
        clothing_image_path, clothing_original_name = FileController.save_uploaded_image(clothing_image_file, subfolder="vton/uploads", prefix="clothing")

        # Update database record with upload info
        vton_request.person_image = person_image_path
        vton_request.clothing_image = clothing_image_path
        vton_request.person_image_original_name = person_original_name
        vton_request.clothing_image_original_name = clothing_original_name
        vton_request.save()

        logger.info(f"Created VTON request: {vton_request.request_id}")

        # Create audit log for request creation
        try:
            AuditLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                action="create",
                resource_type="VTONRequest",
                resource_id=str(vton_request.request_id),
                description=f"VTON request created from {vton_request.source}",
                metadata={
                    "person_image_size": person_image_size,
                    "clothing_image_size": clothing_image_size,
                    "has_instructions": bool(instructions),
                },
            )
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")

        save_time = time.time()
        logger.info(f"Image save took: {save_time - start_time:.2f}s")

    except Exception as e:
        logger.error(f"Error saving uploaded images: {str(e)}", exc_info=True)
        return create_response("FIL001", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Process the images and generate the virtual try-on result
    try:
        # Update status to processing
        vton_request.status = "processing"
        vton_request.processing_started_at = timezone.now()
        vton_request.save()

        processing_start = time.time()
        logger.info(f"Setup took: {processing_start - save_time:.2f}s")

        # Convert relative paths to absolute paths for the API
        person_image_absolute_path = os.path.join(settings.MEDIA_ROOT, person_image_path)
        clothing_image_absolute_path = os.path.join(settings.MEDIA_ROOT, clothing_image_path)

        logger.info(f"Processing VTON request {vton_request.request_id}")
        logger.info(f"  Person: {person_image_absolute_path}")
        logger.info(f"  Clothing: {clothing_image_absolute_path}")

        # Call the VTON controller with absolute paths
        output_image = vton_controller.generate_virtual_tryon(person_image_absolute_path, clothing_image_absolute_path, instructions, False)  # cloths_on deprecated

        processing_end = time.time()
        processing_duration = processing_end - processing_start
        logger.info(f"VTON API call took: {processing_duration:.2f}s")

        # Save result image with unique filename
        logger.info(f"Saving result image for request: {vton_request.request_id}")
        result_image_path = FileController.save_pil_image(output_image, subfolder="vton/output", prefix="result")

        # Get result file size
        result_absolute_path = os.path.join(settings.MEDIA_ROOT, result_image_path)
        result_image_size = os.path.getsize(result_absolute_path) if os.path.exists(result_absolute_path) else None

        # Update database record with result
        vton_request.result_image = result_image_path
        vton_request.result_image_size = result_image_size
        vton_request.status = "completed"
        vton_request.processing_completed_at = timezone.now()
        vton_request.completed_at = timezone.now()
        vton_request.processing_duration_seconds = Decimal(str(processing_duration))
        vton_request.save()

        logger.info(f"Successfully completed VTON request: {vton_request.request_id}")

        # Create audit log for completion
        try:
            AuditLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                action="update",
                resource_type="VTONRequest",
                resource_id=str(vton_request.request_id),
                description=f"VTON request completed successfully",
                metadata={
                    "processing_duration_seconds": float(processing_duration),
                    "result_image_size": result_image_size,
                },
            )
        except Exception as e:
            logger.error(f"Error creating completion audit log: {str(e)}")

        # Serialize and return response with public URLs
        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        total_time = time.time() - start_time
        logger.info(f"Total request time: {total_time:.2f}s")

        # Log API usage
        try:
            APIUsageLog.objects.create(
                api_key=api_key,
                vton_request=vton_request,
                endpoint=request.path,
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                request_body_size=person_image_size + clothing_image_size,
                response_status_code=status.HTTP_200_OK,
                response_body_size=len(str(response_serializer.data)),
                response_time_ms=int(total_time * 1000),
                is_successful=True,
            )
        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")

        return create_response("VTON_REQUEST_COMPLETED", response_serializer.data, status.HTTP_200_OK)

    except Exception as e:
        # Update status to failed
        vton_request.status = "failed"
        vton_request.error_message = str(e)
        vton_request.processing_completed_at = timezone.now()
        vton_request.completed_at = timezone.now()

        if vton_request.processing_started_at:
            processing_duration = (timezone.now() - vton_request.processing_started_at).total_seconds()
            vton_request.processing_duration_seconds = Decimal(str(processing_duration))

        vton_request.save()

        logger.error(f"VTON processing failed for request {vton_request.request_id}: {str(e)}", exc_info=True)

        # Create audit log for failure
        try:
            AuditLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                action="update",
                resource_type="VTONRequest",
                resource_id=str(vton_request.request_id),
                description=f"VTON request failed",
                metadata={
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                },
            )
        except Exception as audit_error:
            logger.error(f"Error creating failure audit log: {str(audit_error)}")

        # Log API usage for failed request
        try:
            total_time = time.time() - start_time
            APIUsageLog.objects.create(
                api_key=api_key,
                vton_request=vton_request,
                endpoint=request.path,
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                request_body_size=person_image_size + clothing_image_size,
                response_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                response_time_ms=int(total_time * 1000),
                is_successful=False,
                error_message=str(e),
                error_code="VTN009",
            )
        except Exception as log_error:
            logger.error(f"Error logging failed API usage: {str(log_error)}")

        # Return error with partial data (uploaded images still accessible)
        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        return create_response("VTON_PROCESSING_ERROR", response_serializer.data, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])  # Middleware handles API key validation
def get_request_status(request, request_id):
    """
    Get the status and details of a VTON request by its UUID.

    GET /api/v1/virtual-tryon/{request_id}/status/

    Request Headers:
        - X-API-Key: string (required) - Your API key for authentication

    Args:
        request_id: UUID of the VTON request

    Response Codes:
        - API111: VTON status fetched successfully
        - VTN001: VTON request not found
        - API010: API key missing
        - API002: Invalid API key

    Returns:
        JSON response with request details including public URLs
    """
    request_start = time.time()
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Get API key from middleware
    api_key = getattr(request, "api_key", None)
    user = api_key.user if api_key else None

    try:
        vton_request = get_object_or_404(VTONRequest, request_id=request_id)

        # Create audit log for access
        try:
            AuditLog.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                action="access",
                resource_type="VTONRequest",
                resource_id=str(vton_request.request_id),
                description=f"VTON request status accessed",
                metadata={
                    "status": vton_request.status,
                },
            )
        except Exception as e:
            logger.error(f"Error creating audit log: {str(e)}")

        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        # Log API usage
        try:
            total_time = time.time() - request_start
            APIUsageLog.objects.create(
                api_key=api_key,
                vton_request=vton_request,
                endpoint=request.path,
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                response_status_code=status.HTTP_200_OK,
                response_body_size=len(str(response_serializer.data)),
                response_time_ms=int(total_time * 1000),
                is_successful=True,
            )
        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")

        return create_response("VTON_STATUS_FETCHED", response_serializer.data, status.HTTP_200_OK)

    except Http404:
        # Handle the expected case where request_id doesn't exist
        logger.info(f"VTON request not found: {request_id}")

        # Log failed API usage
        try:
            total_time = time.time() - request_start
            APIUsageLog.objects.create(
                api_key=api_key,
                endpoint=request.path,
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                response_status_code=status.HTTP_404_NOT_FOUND,
                response_time_ms=int(total_time * 1000),
                is_successful=False,
                error_message=f"VTONRequest with ID {request_id} not found",
                error_code="VTN001",
            )
        except Exception as log_error:
            logger.error(f"Error logging failed API usage: {str(log_error)}")

        return create_response("VTON_REQUEST_NOT_FOUND", {"detail": f"VTONRequest with ID {request_id} not found"}, status.HTTP_404_NOT_FOUND)

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error retrieving request {request_id}: {str(e)}", exc_info=True)

        # Log failed API usage
        try:
            total_time = time.time() - request_start
            APIUsageLog.objects.create(
                api_key=api_key,
                endpoint=request.path,
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                response_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                response_time_ms=int(total_time * 1000),
                is_successful=False,
                error_message=str(e),
                error_code="SYS001",
            )
        except Exception as log_error:
            logger.error(f"Error logging failed API usage: {str(log_error)}")

        return create_response("SYSTEM_ERROR", {"detail": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])  # Middleware handles API key validation
def list_recent_requests(request):
    """
    List recent VTON requests (for the authenticated API key user).

    GET /api/v1/virtual-tryon/requests/

    Request Headers:
        - X-API-Key: string (required) - Your API key for authentication

    Query params:
        - limit: Number of requests to return (default: 10, max: 100)
        - status: Filter by status (pending, queued, processing, completed, failed, cancelled)

    Response Codes:
        - API110: VTON requests fetched successfully
        - SYS004: Validation error (invalid status filter)
        - API010: API key missing
        - API002: Invalid API key
    """
    request_start = time.time()
    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Get API key from middleware
    api_key = getattr(request, "api_key", None)
    user = api_key.user if api_key else None

    try:
        limit = min(int(request.GET.get("limit", 10)), 100)
    except ValueError:
        limit = 10

    status_filter = request.GET.get("status", None)

    # Validate status filter
    valid_statuses = ["pending", "queued", "processing", "completed", "failed", "cancelled"]
    if status_filter and status_filter not in valid_statuses:
        return create_response(
            "VALIDATION_ERROR", {"errors": {"status": [f"Invalid status. Must be one of: {', '.join(valid_statuses)}"]}}, status.HTTP_400_BAD_REQUEST
        )

    queryset = VTONRequest.objects.all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    # Filter by API key - users can only see their own requests
    if api_key:
        queryset = queryset.filter(api_key=api_key)

    requests_list = queryset[:limit]

    # Create audit log for list access
    try:
        AuditLog.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            action="access",
            resource_type="VTONRequest",
            resource_id="list",
            description=f"VTON requests list accessed",
            metadata={
                "limit": limit,
                "status_filter": status_filter,
                "result_count": len(requests_list),
            },
        )
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")

    response_serializer = VTONResponseSerializer(requests_list, many=True, context={"request": request})

    # Log API usage
    try:
        total_time = time.time() - request_start
        APIUsageLog.objects.create(
            api_key=api_key,
            endpoint=request.path,
            method=request.method,
            ip_address=ip_address,
            user_agent=user_agent,
            response_status_code=status.HTTP_200_OK,
            response_body_size=len(str(response_serializer.data)),
            response_time_ms=int(total_time * 1000),
            is_successful=True,
        )
    except Exception as e:
        logger.error(f"Error logging API usage: {str(e)}")

    return create_response("VTON_REQUESTS_FETCHED", {"requests": response_serializer.data, "count": len(requests_list)}, status.HTTP_200_OK)
