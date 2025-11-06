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


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for admin to list all users with key information."""

    user_type = serializers.CharField(source="userdata.user_type", read_only=True)
    is_verified = serializers.BooleanField(source="userdata.is_verified", read_only=True)
    is_premium = serializers.BooleanField(source="userdata.is_premium", read_only=True)
    is_suspended = serializers.BooleanField(source="userdata.is_suspended", read_only=True)
    api_key_count = serializers.SerializerMethodField()
    last_login_at = serializers.DateTimeField(source="userdata.last_login_at", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "user_type",
            "is_verified",
            "is_premium",
            "is_suspended",
            "api_key_count",
            "last_login_at",
        ]

    def get_api_key_count(self, obj):
        """Get count of user's API keys."""
        return APIKey.objects.filter(user=obj).count()


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for admin to view complete user information."""

    userdata = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "userdata",
        ]

    def get_userdata(self, obj):
        """Get complete UserData information."""
        try:
            user_data = obj.userdata
            return {
                "user_type": user_data.user_type,
                "is_verified": user_data.is_verified,
                "is_premium": user_data.is_premium,
                "premium_expiry": user_data.premium_expiry,
                "phone_number": user_data.phone_number,
                "city": user_data.city,
                "state": user_data.state,
                "country": user_data.country,
                "postal_code": user_data.postal_code,
                "is_active": user_data.is_active,
                "is_suspended": user_data.is_suspended,
                "suspension_reason": user_data.suspension_reason,
                "suspended_at": user_data.suspended_at,
                "created_at": user_data.created_at,
                "updated_at": user_data.updated_at,
                "last_login_at": user_data.last_login_at,
                "max_api_keys": user_data.max_api_keys,
                "api_key_generation_enabled": user_data.api_key_generation_enabled,
                "user_monthly_quota": user_data.user_monthly_quota,
                "default_rate_limit_per_minute": user_data.default_rate_limit_per_minute,
                "default_rate_limit_per_hour": user_data.default_rate_limit_per_hour,
                "default_rate_limit_per_day": user_data.default_rate_limit_per_day,
                "default_monthly_quota": user_data.default_monthly_quota,
                "metadata": user_data.metadata,
            }
        except UserData.DoesNotExist:
            return None


class AdminUserUpdateSerializer(serializers.Serializer):
    """Serializer for admin to update user information."""

    # User model fields
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)
    is_superuser = serializers.BooleanField(required=False)

    # UserData model fields
    user_type = serializers.ChoiceField(choices=UserData.USER_TYPE_CHOICES, required=False)
    is_verified = serializers.BooleanField(required=False)
    is_premium = serializers.BooleanField(required=False)
    premium_expiry = serializers.DateTimeField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)

    def validate_email(self, value):
        """Validate email uniqueness."""
        user = self.context.get("user")
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, instance, validated_data):
        """Update both User and UserData."""
        # Update User fields
        user_fields = ["email", "first_name", "last_name", "is_active", "is_staff", "is_superuser"]
        for field in user_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

        # Update UserData fields
        userdata_fields = ["user_type", "is_verified", "is_premium", "premium_expiry", "phone_number", "city", "state", "country", "postal_code", "metadata"]
        user_data, created = UserData.objects.get_or_create(user=instance)
        for field in userdata_fields:
            if field in validated_data:
                setattr(user_data, field, validated_data[field])
        user_data.save()

        return instance


class AdminUserSuspendSerializer(serializers.Serializer):
    """Serializer for admin to suspend/unsuspend a user."""

    is_suspended = serializers.BooleanField(required=True)
    suspension_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate suspension data."""
        if attrs.get("is_suspended") and not attrs.get("suspension_reason"):
            raise serializers.ValidationError({"suspension_reason": "Suspension reason is required when suspending a user."})
        return attrs


class AdminUserCreateSerializer(serializers.Serializer):
    """Serializer for admin to create a new user."""

    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    user_type = serializers.ChoiceField(choices=UserData.USER_TYPE_CHOICES, default="customer")
    is_staff = serializers.BooleanField(default=False)
    is_superuser = serializers.BooleanField(default=False)
    is_verified = serializers.BooleanField(default=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create user and UserData."""
        # Extract UserData fields
        user_type = validated_data.pop("user_type", "customer")
        phone_number = validated_data.pop("phone_number", "")
        is_verified = validated_data.pop("is_verified", False)

        # Create User
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_staff=validated_data.get("is_staff", False),
            is_superuser=validated_data.get("is_superuser", False),
        )

        # Create UserData
        UserData.objects.create(
            user=user,
            user_type=user_type,
            phone_number=phone_number,
            is_verified=is_verified,
        )

        return user
