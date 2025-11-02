"""
Admin-specific serializers for managing users and their API key quotas.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from app.models import UserData, APIKey


class UserQuotaSerializer(serializers.ModelSerializer):
    """Serializer for admin to view/update user-level API key quotas."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    user_type = serializers.CharField(read_only=True)
    current_api_keys = serializers.SerializerMethodField()
    cumulative_quota_used = serializers.SerializerMethodField()
    quota_remaining = serializers.SerializerMethodField()

    class Meta:
        model = UserData
        fields = [
            "username",
            "email",
            "user_type",
            "max_api_keys",
            "api_key_generation_enabled",
            "user_monthly_quota",
            "default_rate_limit_per_minute",
            "default_rate_limit_per_hour",
            "default_rate_limit_per_day",
            "default_monthly_quota",
            "current_api_keys",
            "cumulative_quota_used",
            "quota_remaining",
        ]

    def get_current_api_keys(self, obj):
        """Get count of current API keys."""
        return APIKey.objects.filter(user=obj.user).count()

    def get_cumulative_quota_used(self, obj):
        """Get cumulative monthly quota used."""
        return obj.get_cumulative_monthly_quota_used()

    def get_quota_remaining(self, obj):
        """Get remaining quota."""
        return obj.get_remaining_user_quota()


class UserQuotaUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update user-level API key quotas."""

    class Meta:
        model = UserData
        fields = [
            "max_api_keys",
            "api_key_generation_enabled",
            "user_monthly_quota",
            "default_rate_limit_per_minute",
            "default_rate_limit_per_hour",
            "default_rate_limit_per_day",
            "default_monthly_quota",
        ]

    def validate(self, attrs):
        """Validate quota settings."""
        per_minute = attrs.get("default_rate_limit_per_minute", self.instance.default_rate_limit_per_minute)
        per_hour = attrs.get("default_rate_limit_per_hour", self.instance.default_rate_limit_per_hour)
        per_day = attrs.get("default_rate_limit_per_day", self.instance.default_rate_limit_per_day)

        if per_hour < per_minute:
            raise serializers.ValidationError("Hourly limit must be >= minutely limit")
        if per_day < per_hour:
            raise serializers.ValidationError("Daily limit must be >= hourly limit")

        return attrs


class AdminAPIKeyListSerializer(serializers.ModelSerializer):
    """Serializer for admin to list all API keys across all users."""

    username = serializers.CharField(source="user.username", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    api_key_masked = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = [
            "key_id",
            "username",
            "user_email",
            "name",
            "api_key_masked",
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

    def get_api_key_masked(self, obj):
        """Return masked API key."""
        if obj.api_key:
            key = obj.api_key
            return f"{key[:7]}...{key[-4:]}"
        return None

    def get_is_expired(self, obj):
        """Check if API key has expired."""
        from django.utils import timezone

        if obj.expires_at:
            return obj.expires_at <= timezone.now()
        return False


class AdminAPIKeyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for admin to update any API key (full control)."""

    class Meta:
        model = APIKey
        fields = [
            "name",
            "status",
            "rate_limit_per_minute",
            "rate_limit_per_hour",
            "rate_limit_per_day",
            "monthly_quota",
            "allowed_domains",
            "allowed_ips",
        ]

    def validate(self, attrs):
        """Validate settings."""
        obj = self.instance

        per_minute = attrs.get("rate_limit_per_minute", obj.rate_limit_per_minute)
        per_hour = attrs.get("rate_limit_per_hour", obj.rate_limit_per_hour)
        per_day = attrs.get("rate_limit_per_day", obj.rate_limit_per_day)

        if per_hour < per_minute:
            raise serializers.ValidationError("Hourly limit must be >= minutely limit")
        if per_day < per_hour:
            raise serializers.ValidationError("Daily limit must be >= hourly limit")

        return attrs
