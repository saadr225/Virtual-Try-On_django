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

    # API Key Management Settings (Admin-controlled)
    max_api_keys = models.IntegerField(default=5, help_text="Maximum number of API keys user can create")
    api_key_generation_enabled = models.BooleanField(default=True, help_text="Whether user can generate new API keys")

    # User-Level Quota Settings (Admin-controlled)
    user_monthly_quota = models.IntegerField(default=1000, help_text="Total monthly quota across all user's API keys")

    # Default Rate Limits for New API Keys (Admin-controlled)
    default_rate_limit_per_minute = models.IntegerField(default=100, help_text="Default per-minute rate limit for new API keys")
    default_rate_limit_per_hour = models.IntegerField(default=1000, help_text="Default per-hour rate limit for new API keys")
    default_rate_limit_per_day = models.IntegerField(default=10000, help_text="Default per-day rate limit for new API keys")
    default_monthly_quota = models.IntegerField(default=500, help_text="Default monthly quota for new API keys")

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

    def get_cumulative_monthly_quota_used(self):
        """Calculate total monthly quota used across all user's API keys."""
        from django.utils import timezone
        from app.models import APIUsageLog

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Count all requests from this user's API keys this month
        total_usage = APIUsageLog.objects.filter(api_key__user=self.user, timestamp__gte=month_start).count()

        return total_usage

    def get_remaining_user_quota(self):
        """Get remaining monthly quota for the user."""
        used = self.get_cumulative_monthly_quota_used()
        return max(0, self.user_monthly_quota - used)

    def can_create_api_key(self):
        """Check if user can create a new API key."""
        if not self.api_key_generation_enabled:
            return False, "API key generation is disabled for your account"

        from app.models import APIKey

        current_count = APIKey.objects.filter(user=self.user).count()

        if current_count >= self.max_api_keys:
            return False, f"Maximum API key limit reached ({self.max_api_keys})"

        return True, None


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
