from django.db import models
from django.contrib.auth.models import User
import uuid


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
    description = models.TextField(blank=True)

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
        ]

    def __str__(self):
        return self.store_name
