from django.db import models
from django.contrib.auth.models import User
from .store_models import Store
from .user_models import APIKey
import uuid
from decimal import Decimal


class VTONRequest(models.Model):
    """Enhanced VTON request with full tracking"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    SOURCE_CHOICES = [
        ("web", "Web Interface"),
        ("api", "API"),
        ("mobile", "Mobile App"),
    ]

    # Request identification
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # User & Store info
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="vton_requests")
    store = models.ForeignKey(Store, on_delete=models.SET_NULL, null=True, blank=True, related_name="vton_requests")
    api_key = models.ForeignKey(APIKey, on_delete=models.SET_NULL, null=True, blank=True, related_name="vton_requests")

    # Request source
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="web")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)

    # Images
    person_image = models.FileField(upload_to="vton/uploads/", max_length=512)
    clothing_image = models.FileField(upload_to="vton/uploads/", max_length=512)
    result_image = models.FileField(upload_to="vton/output/", max_length=512, null=True, blank=True)

    person_image_original_name = models.CharField(max_length=256)
    clothing_image_original_name = models.CharField(max_length=256)

    # Image metadata
    person_image_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")
    clothing_image_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")
    result_image_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")

    # Processing details
    instructions = models.TextField(blank=True, default="")
    cloths_on = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")

    # Processing metrics
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_duration_seconds = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Quality metrics (if available from API)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Result tracking
    is_saved = models.BooleanField(default=False, help_text="User saved the result")
    is_shared = models.BooleanField(default=False, help_text="Result was shared")

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "VTON Request"
        verbose_name_plural = "VTON Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["store", "-created_at"]),
            models.Index(fields=["api_key", "-created_at"]),
        ]

    def __str__(self):
        return f"VTON Request {self.request_id} - {self.status}"
