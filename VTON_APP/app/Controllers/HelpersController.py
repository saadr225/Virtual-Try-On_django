import os
from django.conf import settings


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
