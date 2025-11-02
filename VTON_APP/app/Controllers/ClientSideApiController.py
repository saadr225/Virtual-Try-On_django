"""
Client-Side API Controller
Handles all business logic for API key validation, rate limiting, and usage tracking.
"""

from app.models import APIKey, APIUsageLog, DailyUsageStats
from app.Controllers.ResponseCodesController import get_response_code
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class ClientSideApiController:
    """Controller for client API key management and validation."""

    @staticmethod
    def validate_api_key(api_key_string):
        """
        Validate API key and return key object or error response data.

        Args:
            api_key_string (str): The API key string from request header

        Returns:
            tuple: (is_valid: bool, api_key_or_error: APIKey or dict)
        """
        if not api_key_string:
            return False, get_response_code("API_KEY_MISSING")

        try:
            api_key = APIKey.objects.select_related("user").get(api_key=api_key_string)
        except APIKey.DoesNotExist:
            return False, get_response_code("API_KEY_INVALID")

        # Check if key is expired
        if api_key.expires_at and api_key.expires_at <= timezone.now():
            return False, get_response_code("API_KEY_EXPIRED")

        # Check if key is active
        if api_key.status == "suspended":
            return False, get_response_code("API_KEY_SUSPENDED")
        elif api_key.status != "active":
            return False, get_response_code("API_KEY_INACTIVE")

        return True, api_key

    @staticmethod
    def check_domain_whitelist(api_key, domain):
        """
        Check if domain is whitelisted for the API key.

        Args:
            api_key (APIKey): The API key object
            domain (str): The domain to check

        Returns:
            tuple: (is_allowed: bool, error_code: dict or None)
        """
        if api_key.allowed_domains and domain not in api_key.allowed_domains:
            return False, get_response_code("API_DOMAIN_NOT_WHITELISTED")
        return True, None

    @staticmethod
    def check_ip_whitelist(api_key, ip_address):
        """
        Check if IP address is whitelisted for the API key.

        Args:
            api_key (APIKey): The API key object
            ip_address (str): The IP address to check

        Returns:
            tuple: (is_allowed: bool, error_code: dict or None)
        """
        if api_key.allowed_ips and ip_address not in api_key.allowed_ips:
            return False, get_response_code("API_IP_NOT_WHITELISTED")
        return True, None

    @staticmethod
    def check_rate_limits(api_key):
        """
        Check if API key has exceeded any rate limits.

        Args:
            api_key (APIKey): The API key object

        Returns:
            tuple: (is_within_limits: bool, error_code: dict or None)
        """
        cache_prefix = f"api_key_{api_key.key_id}"

        # Check per-minute limit
        minute_count_key = f"{cache_prefix}_minute"
        minute_count = cache.get(minute_count_key, 0)
        if minute_count >= api_key.rate_limit_per_minute:
            return False, get_response_code("API_RATE_LIMIT_PER_MINUTE")

        # Check per-hour limit
        hour_count_key = f"{cache_prefix}_hour"
        hour_count = cache.get(hour_count_key, 0)
        if hour_count >= api_key.rate_limit_per_hour:
            return False, get_response_code("API_RATE_LIMIT_PER_HOUR")

        # Check per-day limit
        day_count_key = f"{cache_prefix}_day"
        day_count = cache.get(day_count_key, 0)
        if day_count >= api_key.rate_limit_per_day:
            return False, get_response_code("API_RATE_LIMIT_PER_DAY")

        # Increment counters
        cache.set(minute_count_key, minute_count + 1, 60)  # 1 minute expiry
        cache.set(hour_count_key, hour_count + 1, 3600)  # 1 hour expiry
        cache.set(day_count_key, day_count + 1, 86400)  # 1 day expiry

        return True, None

    @staticmethod
    def check_monthly_quota(api_key):
        """
        Check if API key has exceeded monthly quota.

        Args:
            api_key (APIKey): The API key object

        Returns:
            tuple: (is_within_quota: bool, error_code: dict or None)
        """
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Count requests this month
        this_month_count = APIUsageLog.objects.filter(api_key=api_key, timestamp__gte=month_start).count()

        if this_month_count >= api_key.monthly_quota:
            return False, get_response_code("API_MONTHLY_QUOTA_EXCEEDED")

        return True, None

    @staticmethod
    def log_api_usage(api_key, request, response):
        """
        Log API usage to database.

        Args:
            api_key (APIKey): The API key object
            request: Django request object
            response: Django response object
        """
        try:
            # Get client IP
            client_ip = ClientSideApiController.get_client_ip(request)

            # Log to APIUsageLog
            APIUsageLog.objects.create(
                api_key=api_key,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=client_ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                request_size=len(request.body) if hasattr(request, "body") else 0,
                response_size=len(response.content) if hasattr(response, "content") else 0,
            )

            # Update or create DailyUsageStats
            today = timezone.now().date()
            daily_stats, created = DailyUsageStats.objects.get_or_create(api_key=api_key, date=today, defaults={"request_count": 0, "error_count": 0})

            daily_stats.request_count += 1
            if response.status_code >= 400:
                daily_stats.error_count += 1
            daily_stats.save()

        except Exception as e:
            logger.error(f"Error logging API usage: {str(e)}")

    @staticmethod
    def update_last_used(api_key):
        """
        Update the last_used_at timestamp for an API key.

        Args:
            api_key (APIKey): The API key object
        """
        try:
            api_key.last_used_at = timezone.now()
            api_key.save(update_fields=["last_used_at"])
        except Exception as e:
            logger.error(f"Error updating last_used_at: {str(e)}")

    @staticmethod
    def get_client_ip(request):
        """
        Extract client IP address from request.

        Args:
            request: Django request object

        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def validate_request(api_key_string, request):
        """
        Complete validation pipeline for an API request.
        Validates key, checks permissions, rate limits, and quotas.

        Args:
            api_key_string (str): The API key from request header
            request: Django request object

        Returns:
            tuple: (is_valid: bool, api_key_or_error: APIKey or dict, http_status: int or None)
        """
        # Validate API key exists and is active
        is_valid, result = ClientSideApiController.validate_api_key(api_key_string)
        if not is_valid:
            return False, result, 401

        api_key = result

        # Check domain whitelist
        domain = request.META.get("HTTP_HOST")
        is_allowed, error = ClientSideApiController.check_domain_whitelist(api_key, domain)
        if not is_allowed:
            return False, error, 403

        # Check IP whitelist
        client_ip = ClientSideApiController.get_client_ip(request)
        is_allowed, error = ClientSideApiController.check_ip_whitelist(api_key, client_ip)
        if not is_allowed:
            return False, error, 403

        # Check rate limits
        is_within_limits, error = ClientSideApiController.check_rate_limits(api_key)
        if not is_within_limits:
            return False, error, 429

        # Check monthly quota
        is_within_quota, error = ClientSideApiController.check_monthly_quota(api_key)
        if not is_within_quota:
            return False, error, 429

        # All checks passed
        return True, api_key, None

    @staticmethod
    def get_usage_statistics(api_key):
        """
        Get usage statistics for an API key.

        Args:
            api_key (APIKey): The API key object

        Returns:
            dict: Usage statistics
        """
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total requests
        total_requests = APIUsageLog.objects.filter(api_key=api_key).count()

        # This month requests
        requests_this_month = APIUsageLog.objects.filter(api_key=api_key, timestamp__gte=month_start).count()

        # Today requests
        requests_today = APIUsageLog.objects.filter(api_key=api_key, timestamp__gte=day_start).count()

        # Quota remaining
        quota_remaining = max(0, api_key.monthly_quota - requests_this_month)

        return {
            "total_requests": total_requests,
            "requests_this_month": requests_this_month,
            "requests_today": requests_today,
            "quota_remaining": quota_remaining,
            "monthly_quota": api_key.monthly_quota,
            "last_used_at": api_key.last_used_at,
            "status": api_key.status,
        }
