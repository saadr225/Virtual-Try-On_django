"""Serializers for client API key management operations."""

from rest_framework import serializers
from app.models import APIKey
from django.utils import timezone
from datetime import timedelta
import secrets
import string


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new API keys."""

    name = serializers.CharField(required=True, max_length=100, help_text="Unique name to identify this API key")
    rate_limit_per_minute = serializers.IntegerField(required=False, min_value=1, help_text="Maximum requests per minute (admin only)")
    rate_limit_per_hour = serializers.IntegerField(required=False, min_value=1, help_text="Maximum requests per hour (admin only)")
    rate_limit_per_day = serializers.IntegerField(required=False, min_value=1, help_text="Maximum requests per day (admin only)")
    monthly_quota = serializers.IntegerField(required=False, min_value=1, help_text="Maximum requests per month (admin only)")
    allowed_domains = serializers.JSONField(required=False, default=list, help_text="List of allowed domains (admin only)")
    allowed_ips = serializers.JSONField(required=False, default=list, help_text="List of allowed IP addresses (admin only)")
    expires_in_days = serializers.IntegerField(required=False, allow_null=True, help_text="Number of days until key expires (null = never expires)")

    class Meta:
        model = APIKey
        fields = [
            "name",
            "rate_limit_per_minute",
            "rate_limit_per_hour",
            "rate_limit_per_day",
            "monthly_quota",
            "allowed_domains",
            "allowed_ips",
            "expires_in_days",
        ]

    def validate_name(self, value):
        """Validate API key name is unique for the user."""
        user = self.context["request"].user
        if APIKey.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("API key name already exists for this user.")
        return value

    def validate_allowed_domains(self, value):
        """Validate allowed_domains is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("allowed_domains must be a list of domain strings.")
        return value

    def validate_allowed_ips(self, value):
        """Validate allowed_ips is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("allowed_ips must be a list of IP addresses.")
        return value

    def validate(self, attrs):
        """Validate rate limits and apply user defaults."""
        user = self.context["request"].user
        from api.internal_api.utils.permissions import is_admin_user
        from app.models import UserData

        # Get or create user data
        user_data, created = UserData.objects.get_or_create(user=user)

        # Check if user can create API key
        can_create, error_msg = user_data.can_create_api_key()
        if not can_create:
            raise serializers.ValidationError(error_msg)

        # Apply defaults from UserData if not admin
        is_admin = is_admin_user(user)

        # Restricted fields that only admins can set
        restricted_fields = ["rate_limit_per_minute", "rate_limit_per_hour", "rate_limit_per_day", "monthly_quota", "allowed_domains", "allowed_ips"]

        # Check if non-admin is trying to set restricted fields
        if not is_admin:
            for field in restricted_fields:
                if field in attrs and attrs[field] is not None and (field not in ["allowed_domains", "allowed_ips"] or attrs[field] != []):
                    raise serializers.ValidationError({field: f"Only admins can set {field}. Contact administrator for assistance."})

            # Non-admin users get defaults from their UserData
            attrs["rate_limit_per_minute"] = user_data.default_rate_limit_per_minute
            attrs["rate_limit_per_hour"] = user_data.default_rate_limit_per_hour
            attrs["rate_limit_per_day"] = user_data.default_rate_limit_per_day
            attrs["monthly_quota"] = user_data.default_monthly_quota
            attrs["allowed_domains"] = []
            attrs["allowed_ips"] = []
        else:
            # Admin can specify custom values, or use defaults
            attrs.setdefault("rate_limit_per_minute", user_data.default_rate_limit_per_minute)
            attrs.setdefault("rate_limit_per_hour", user_data.default_rate_limit_per_hour)
            attrs.setdefault("rate_limit_per_day", user_data.default_rate_limit_per_day)
            attrs.setdefault("monthly_quota", user_data.default_monthly_quota)
            attrs.setdefault("allowed_domains", [])
            attrs.setdefault("allowed_ips", [])

        # Validate rate limits are in sensible order
        per_minute = attrs.get("rate_limit_per_minute")
        per_hour = attrs.get("rate_limit_per_hour")
        per_day = attrs.get("rate_limit_per_day")

        if per_hour < per_minute:
            raise serializers.ValidationError("Hourly limit must be >= minutely limit")
        if per_day < per_hour:
            raise serializers.ValidationError("Daily limit must be >= hourly limit")

        # Validate cumulative quota doesn't exceed user's limit (for non-admins)
        if not is_admin:
            monthly_quota = attrs.get("monthly_quota")
            current_total = sum(key.monthly_quota for key in APIKey.objects.filter(user=user))

            if current_total + monthly_quota > user_data.user_monthly_quota:
                raise serializers.ValidationError(
                    f"Total monthly quota ({current_total + monthly_quota}) would exceed "
                    f"user limit ({user_data.user_monthly_quota}). "
                    f"You have {user_data.user_monthly_quota - current_total} quota remaining."
                )

        return attrs

    def create(self, validated_data):
        """Create API key with generated key string."""
        user = self.context["request"].user
        expires_in_days = validated_data.pop("expires_in_days", None)

        # Generate secure API key
        api_key_string = self._generate_api_key()

        # Calculate expiration date if specified
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timedelta(days=expires_in_days)

        api_key = APIKey.objects.create(user=user, api_key=api_key_string, expires_at=expires_at, **validated_data)

        return api_key

    @staticmethod
    def _generate_api_key(length=32):
        """Generate a secure API key string."""
        alphabet = string.ascii_letters + string.digits
        return "sk_" + "".join(secrets.choice(alphabet) for _ in range(length))


class APIKeyListSerializer(serializers.ModelSerializer):
    """Serializer for listing API keys (sensitive data masked)."""

    api_key = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            "key_id",
            "name",
            "api_key",
            "status",
            "rate_limit_per_minute",
            "rate_limit_per_hour",
            "rate_limit_per_day",
            "monthly_quota",
            "created_at",
            "last_used_at",
            "expires_at",
            "is_expired",
        ]
        read_only_fields = ["key_id", "created_at", "last_used_at", "expires_at", "is_expired"]

    def get_api_key(self, obj):
        """Return masked API key for security."""
        if obj.api_key:
            key = obj.api_key
            return f"{key[:7]}...{key[-4:]}"
        return None

    def get_is_expired(self, obj):
        """Check if API key has expired."""
        if obj.expires_at:
            return obj.expires_at <= timezone.now()
        return False


class APIKeyDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed API key information (full key on creation only)."""

    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            "key_id",
            "name",
            "api_key",
            "status",
            "rate_limit_per_minute",
            "rate_limit_per_hour",
            "rate_limit_per_day",
            "monthly_quota",
            "allowed_domains",
            "allowed_ips",
            "created_at",
            "last_used_at",
            "expires_at",
            "is_expired",
            "days_until_expiry",
            "is_active",
        ]
        read_only_fields = ["key_id", "api_key", "created_at", "last_used_at", "is_expired", "days_until_expiry", "is_active"]

    def get_is_expired(self, obj):
        """Check if API key has expired."""
        if obj.expires_at:
            return obj.expires_at <= timezone.now()
        return False

    def get_days_until_expiry(self, obj):
        """Calculate days until expiry."""
        if obj.expires_at:
            delta = obj.expires_at - timezone.now()
            days = delta.days
            return max(0, days)
        return None

    def get_is_active(self, obj):
        """Check if API key is active and not expired."""
        is_expired = self.get_is_expired(obj)
        return obj.status == "active" and not is_expired


class APIKeyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating API key settings."""

    rate_limit_per_minute = serializers.IntegerField(required=False, min_value=1)
    rate_limit_per_hour = serializers.IntegerField(required=False, min_value=1)
    rate_limit_per_day = serializers.IntegerField(required=False, min_value=1)
    monthly_quota = serializers.IntegerField(required=False, min_value=1)
    allowed_domains = serializers.JSONField(required=False)
    allowed_ips = serializers.JSONField(required=False)
    status = serializers.ChoiceField(choices=["active", "inactive", "suspended"], required=False)

    class Meta:
        model = APIKey
        fields = ["name", "status", "rate_limit_per_minute", "rate_limit_per_hour", "rate_limit_per_day", "monthly_quota", "allowed_domains", "allowed_ips"]
        read_only_fields = ["name"]

    def validate_allowed_domains(self, value):
        """Validate allowed_domains is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("allowed_domains must be a list of domain strings.")
        return value

    def validate_allowed_ips(self, value):
        """Validate allowed_ips is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("allowed_ips must be a list of IP addresses.")
        return value

    def validate(self, attrs):
        """Validate rate limits are sensible and check permissions."""
        from api.internal_api.utils.permissions import is_admin_user

        user = self.context["request"].user
        is_admin = is_admin_user(user)
        obj = self.instance

        # Restricted fields that only admins can modify
        restricted_fields = ["rate_limit_per_minute", "rate_limit_per_hour", "rate_limit_per_day", "monthly_quota", "allowed_domains", "allowed_ips"]

        # Check if non-admin is trying to modify restricted fields
        if not is_admin:
            for field in restricted_fields:
                if field in attrs:
                    raise serializers.ValidationError({field: f"Only admins can modify {field}. Contact administrator to change rate limits and restrictions."})

        # Validate rate limit hierarchy if they're being changed
        per_minute = attrs.get("rate_limit_per_minute", obj.rate_limit_per_minute)
        per_hour = attrs.get("rate_limit_per_hour", obj.rate_limit_per_hour)
        per_day = attrs.get("rate_limit_per_day", obj.rate_limit_per_day)

        if per_hour < per_minute:
            raise serializers.ValidationError("Hourly limit must be >= minutely limit")
        if per_day < per_hour:
            raise serializers.ValidationError("Daily limit must be >= hourly limit")

        return attrs

    def update(self, instance, validated_data):
        """Update API key settings."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class APIKeyRegenerateSerializer(serializers.Serializer):
    """Serializer for regenerating API keys."""

    confirm = serializers.BooleanField(required=True, help_text="Must be true to confirm regeneration")

    def validate_confirm(self, value):
        """Ensure confirmation is true."""
        if not value:
            raise serializers.ValidationError("Regeneration must be confirmed with confirm=true.")
        return value


class APIKeyStatsSerializer(serializers.Serializer):
    """Serializer for API key usage statistics."""

    key_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    total_requests = serializers.IntegerField(read_only=True)
    requests_this_month = serializers.IntegerField(read_only=True)
    requests_this_day = serializers.IntegerField(read_only=True)
    quota_remaining = serializers.IntegerField(read_only=True)
    last_used_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
