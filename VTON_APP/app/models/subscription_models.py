from django.db import models
from django.contrib.auth.models import User
import uuid
from decimal import Decimal


class SubscriptionPlan(models.Model):
    """Subscription plans for different user tiers"""

    PLAN_TYPE_CHOICES = [
        ("free", "Free"),
        ("basic", "Basic"),
        ("pro", "Professional"),
        ("enterprise", "Enterprise"),
        ("custom", "Custom"),
    ]

    BILLING_CYCLE_CHOICES = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
        ("Custom", "Custom"),
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
