import secrets
import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

# from app.models import UserData
from django.utils import timezone


class VTONRequest(models.Model):
    """
    Model to track virtual try-on requests with uploads and results
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # Unique identifier for this request
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # Upload information
    person_image = models.FileField(upload_to="uploads/", max_length=512)
    clothing_image = models.FileField(upload_to="uploads/", max_length=512)
    person_image_original_name = models.CharField(max_length=256)
    clothing_image_original_name = models.CharField(max_length=256)

    # Result information
    result_image = models.FileField(upload_to="output/", max_length=512, null=True, blank=True)

    # Request metadata
    instructions = models.TextField(blank=True, default="")
    cloths_on = models.BooleanField(default=False, help_text="Indicates if the clothing image shows someone wearing the garment")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional user tracking (for future authentication)
    # user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"VTON Request {self.request_id} - {self.status}"


# class MediaUpload(models.Model):
#     user = models.ForeignKey(UserData, on_delete=models.CASCADE)
#     # file = models.FileField(upload_to=f"{settings.MEDIA_ROOT}/submissions", max_length=512)
#     file = models.FileField(upload_to=f"submissions/", max_length=512)
#     original_filename = models.CharField(max_length=256, blank=False)
#     submission_identifier = models.CharField(max_length=128, blank=False)
#     file_identifier = models.CharField(max_length=128, blank=False)
#     file_type = models.CharField(max_length=32, default="Video")
#     purpose = models.CharField(max_length=32, default="Deepfake-Analaysis", blank=False)
#     upload_date = models.DateTimeField(auto_now_add=True)
#     # description = models.TextField(blank=True)

#     def __str__(self):
#         return f"{self.user.username} - {self.file.name} - {self.upload_date}"
