"""Serializers for authentication operations."""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from app.models import UserData


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password], style={"input_type": "password"})
    password2 = serializers.CharField(write_only=True, required=True, style={"input_type": "password"}, label="Confirm Password")
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    # Optional UserData fields
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    user_type = serializers.ChoiceField(choices=UserData.USER_TYPE_CHOICES, default="customer", required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password", "password2", "first_name", "last_name", "phone_number", "user_type"]

    def validate(self, attrs):
        """Validate password confirmation and email uniqueness."""
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # Check if email already exists
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        return attrs

    def create(self, validated_data):
        """Create user and associated UserData profile."""
        # Remove password2 and extra fields
        validated_data.pop("password2")
        phone_number = validated_data.pop("phone_number", "")
        user_type = validated_data.pop("user_type", "customer")

        # Create user
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

        # Create UserData profile
        UserData.objects.create(user=user, user_type=user_type, phone_number=phone_number, is_verified=False, is_premium=False)

        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password."""

    old_password = serializers.CharField(required=True, write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password], style={"input_type": "password"})
    new_password2 = serializers.CharField(required=True, write_only=True, style={"input_type": "password"}, label="Confirm New Password")

    def validate(self, attrs):
        """Validate password confirmation."""
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information."""

    user_type = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    is_premium = serializers.SerializerMethodField()
    premium_expiry = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

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
            "premium_expiry",
            "phone_number",
            "is_admin",
        ]
        read_only_fields = ["id", "username", "date_joined", "last_login", "is_staff", "is_superuser"]

    def get_user_type(self, obj):
        """Get user type from UserData."""
        try:
            return obj.userdata.user_type
        except UserData.DoesNotExist:
            return "customer"

    def get_is_verified(self, obj):
        """Get verification status from UserData."""
        try:
            return obj.userdata.is_verified
        except UserData.DoesNotExist:
            return False

    def get_is_premium(self, obj):
        """Get premium status from UserData."""
        try:
            return obj.userdata.is_premium
        except UserData.DoesNotExist:
            return False

    def get_premium_expiry(self, obj):
        """Get premium expiry from UserData."""
        try:
            return obj.userdata.premium_expiry
        except UserData.DoesNotExist:
            return None

    def get_phone_number(self, obj):
        """Get phone number from UserData."""
        try:
            return obj.userdata.phone_number
        except UserData.DoesNotExist:
            return ""

    def get_is_admin(self, obj):
        """
        Determine if user has admin privileges.

        A user is considered an admin if:
        - is_staff is True (Django staff user)
        - is_superuser is True (Django superuser)
        - user_type is 'admin' in UserData

        Returns:
            bool: True if user has admin privileges
        """
        # Check Django admin status
        if obj.is_staff or obj.is_superuser:
            return True

        # Check user_type in UserData
        try:
            if obj.userdata.user_type == "admin":
                return True
        except UserData.DoesNotExist:
            pass

        return False


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user information."""

    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=20)
    company_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    # Address fields
    address_line1 = serializers.CharField(required=False, allow_blank=True, max_length=255)
    address_line2 = serializers.CharField(required=False, allow_blank=True, max_length=255)
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    state = serializers.CharField(required=False, allow_blank=True, max_length=100)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "company_name", "address_line1", "address_line2", "city", "state", "country", "postal_code"]

    def validate_email(self, value):
        """Validate email uniqueness (excluding current user)."""
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def update(self, instance, validated_data):
        """Update user and UserData fields."""
        # Extract UserData fields
        userdata_fields = {
            "phone_number": validated_data.pop("phone_number", None),
            "company_name": validated_data.pop("company_name", None),
            "address_line1": validated_data.pop("address_line1", None),
            "address_line2": validated_data.pop("address_line2", None),
            "city": validated_data.pop("city", None),
            "state": validated_data.pop("state", None),
            "country": validated_data.pop("country", None),
            "postal_code": validated_data.pop("postal_code", None),
        }

        # Update User fields
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.save()

        # Update or create UserData
        user_data, created = UserData.objects.get_or_create(user=instance)
        for field, value in userdata_fields.items():
            if value is not None:
                setattr(user_data, field, value)
        user_data.save()

        return instance
