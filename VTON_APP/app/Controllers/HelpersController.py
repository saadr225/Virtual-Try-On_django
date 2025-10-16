import os
import uuid
from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
from io import BytesIO


class URLHelper:
    def __init__(self) -> None:
        pass

    def convert_to_public_url(file_path: str) -> str:
        """
        Convert a file path to a public URL.

        Args:
            file_path (str): The file path to convert.

        Returns:
            str: The public URL.
        """
        # If it's already a URL, return it as-is
        if file_path.startswith("http"):
            return file_path

        # Handle path normalization to avoid issues with relative paths
        # Make sure the path is absolute
        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)

        relative_path = os.path.normpath(os.path.relpath(file_path, settings.MEDIA_ROOT))
        return f"{settings.HOST_URL}{settings.MEDIA_URL}{relative_path.replace(os.sep, '/')}"


class FileController:
    def __init__(self) -> None:
        pass

    @staticmethod
    def generate_unique_filename(original_filename, prefix=""):
        """
        Generate a unique filename using UUID and timestamp
        Format: prefix_YYYYMMDD_HHMMSS_uuid_original_ext

        Args:
            original_filename: Original name of the file
            prefix: Optional prefix (e.g., 'person', 'clothing', 'result')

        Returns:
            Unique filename string
        """
        # Get file extension
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = ".png"  # Default extension

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate short UUID (first 8 characters)
        unique_id = str(uuid.uuid4())[:8]

        # Construct filename
        if prefix:
            filename = f"{prefix}_{timestamp}_{unique_id}{ext}"
        else:
            filename = f"{timestamp}_{unique_id}{ext}"

        return filename

    @staticmethod
    def save_uploaded_image(uploaded_file, subfolder="uploads", prefix=""):
        """
        Save an uploaded file with a unique name

        Args:
            uploaded_file: Django UploadedFile object
            subfolder: Subdirectory within MEDIA_ROOT (default: 'uploads')
            prefix: Optional prefix for filename

        Returns:
            Tuple of (relative_path, original_filename)
        """
        original_filename = uploaded_file.name
        unique_filename = FileController.generate_unique_filename(original_filename, prefix)
        relative_path = os.path.join(subfolder, unique_filename)

        # Save the file
        saved_path = default_storage.save(relative_path, uploaded_file)

        return saved_path, original_filename

    @staticmethod
    def save_pil_image(pil_image, subfolder="output", prefix="result", format="PNG"):
        """
        Save a PIL Image object with a unique name

        Args:
            pil_image: PIL Image object
            subfolder: Subdirectory within MEDIA_ROOT (default: 'output')
            prefix: Optional prefix for filename
            format: Image format (default: 'PNG')

        Returns:
            Relative path of the saved image
        """
        # Generate unique filename
        unique_filename = FileController.generate_unique_filename(f"image.{format.lower()}", prefix)
        relative_path = os.path.join(subfolder, unique_filename)

        # Convert PIL Image to bytes
        buffer = BytesIO()
        pil_image.save(buffer, format=format)
        buffer.seek(0)

        # Save using Django's storage system
        saved_path = default_storage.save(relative_path, ContentFile(buffer.read()))

        return saved_path

    @staticmethod
    def delete_file(file_path):
        """
        Safely delete a file from storage

        Args:
            file_path: Relative path to the file

        Returns:
            Boolean indicating success
        """
        try:
            if file_path and default_storage.exists(file_path):
                default_storage.delete(file_path)
                return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
        return False


class VTONRequestHelper:
    """
    Helper class for VTONRequest-related operations
    """

    @staticmethod
    def get_person_image_url(vton_request, request=None):
        """
        Get the full public URL for the person image

        Args:
            vton_request: VTONRequest instance
            request: Django request object for building absolute URI (optional)

        Returns:
            Full public URL string or None
        """
        if not vton_request.person_image:
            return None

        relative_url = f"{settings.MEDIA_URL}{vton_request.person_image.name}"

        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    @staticmethod
    def get_clothing_image_url(vton_request, request=None):
        """
        Get the full public URL for the clothing image

        Args:
            vton_request: VTONRequest instance
            request: Django request object for building absolute URI (optional)

        Returns:
            Full public URL string or None
        """
        if not vton_request.clothing_image:
            return None

        relative_url = f"{settings.MEDIA_URL}{vton_request.clothing_image.name}"

        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    @staticmethod
    def get_result_image_url(vton_request, request=None):
        """
        Get the full public URL for the result image

        Args:
            vton_request: VTONRequest instance
            request: Django request object for building absolute URI (optional)

        Returns:
            Full public URL string or None
        """
        if not vton_request.result_image:
            return None

        relative_url = f"{settings.MEDIA_URL}{vton_request.result_image.name}"

        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    @staticmethod
    def get_all_urls(vton_request, request=None):
        """
        Get all image URLs for a VTON request

        Args:
            vton_request: VTONRequest instance
            request: Django request object for building absolute URI (optional)

        Returns:
            Dictionary with person_image_url, clothing_image_url, and result_image_url
        """
        return {
            "person_image_url": VTONRequestHelper.get_person_image_url(vton_request, request),
            "clothing_image_url": VTONRequestHelper.get_clothing_image_url(vton_request, request),
            "result_image_url": VTONRequestHelper.get_result_image_url(vton_request, request),
        }
