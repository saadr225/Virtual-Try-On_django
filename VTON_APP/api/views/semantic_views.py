from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, parser_classes
from django.http import HttpResponse
from rest_framework.response import Response
from api.serializers import VTONSerializer
from VTON_APP.app.Controllers.VTONController import VTONController
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from PIL import Image
import os

vton_controller = VTONController(os.getenv("GOOGLE_GENAI_API_KEY"))
vton_serializer = VTONSerializer()


# Create your views here.
@api_view(["POST"])
@permission_classes([AllowAny])
def virtual_tryon(request):
    """
    Handle virtual try-on requests by processing uploaded images and generating the output.
    """
    vton_serializer = VTONSerializer(data=request.data)
    if not vton_serializer.is_valid():
        return Response(vton_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    person_image_file = vton_serializer.validated_data.get("person_image")
    clothing_image_file = vton_serializer.validated_data.get("clothing_image")
    instructions = vton_serializer.validated_data.get("instructions", "")

    if not person_image_file and not clothing_image_file:
        return Response({"error": "Both person and clothing images are required."}, status=status.HTTP_400_BAD_REQUEST)
    elif not person_image_file:
        return Response({"error": "Person image is required."}, status=status.HTTP_400_BAD_REQUEST)
    elif not clothing_image_file:
        return Response({"error": "Clothing image is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Convert uploaded files to PIL Images
    try:
        person_image = Image.open(person_image_file)
        clothing_image = Image.open(clothing_image_file)
    except Exception as e:
        return Response({"error": f"Invalid image format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # Process the images and generate the virtual try-on result
    try:
        output_image = vton_controller.generate_virtual_tryon(person_image, clothing_image, instructions)
        response = HttpResponse(content_type="image/png")
        output_image.save(response, "PNG")
        return response
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
