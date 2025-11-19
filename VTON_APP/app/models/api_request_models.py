"""Models for API key request/ticket system."""

from django.db import models
from django.contrib.auth.models import User
import uuid


class APIKeyRequest(models.Model):
    """Requests from users to generate API keys (ticket system)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    # Request identification
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)

    # Requester information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_key_requests")

    # Request details
    requested_key_name = models.CharField(max_length=100, help_text="Name for the requested API key")
    reason = models.TextField(help_text="User's reason for requesting an API key")
    intended_use = models.TextField(blank=True, help_text="Description of how the API key will be used")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)

    # Admin action details
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_api_requests", help_text="Admin/staff who reviewed the request"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, help_text="When the request was reviewed")

    # Payment and approval details (for approved requests)
    payment_date = models.DateField(null=True, blank=True, help_text="Date when payment was received")
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Payment amount received")
    payment_proof = models.FileField(upload_to="api_requests/payment_proofs/", null=True, blank=True, help_text="Payment proof/receipt attachment")
    admin_notes = models.TextField(blank=True, help_text="Internal notes from admin/staff")

    # Rejection details
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection (if rejected)")

    # Generated API key reference (after approval)
    generated_api_key = models.ForeignKey(
        "APIKey", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_request", help_text="The API key created from this request"
    )

    # Requested API key settings (user can suggest, admin decides)
    requested_rate_limit_per_minute = models.IntegerField(null=True, blank=True, help_text="Requested per-minute rate limit")
    requested_rate_limit_per_hour = models.IntegerField(null=True, blank=True, help_text="Requested per-hour rate limit")
    requested_rate_limit_per_day = models.IntegerField(null=True, blank=True, help_text="Requested per-day rate limit")
    requested_monthly_quota = models.IntegerField(null=True, blank=True, help_text="Requested monthly quota")

    # Approved settings (what admin actually grants)
    approved_rate_limit_per_minute = models.IntegerField(null=True, blank=True, help_text="Approved per-minute rate limit")
    approved_rate_limit_per_hour = models.IntegerField(null=True, blank=True, help_text="Approved per-hour rate limit")
    approved_rate_limit_per_day = models.IntegerField(null=True, blank=True, help_text="Approved per-day rate limit")
    approved_monthly_quota = models.IntegerField(null=True, blank=True, help_text="Approved monthly quota")
    approved_expires_in_days = models.IntegerField(null=True, blank=True, help_text="Number of days until key expires (null = never)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional request metadata")

    class Meta:
        verbose_name = "API Key Request"
        verbose_name_plural = "API Key Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["reviewed_by", "-reviewed_at"]),
        ]

    def __str__(self):
        return f"API Key Request #{self.request_id} - {self.user.username} ({self.status})"

    def can_be_approved(self):
        """Check if request can be approved."""
        return self.status == "pending"

    def can_be_rejected(self):
        """Check if request can be rejected."""
        return self.status == "pending"

    def can_be_cancelled(self):
        """Check if request can be cancelled by user."""
        return self.status == "pending"
