"Views for handling Virtual Try-On (VTON) requests and responses."

from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.http import HttpResponse
from rest_framework.response import Response
from api.client_api.serializers import VTONSerializer, VTONResponseSerializer
from api.client_api.models import VTONRequest
from app.Controllers.HelpersController import FileController
from app.Controllers.VTONController import VTONController
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
from django.utils import timezone
from django.conf import settings  # Add this import
import os
import logging
import time

# Setup logging
logger = logging.getLogger(__name__)


vton_controller = VTONController(os.getenv("VERTEX_AI_API_KEY"))


# Create your views here.
@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def virtual_tryon(request):
    start_time = time.time()

    """
    Handle virtual try-on requests by processing uploaded images and generating the output.

    This endpoint:
    1. Validates and saves uploaded images to the uploads/ directory
    2. Creates a database record to track the request
    3. Processes the images through the VTON controller
    4. Saves the result to the output/ directory
    5. Returns public URLs for all images with status
    """
    # Validate input data
    vton_serializer = VTONSerializer(data=request.data)
    if not vton_serializer.is_valid():
        return Response(vton_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    person_image_file = vton_serializer.validated_data.get("person_image")
    clothing_image_file = vton_serializer.validated_data.get("clothing_image")
    instructions = vton_serializer.validated_data.get("instructions", "")
    # DEPRECATED: cloths_on is no longer used by Vertex AI API
    # Kept for backward compatibility
    cloths_on = vton_serializer.validated_data.get("cloths_on", False)

    # Validate required files
    if not person_image_file and not clothing_image_file:
        return Response({"error": "Both person and clothing images are required."}, status=status.HTTP_400_BAD_REQUEST)
    elif not person_image_file:
        return Response({"error": "Person image is required."}, status=status.HTTP_400_BAD_REQUEST)
    elif not clothing_image_file:
        return Response({"error": "Clothing image is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Create database record
    vton_request = VTONRequest(instructions=instructions, cloths_on=cloths_on, status="pending")

    try:
        # Save uploaded images with unique filenames
        logger.info("Saving uploaded images...")
        person_image_path, person_original_name = FileController.save_uploaded_image(person_image_file, subfolder="uploads", prefix="person")
        clothing_image_path, clothing_original_name = FileController.save_uploaded_image(clothing_image_file, subfolder="uploads", prefix="clothing")

        # Update database record with upload info
        vton_request.person_image = person_image_path
        vton_request.clothing_image = clothing_image_path
        vton_request.person_image_original_name = person_original_name
        vton_request.clothing_image_original_name = clothing_original_name
        vton_request.save()

        logger.info(f"Created VTON request: {vton_request.request_id}")

        save_time = time.time()
        logger.info(f"Image save took: {save_time - start_time:.2f}s")

    except Exception as e:
        logger.error(f"Error saving uploaded images: {str(e)}")
        return Response({"error": f"Failed to save uploaded images: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Process the images and generate the virtual try-on result
    try:
        # Update status to processing
        vton_request.status = "processing"
        vton_request.save()

        processing_start = time.time()
        logger.info(f"Setup took: {processing_start - save_time:.2f}s")

        # DEPRECATED: Log warning if cloths_on is set to True
        # The Vertex AI API handles both scenarios automatically
        if cloths_on:
            logger.warning(
                f"Request {vton_request.request_id}: cloths_on parameter is deprecated. " "Vertex AI Virtual Try-On API automatically handles both scenarios."
            )

        # Convert relative paths to absolute paths for the API
        person_image_absolute_path = os.path.join(settings.MEDIA_ROOT, person_image_path)
        clothing_image_absolute_path = os.path.join(settings.MEDIA_ROOT, clothing_image_path)

        logger.info(f"Processing with absolute paths:")
        logger.info(f"  Person: {person_image_absolute_path}")
        logger.info(f"  Clothing: {clothing_image_absolute_path}")

        # Call the VTON controller with absolute paths
        output_image = vton_controller.generate_virtual_tryon(person_image_absolute_path, clothing_image_absolute_path, instructions, cloths_on)

        processing_end = time.time()
        logger.info(f"VTON API call took: {processing_end - processing_start:.2f}s")

        # Save result image with unique filename
        logger.info(f"Saving result image for request: {vton_request.request_id}")
        result_image_path = FileController.save_pil_image(output_image, subfolder="output", prefix="result")

        # Update database record with result
        vton_request.result_image = result_image_path
        vton_request.status = "completed"
        vton_request.completed_at = timezone.now()
        vton_request.save()

        logger.info(f"Successfully completed VTON request: {vton_request.request_id}")

        # Serialize and return response with public URLs
        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        total_time = time.time() - start_time
        logger.info(f"Total request time: {total_time:.2f}s")

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        # Update status to failed
        vton_request.status = "failed"
        vton_request.error_message = str(e)
        vton_request.save()

        logger.error(f"VTON processing failed for request {vton_request.request_id}: {str(e)}")

        # Return error with partial data (uploaded images still accessible)
        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        return Response(response_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_request_status(request, request_id):
    """
    Get the status and details of a VTON request by its UUID

    Args:
        request_id: UUID of the VTON request

    Returns:
        JSON response with request details including public URLs
    """
    try:
        vton_request = get_object_or_404(VTONRequest, request_id=request_id)

        response_serializer = VTONResponseSerializer(vton_request, context={"request": request})

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error retrieving request {request_id}: {str(e)}")
        return Response({"error": f"Request not found: {str(e)}"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_recent_requests(request):
    """
    List recent VTON requests (optional, for admin/monitoring purposes)

    Query params:
        limit: Number of requests to return (default: 10, max: 100)
        status: Filter by status (pending, processing, completed, failed)
    """
    limit = min(int(request.GET.get("limit", 10)), 100)
    status_filter = request.GET.get("status", None)

    queryset = VTONRequest.objects.all()

    if status_filter and status_filter in ["pending", "processing", "completed", "failed"]:
        queryset = queryset.filter(status=status_filter)

    requests = queryset[:limit]

    response_serializer = VTONResponseSerializer(requests, many=True, context={"request": request})

    return Response(response_serializer.data, status=status.HTTP_200_OK)
