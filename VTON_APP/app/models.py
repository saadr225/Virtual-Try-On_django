from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib import admin
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _


class UserData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    premium_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)


from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib import admin
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
import uuid
from decimal import Decimal


# ==================== USER & ACCOUNT MODELS ====================


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
    company_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
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
    rate_limit_per_minute = models.IntegerField(default=10)
    rate_limit_per_hour = models.IntegerField(default=100)
    rate_limit_per_day = models.IntegerField(default=1000)
    monthly_quota = models.IntegerField(default=10000, help_text="Monthly request quota")

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


# ==================== STORE & PRODUCT MODELS ====================


class Store(models.Model):
    """Store information for store owners"""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("pending", "Pending Approval"),
        ("suspended", "Suspended"),
        ("closed", "Closed"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="stores")
    store_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Store details
    store_name = models.CharField(max_length=255)
    store_slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="stores/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="stores/banners/", null=True, blank=True)

    # Contact
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    is_verified = models.BooleanField(default=False)

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store"
        verbose_name_plural = "Stores"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["store_slug"]),
        ]

    def __str__(self):
        return self.store_name


# ==================== VTON REQUEST MODELS (Enhanced) ====================


class VTONRequestEnhanced(models.Model):
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


# ==================== SUBSCRIPTION & BILLING MODELS ====================


class SubscriptionPlan(models.Model):
    """Subscription plans for different user tiers"""

    PLAN_TYPE_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Professional"),
        ("enterprise", "Enterprise"),
    ]

    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    plan_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True)

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default="monthly")

    # Limits
    monthly_request_limit = models.IntegerField(default=100)
    api_rate_limit_per_minute = models.IntegerField(default=10)
    max_api_keys = models.IntegerField(default=1)
    max_stores = models.IntegerField(default=1)

    # Features
    features = models.JSONField(default=list, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()}"


class Subscription(models.Model):
    """User subscriptions"""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("past_due", "Past Due"),
        ("suspended", "Suspended"),
    ]

    subscription_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    # Billing
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    next_billing_date = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Usage tracking
    requests_used_this_period = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "current_period_end"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class Invoice(models.Model):
    """Billing invoices"""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    invoice_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invoice_number = models.CharField(max_length=50, unique=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")

    # Amount
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Payment details
    payment_method = models.CharField(max_length=50, blank=True)
    payment_transaction_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Dates
    issue_date = models.DateField()
    due_date = models.DateField()

    # Additional info
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["user", "-issue_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["invoice_number"]),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.username}"


# ==================== USAGE & ANALYTICS MODELS ====================


class APIUsageLog(models.Model):
    """Detailed API usage logging"""

    log_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Request info
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE, related_name="usage_logs")
    vton_request = models.ForeignKey(VTONRequestEnhanced, on_delete=models.SET_NULL, null=True, blank=True, related_name="usage_logs")

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


# ==================== AUDIT & COMPLIANCE MODELS ====================


class AuditLog(models.Model):
    """System-wide audit logging for compliance"""

    ACTION_CHOICES = [
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("access", "Access"),
        ("export", "Export"),
        ("share", "Share"),
    ]

    log_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Actor (who did it)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Action details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100)  # e.g., 'VTONRequest', 'Store', 'Product'
    resource_id = models.CharField(max_length=255)

    # Changes (for updates)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)

    # Additional context
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.resource_type} by {self.user}"


class SystemConfiguration(models.Model):
    """System-wide configuration settings"""

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False, help_text="Sensitive data like API keys")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configurations"
        ordering = ["key"]

    def __str__(self):
        return self.key
