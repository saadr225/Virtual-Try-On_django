from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserData,
    APIKey,
    APIKeyRequest,
    Store,
    VTONRequest,
    SubscriptionPlan,
    Subscription,
    Invoice,
    APIUsageLog,
    DailyUsageStats,
    AuditLog,
    SystemConfiguration,
)


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ["user", "user_type", "is_verified", "is_premium", "is_active", "created_at"]
    list_filter = ["user_type", "is_verified", "is_premium", "is_active", "created_at"]
    search_fields = ["user__username", "user__email", "phone_number"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("User Information", {"fields": ("user", "user_type", "phone_number")}),
        ("Address", {"fields": ("city", "state", "country", "postal_code")}),
        ("Account Status", {"fields": ("is_verified", "is_premium", "premium_expiry", "is_active", "is_suspended", "suspension_reason", "suspended_at")}),
        (
            "API Key Settings",
            {
                "fields": (
                    "max_api_keys",
                    "api_key_generation_enabled",
                    "user_monthly_quota",
                    "default_rate_limit_per_minute",
                    "default_rate_limit_per_hour",
                    "default_rate_limit_per_day",
                    "default_monthly_quota",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_login_at")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
    )


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "status", "created_at", "last_used_at", "expires_at"]
    list_filter = ["status", "created_at", "expires_at"]
    search_fields = ["name", "user__username", "api_key"]
    readonly_fields = ["key_id", "api_key", "created_at", "last_used_at"]

    fieldsets = (
        ("Key Information", {"fields": ("key_id", "api_key", "name", "user", "status")}),
        ("Usage Limits", {"fields": ("rate_limit_per_minute", "rate_limit_per_hour", "rate_limit_per_day", "monthly_quota")}),
        ("Security", {"fields": ("allowed_domains", "allowed_ips")}),
        ("Timestamps", {"fields": ("created_at", "last_used_at", "expires_at")}),
    )


@admin.register(APIKeyRequest)
class APIKeyRequestAdmin(admin.ModelAdmin):
    list_display = ["request_id", "user", "requested_key_name", "status", "created_at", "reviewed_by", "payment_amount"]
    list_filter = ["status", "created_at", "reviewed_at"]
    search_fields = ["request_id", "user__username", "requested_key_name", "reason"]
    readonly_fields = ["request_id", "created_at", "updated_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Request Information", {"fields": ("request_id", "user", "requested_key_name", "reason", "intended_use", "status")}),
        (
            "Requested Settings",
            {
                "fields": (
                    "requested_rate_limit_per_minute",
                    "requested_rate_limit_per_hour",
                    "requested_rate_limit_per_day",
                    "requested_monthly_quota",
                )
            },
        ),
        (
            "Approval Details",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                    "approved_rate_limit_per_minute",
                    "approved_rate_limit_per_hour",
                    "approved_rate_limit_per_day",
                    "approved_monthly_quota",
                    "approved_expires_in_days",
                )
            },
        ),
        ("Payment Information", {"fields": ("payment_date", "payment_amount", "payment_proof", "admin_notes")}),
        ("Rejection Details", {"fields": ("rejection_reason",)}),
        ("Generated API Key", {"fields": ("generated_api_key",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly after creation."""
        readonly = list(self.readonly_fields)
        if obj and obj.status != "pending":
            # Once reviewed, lock the request details
            readonly.extend(["user", "requested_key_name", "reason", "intended_use"])
        return readonly


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ["store_name", "owner", "status", "is_verified", "created_at"]
    list_filter = ["status", "is_verified", "created_at"]
    search_fields = ["store_name", "owner__username", "email"]
    readonly_fields = ["store_id", "created_at", "updated_at"]

    fieldsets = (
        ("Store Information", {"fields": ("store_id", "owner", "store_name", "description")}),
        ("Contact", {"fields": ("email", "phone", "website")}),
        ("Status", {"fields": ("status", "is_verified")}),
        ("Settings", {"fields": ("settings",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(VTONRequest)
class VTONRequestAdmin(admin.ModelAdmin):
    list_display = ["request_id", "user", "store", "status", "source", "created_at", "processing_duration_seconds"]
    list_filter = ["status", "source", "created_at", "is_saved", "is_shared"]
    search_fields = ["request_id", "user__username", "store__store_name", "ip_address"]
    readonly_fields = ["request_id", "created_at", "updated_at", "completed_at", "processing_duration_seconds"]
    date_hierarchy = "created_at"

    fieldsets = (
        ("Request Information", {"fields": ("request_id", "user", "store", "api_key", "source")}),
        ("Request Metadata", {"fields": ("ip_address", "user_agent", "referer")}),
        (
            "Images",
            {
                "fields": (
                    "person_image",
                    "person_image_original_name",
                    "person_image_size",
                    "clothing_image",
                    "clothing_image_original_name",
                    "clothing_image_size",
                    "result_image",
                    "result_image_size",
                )
            },
        ),
        ("Processing", {"fields": ("status", "error_message")}),
        ("Metrics", {"fields": ("processing_started_at", "processing_completed_at", "processing_duration_seconds")}),
        ("Result Tracking", {"fields": ("is_saved", "is_shared")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "completed_at")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ["name", "plan_type", "price", "currency", "billing_cycle", "is_active", "is_featured"]
    list_filter = ["plan_type", "billing_cycle", "is_active", "is_featured"]
    search_fields = ["name", "description"]

    fieldsets = (
        ("Plan Information", {"fields": ("plan_id", "name", "plan_type", "description")}),
        ("Pricing", {"fields": ("price", "currency", "billing_cycle")}),
        ("Limits", {"fields": ("monthly_request_limit", "api_rate_limit_per_minute", "max_api_keys", "max_stores")}),
        ("Features", {"fields": ("features",)}),
        ("Status", {"fields": ("is_active", "is_featured")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "current_period_start", "current_period_end", "requests_used_this_period"]
    list_filter = ["status", "plan", "created_at"]
    search_fields = ["user__username", "subscription_id"]
    readonly_fields = ["subscription_id", "created_at", "updated_at"]
    date_hierarchy = "current_period_end"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "user", "total", "currency", "status", "issue_date", "due_date", "paid_at"]
    list_filter = ["status", "issue_date", "due_date"]
    search_fields = ["invoice_number", "user__username", "payment_transaction_id"]
    readonly_fields = ["invoice_id", "created_at", "updated_at"]
    date_hierarchy = "issue_date"


@admin.register(APIUsageLog)
class APIUsageLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "api_key", "method", "endpoint", "response_status_code", "response_time_ms", "is_successful"]
    list_filter = ["is_successful", "method", "timestamp"]
    search_fields = ["api_key__name", "endpoint", "ip_address"]
    readonly_fields = ["log_id", "timestamp"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False  # Logs are auto-generated


@admin.register(DailyUsageStats)
class DailyUsageStatsAdmin(admin.ModelAdmin):
    list_display = ["date", "user", "store", "total_requests", "successful_requests", "failed_requests", "avg_processing_time_seconds"]
    list_filter = ["date"]
    search_fields = ["user__username", "store__store_name"]
    readonly_fields = ["stats_id", "created_at", "updated_at"]
    date_hierarchy = "date"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "user", "action", "resource_type", "resource_id", "ip_address"]
    list_filter = ["action", "resource_type", "timestamp"]
    search_fields = ["user__username", "resource_id", "description"]
    readonly_fields = ["log_id", "timestamp"]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should never be deleted


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ["key", "description", "is_sensitive", "updated_at", "updated_by"]
    list_filter = ["is_sensitive", "updated_at"]
    search_fields = ["key", "description"]
    readonly_fields = ["created_at", "updated_at"]
