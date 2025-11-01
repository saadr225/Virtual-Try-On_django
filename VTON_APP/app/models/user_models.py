from django.db import models
from django.contrib.auth.models import User
import uuid


class UserData(models.Model):
    """Extended user profile for customers and store owners"""

    USER_TYPE_CHOICES = [
        ("customer", "Customer"),
        ("store_owner", "Store Owner"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="customer")
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)

    # Contact & Business Info
    phone_number = models.CharField(max_length=20, blank=True)

    # Address
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Account Status
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    suspension_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            models.Index(fields=["user_type", "is_active"]),
            models.Index(fields=["is_premium", "premium_expiry"]),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_user_type_display()})"


class APIKey(models.Model):
    """API keys for store owners to integrate VTON services"""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    key_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    api_key = models.CharField(max_length=255, unique=True, db_index=True)

    # Key details
    name = models.CharField(max_length=100, help_text="Name to identify this key")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Usage limits
    rate_limit_per_minute = models.IntegerField(default=100)
    rate_limit_per_hour = models.IntegerField(default=1000)
    rate_limit_per_day = models.IntegerField(default=10000)
    monthly_quota = models.IntegerField(default=500, help_text="Monthly request quota")

    # Permissions
    allowed_domains = models.JSONField(default=list, blank=True, help_text="Whitelist of allowed domains")
    allowed_ips = models.JSONField(default=list, blank=True, help_text="Whitelist of allowed IP addresses")

    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["api_key"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.username}"
