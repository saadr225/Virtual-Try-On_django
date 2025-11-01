from django.db import models
from django.contrib.auth.models import User
from .user_models import APIKey
from .vton_models import VTONRequest
from .store_models import Store
import uuid
from decimal import Decimal


class APIUsageLog(models.Model):
    """Detailed API usage logging"""

    log_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Request info
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, null=True, blank=True, related_name="usage_logs")
    vton_request = models.ForeignKey(VTONRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_logs")

    # Endpoint details
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10)

    # Request metadata
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    request_headers = models.JSONField(default=dict, blank=True)
    request_body_size = models.IntegerField(null=True, blank=True)

    # Response metadata
    response_status_code = models.IntegerField()
    response_body_size = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    # Success/Error
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "API Usage Log"
        verbose_name_plural = "API Usage Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["api_key", "-timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["is_successful", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.response_status_code}"


class DailyUsageStats(models.Model):
    """Aggregated daily usage statistics"""

    stats_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    date = models.DateField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="daily_stats")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name="daily_stats")
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, null=True, blank=True, related_name="daily_stats")

    # Request counts
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)

    # Processing metrics
    avg_processing_time_seconds = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_processing_time_seconds = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Data transfer
    total_data_uploaded_bytes = models.BigIntegerField(default=0)
    total_data_downloaded_bytes = models.BigIntegerField(default=0)

    # Costs (if tracking)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daily Usage Stats"
        verbose_name_plural = "Daily Usage Stats"
        ordering = ["-date"]
        unique_together = [["date", "user", "store", "api_key"]]
        indexes = [
            models.Index(fields=["date", "user"]),
            models.Index(fields=["date", "store"]),
            models.Index(fields=["date", "api_key"]),
        ]

    def __str__(self):
        target = self.user or self.store or self.api_key
        return f"Stats for {target} on {self.date}"
