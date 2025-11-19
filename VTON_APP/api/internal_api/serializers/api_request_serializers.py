"""Serializers for API key request/ticket system."""

from rest_framework import serializers
from app.models import APIKeyRequest, APIKey, UserData
from django.contrib.auth.models import User
from django.utils import timezone


class APIKeyRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for users to submit API key requests."""

    requested_key_name = serializers.CharField(required=True, max_length=100, help_text="Name for the requested API key")
    reason = serializers.CharField(required=True, help_text="Reason for requesting an API key")
    intended_use = serializers.CharField(required=False, allow_blank=True, help_text="Description of intended use")
    requested_rate_limit_per_minute = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text="Requested per-minute rate limit (optional suggestion)"
    )
    requested_rate_limit_per_hour = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text="Requested per-hour rate limit (optional suggestion)"
    )
    requested_rate_limit_per_day = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, help_text="Requested per-day rate limit (optional suggestion)"
    )
    requested_monthly_quota = serializers.IntegerField(required=False, allow_null=True, min_value=1, help_text="Requested monthly quota (optional suggestion)")

    class Meta:
        model = APIKeyRequest
        fields = [
            "requested_key_name",
            "reason",
            "intended_use",
            "requested_rate_limit_per_minute",
            "requested_rate_limit_per_hour",
            "requested_rate_limit_per_day",
            "requested_monthly_quota",
        ]

    def validate_requested_key_name(self, value):
        """Validate that the user doesn't already have a key with this name."""
        user = self.context["request"].user

        # Check if user already has an API key with this name
        if APIKey.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("You already have an API key with this name.")

        # Check if user has a pending request with this name
        if APIKeyRequest.objects.filter(user=user, requested_key_name=value, status="pending").exists():
            raise serializers.ValidationError("You already have a pending request for an API key with this name.")

        return value

    def validate(self, attrs):
        """Validate the request."""
        # Validate rate limit hierarchy if provided
        per_minute = attrs.get("requested_rate_limit_per_minute")
        per_hour = attrs.get("requested_rate_limit_per_hour")
        per_day = attrs.get("requested_rate_limit_per_day")

        if all([per_minute, per_hour, per_day]):
            if per_hour < per_minute:
                raise serializers.ValidationError("Requested hourly limit must be >= requested minutely limit")
            if per_day < per_hour:
                raise serializers.ValidationError("Requested daily limit must be >= requested hourly limit")

        return attrs

    def create(self, validated_data):
        """Create the API key request."""
        user = self.context["request"].user
        request = APIKeyRequest.objects.create(user=user, status="pending", **validated_data)
        return request


class APIKeyRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing API key requests (user view)."""

    user = serializers.CharField(source="user.username", read_only=True)
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)

    class Meta:
        model = APIKeyRequest
        fields = [
            "request_id",
            "user",
            "requested_key_name",
            "reason",
            "status",
            "created_at",
            "reviewed_at",
            "reviewed_by",
        ]
        read_only_fields = fields


class APIKeyRequestDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed API key request information (user view)."""

    user = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    generated_api_key_id = serializers.UUIDField(source="generated_api_key.key_id", read_only=True, allow_null=True)
    generated_api_key_name = serializers.CharField(source="generated_api_key.name", read_only=True, allow_null=True)

    class Meta:
        model = APIKeyRequest
        fields = [
            "request_id",
            "user",
            "user_email",
            "requested_key_name",
            "reason",
            "intended_use",
            "status",
            "requested_rate_limit_per_minute",
            "requested_rate_limit_per_hour",
            "requested_rate_limit_per_day",
            "requested_monthly_quota",
            "approved_rate_limit_per_minute",
            "approved_rate_limit_per_hour",
            "approved_rate_limit_per_day",
            "approved_monthly_quota",
            "approved_expires_in_days",
            "rejection_reason",
            "created_at",
            "updated_at",
            "reviewed_at",
            "reviewed_by",
            "generated_api_key_id",
            "generated_api_key_name",
        ]
        read_only_fields = fields


class APIKeyRequestAdminListSerializer(serializers.ModelSerializer):
    """Serializer for admin to list API key requests."""

    user = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)

    class Meta:
        model = APIKeyRequest
        fields = [
            "request_id",
            "user",
            "user_email",
            "user_id",
            "requested_key_name",
            "reason",
            "status",
            "created_at",
            "reviewed_at",
            "reviewed_by",
            "payment_date",
            "payment_amount",
        ]
        read_only_fields = fields


class APIKeyRequestAdminDetailSerializer(serializers.ModelSerializer):
    """Serializer for admin to view detailed API key request."""

    user = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    reviewed_by = serializers.CharField(source="reviewed_by.username", read_only=True, allow_null=True)
    generated_api_key_id = serializers.UUIDField(source="generated_api_key.key_id", read_only=True, allow_null=True)

    class Meta:
        model = APIKeyRequest
        fields = [
            "request_id",
            "user",
            "user_email",
            "user_id",
            "requested_key_name",
            "reason",
            "intended_use",
            "status",
            "requested_rate_limit_per_minute",
            "requested_rate_limit_per_hour",
            "requested_rate_limit_per_day",
            "requested_monthly_quota",
            "approved_rate_limit_per_minute",
            "approved_rate_limit_per_hour",
            "approved_rate_limit_per_day",
            "approved_monthly_quota",
            "approved_expires_in_days",
            "payment_date",
            "payment_amount",
            "payment_proof",
            "admin_notes",
            "rejection_reason",
            "created_at",
            "updated_at",
            "reviewed_at",
            "reviewed_by",
            "generated_api_key_id",
            "metadata",
        ]
        read_only_fields = fields


class APIKeyRequestApprovalSerializer(serializers.Serializer):
    """Serializer for admin to approve API key requests."""

    payment_date = serializers.DateField(required=True, help_text="Date when payment was received")
    payment_amount = serializers.DecimalField(required=True, max_digits=10, decimal_places=2, min_value=0, help_text="Payment amount received")
    payment_proof = serializers.FileField(required=False, allow_null=True, help_text="Payment proof/receipt attachment")
    admin_notes = serializers.CharField(required=False, allow_blank=True, help_text="Internal admin notes")

    # API key settings to grant
    approved_rate_limit_per_minute = serializers.IntegerField(required=True, min_value=1, help_text="Approved per-minute rate limit")
    approved_rate_limit_per_hour = serializers.IntegerField(required=True, min_value=1, help_text="Approved per-hour rate limit")
    approved_rate_limit_per_day = serializers.IntegerField(required=True, min_value=1, help_text="Approved per-day rate limit")
    approved_monthly_quota = serializers.IntegerField(required=True, min_value=1, help_text="Approved monthly quota")
    approved_expires_in_days = serializers.IntegerField(required=False, allow_null=True, min_value=1, help_text="Number of days until key expires (null = never)")

    # User-level settings
    max_api_keys = serializers.IntegerField(required=False, default=5, min_value=1, help_text="Maximum number of API keys user can create")
    user_monthly_quota = serializers.IntegerField(required=False, default=1000, min_value=1, help_text="Total monthly quota across all user's API keys")

    def validate(self, attrs):
        """Validate approval data."""
        # Validate rate limit hierarchy
        per_minute = attrs["approved_rate_limit_per_minute"]
        per_hour = attrs["approved_rate_limit_per_hour"]
        per_day = attrs["approved_rate_limit_per_day"]

        if per_hour < per_minute:
            raise serializers.ValidationError("Approved hourly limit must be >= approved minutely limit")
        if per_day < per_hour:
            raise serializers.ValidationError("Approved daily limit must be >= approved hourly limit")

        # Validate payment date is not in the future
        if attrs["payment_date"] > timezone.now().date():
            raise serializers.ValidationError({"payment_date": "Payment date cannot be in the future"})

        return attrs


class APIKeyRequestRejectionSerializer(serializers.Serializer):
    """Serializer for admin to reject API key requests."""

    rejection_reason = serializers.CharField(required=True, help_text="Reason for rejecting the request")
    admin_notes = serializers.CharField(required=False, allow_blank=True, help_text="Internal admin notes")


class APIKeyRequestCancellationSerializer(serializers.Serializer):
    """Serializer for users to cancel their pending requests."""

    confirm = serializers.BooleanField(required=True, help_text="Must be true to confirm cancellation")

    def validate_confirm(self, value):
        """Ensure confirmation is true."""
        if not value:
            raise serializers.ValidationError("Cancellation must be confirmed with confirm=true")
        return value
