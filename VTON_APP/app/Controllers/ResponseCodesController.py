"""
Response Code System
-------------------
This file defines all response codes used throughout the application.
These codes are standardized for use in all API responses and serve as documentation
for the API contract.

NAMING CONVENTION:
- Each code consists of a 3-letter prefix followed by a 3-digit number (e.g., SUC001)
- The prefix identifies the category of the code
- The 3-digit number provides unique identification within that category

PREFIX MEANINGS:
SUC - Success codes
AUT - Authentication and authorization related codes
USR - User account management codes
VTN - VTON request processing codes
STR - Store management codes
SUB - Subscription and billing codes
FIL - File and media processing codes
API - API management and integration codes
AUD - Audit and logging codes
SYS - General system and validation codes

MODELS MANAGED:
- UserData: User profiles with roles (customer, store owner, admin)
- APIKey: API keys for store owners
- Store: Store management for store owners
- VTONRequest: Virtual try-on requests with full lifecycle tracking
- SubscriptionPlan: Available subscription tiers
- Subscription: User subscriptions to plans
- Invoice: Billing and payment invoices
- APIUsageLog: Detailed API usage tracking
- DailyUsageStats: Aggregated usage statistics
- AuditLog: System-wide audit trails
- SystemConfiguration: Configuration management
"""

# Success Codes
SUCCESS_CODES = {
    "SUCCESS": {"code": "SUC001", "message": "Request processed successfully."},
    "DATA_RETRIEVED": {"code": "SUC002", "message": "Data retrieved successfully."},
    "RESOURCE_CREATED": {"code": "SUC003", "message": "Resource created successfully."},
    "RESOURCE_UPDATED": {"code": "SUC004", "message": "Resource updated successfully."},
    "RESOURCE_DELETED": {"code": "SUC005", "message": "Resource deleted successfully."},
    "LOGIN_SUCCESS": {"code": "SUC006", "message": "Login successful."},
    "LOGOUT_SUCCESS": {"code": "SUC007", "message": "Logout successful."},
    "EMAIL_VERIFIED": {"code": "SUC008", "message": "Email verified successfully."},
    "PASSWORD_RESET_SENT": {"code": "SUC009", "message": "Password reset email sent successfully."},
    "PASSWORD_RESET_SUCCESS": {"code": "SUC010", "message": "Password reset successfully."},
}

# Authentication and Authorization Error Codes
AUTH_ERROR_CODES = {
    "TOKEN_INVALID_OR_EXPIRED": {"code": "AUT001", "message": "Invalid or expired token."},
    "LOGIN_REQUIRED": {"code": "AUT002", "message": "Authentication required. Please login."},
    "INVALID_CREDENTIALS": {"code": "AUT003", "message": "Invalid email or password."},
    "ACCESS_DENIED": {"code": "AUT004", "message": "You don't have permission to access this resource."},
    "INSUFFICIENT_PERMISSIONS": {"code": "AUT005", "message": "Insufficient permissions for this action."},
    "ACCOUNT_SUSPENDED": {"code": "AUT006", "message": "Your account has been suspended."},
    "SESSION_EXPIRED": {"code": "AUT007", "message": "Your session has expired. Please login again."},
    "UNAUTHORIZED": {"code": "AUT008", "message": "Unauthorized access."},
    "FORBIDDEN": {"code": "AUT009", "message": "You do not have permission to perform this action."},
    "ROLE_REQUIRED": {"code": "AUT010", "message": "Specific role required for this action."},
    "TWO_FACTOR_REQUIRED": {"code": "AUT011", "message": "Two-factor authentication required."},
    "INVALID_OTP": {"code": "AUT012", "message": "Invalid or expired OTP."},
}

# User Account Management Error Codes
USER_ACCOUNT_ERROR_CODES = {
    "USER_NOT_FOUND": {"code": "USR001", "message": "User not found."},
    "USER_CREATION_ERROR": {"code": "USR002", "message": "Error creating user account."},
    "PASSWORD_CHANGE_ERROR": {"code": "USR003", "message": "Error changing password."},
    "OLD_PASSWORD_INCORRECT": {"code": "USR004", "message": "Current password is incorrect."},
    "EMAIL_CHANGE_ERROR": {"code": "USR005", "message": "Error changing email address."},
    "EMAIL_ALREADY_IN_USE": {"code": "USR006", "message": "This email is already registered."},
    "EMAIL_REQUIRED": {"code": "USR007", "message": "Email address is required."},
    "USERNAME_REQUIRED": {"code": "USR008", "message": "Username is required."},
    "PASSWORD_REQUIRED": {"code": "USR009", "message": "Password is required."},
    "PASSWORDS_DONT_MATCH": {"code": "USR010", "message": "Passwords do not match."},
    "USER_DATA_NOT_FOUND": {"code": "USR011", "message": "User profile data not found."},
    "USER_VERIFICATION_REQUIRED": {"code": "USR012", "message": "Please verify your email before proceeding."},
    "USER_NOT_VERIFIED": {"code": "USR013", "message": "User account is not verified."},
    "INVALID_USER_TYPE": {"code": "USR014", "message": "Invalid user type specified."},
    "USER_ACCOUNT_INACTIVE": {"code": "USR015", "message": "User account is inactive."},
    "USER_SUSPENDED": {"code": "USR016", "message": "User account has been suspended."},
    "SUSPENSION_REASON_PROVIDED": {"code": "USR017", "message": "Account suspended."},
    "PREMIUM_EXPIRED": {"code": "USR018", "message": "Premium membership has expired."},
    "INVALID_PHONE_NUMBER": {"code": "USR019", "message": "Invalid phone number format."},
    "PROFILE_UPDATE_ERROR": {"code": "USR020", "message": "Error updating user profile."},
    "ADDRESS_UPDATE_ERROR": {"code": "USR021", "message": "Error updating address information."},
    "USER_QUOTA_EXCEEDED": {"code": "USR022", "message": "User quota limit exceeded."},
    "USER_QUOTA_UPDATE_ERROR": {"code": "USR023", "message": "Error updating user quota settings."},
    "CANNOT_CREATE_API_KEY": {"code": "USR024", "message": "Cannot create API key. Quota or limit exceeded."},
}

# VTON Request Processing Error Codes
VTON_ERROR_CODES = {
    # Status-based errors
    "VTON_REQUEST_NOT_FOUND": {"code": "VTN001", "message": "VTON request not found."},
    "VTON_REQUEST_PENDING": {"code": "VTN002", "message": "VTON request is still pending."},
    "VTON_REQUEST_QUEUED": {"code": "VTN003", "message": "VTON request is queued for processing."},
    "VTON_REQUEST_PROCESSING": {"code": "VTN004", "message": "VTON request is currently being processed."},
    "VTON_REQUEST_COMPLETED": {"code": "VTN005", "message": "VTON request completed successfully."},
    "VTON_REQUEST_FAILED": {"code": "VTN006", "message": "VTON processing failed."},
    "VTON_REQUEST_CANCELLED": {"code": "VTN007", "message": "VTON request was cancelled."},
    "VTON_REQUEST_TIMEOUT": {"code": "VTN008", "message": "VTON processing timed out."},
    # Processing errors
    "VTON_PROCESSING_ERROR": {"code": "VTN009", "message": "Error during VTON processing."},
    "VTON_INVALID_REQUEST": {"code": "VTN010", "message": "Invalid VTON request parameters."},
    "NO_PERSON_DETECTED": {"code": "VTN011", "message": "No person detected in the image."},
    "INVALID_PERSON_IMAGE": {"code": "VTN012", "message": "Person image is invalid or corrupted."},
    "INVALID_CLOTHING_IMAGE": {"code": "VTN013", "message": "Clothing image is invalid or corrupted."},
    # Result errors
    "VTON_RESULT_NOT_READY": {"code": "VTN014", "message": "VTON result is not yet ready."},
    "VTON_RESULT_NOT_FOUND": {"code": "VTN015", "message": "VTON result file not found."},
    "VTON_RESULT_CORRUPTED": {"code": "VTN016", "message": "VTON result is corrupted."},
    # Request lifecycle
    "VTON_CANNOT_CANCEL": {"code": "VTN017", "message": "Cannot cancel request in current state."},
    "VTON_SOURCE_INVALID": {"code": "VTN018", "message": "Invalid request source."},
    "VTON_QUALITY_CHECK_FAILED": {"code": "VTN019", "message": "Result quality check failed."},
}

# File and Media Processing Error Codes
FILE_MEDIA_ERROR_CODES = {
    "FILE_UPLOAD_ERROR": {"code": "FIL001", "message": "Error uploading file."},
    "FILE_DOWNLOAD_ERROR": {"code": "FIL002", "message": "Error downloading file."},
    "FILE_NOT_FOUND": {"code": "FIL003", "message": "File not found."},
    "FILE_IDENTIFIER_REQUIRED": {"code": "FIL004", "message": "File identifier is required."},
    "UNSUPPORTED_FILE_TYPE": {"code": "FIL005", "message": "This file type is not supported."},
    "FILE_SIZE_EXCEEDED": {"code": "FIL006", "message": "File size exceeds maximum allowed size."},
    "FILE_CORRUPTED": {"code": "FIL007", "message": "File is corrupted or invalid."},
    "FILE_DELETE_ERROR": {"code": "FIL008", "message": "Error deleting file."},
    "MEDIA_PROCESSING_ERROR": {"code": "FIL009", "message": "Error processing media file."},
    "FILE_WRITE_ERROR": {"code": "FIL010", "message": "Error writing file to storage."},
    "FILE_READ_ERROR": {"code": "FIL011", "message": "Error reading file from storage."},
    "STORAGE_QUOTA_EXCEEDED": {"code": "FIL012", "message": "Storage quota exceeded."},
    "INVALID_FILE_NAME": {"code": "FIL013", "message": "Invalid file name format."},
    "FILE_EXTENSION_NOT_ALLOWED": {"code": "FIL014", "message": "File extension not allowed."},
    "FILE_TEMPORARILY_UNAVAILABLE": {"code": "FIL015", "message": "File is temporarily unavailable."},
}

# Store Management Error Codes
STORE_ERROR_CODES = {
    # Basic operations
    "STORE_NOT_FOUND": {"code": "STR001", "message": "Store not found."},
    "STORE_CREATION_ERROR": {"code": "STR002", "message": "Error creating store."},
    "STORE_UPDATE_ERROR": {"code": "STR003", "message": "Error updating store."},
    "STORE_DELETE_ERROR": {"code": "STR004", "message": "Error deleting store."},
    # Status-based errors
    "STORE_SUSPENDED": {"code": "STR005", "message": "This store has been suspended."},
    "STORE_CLOSED": {"code": "STR006", "message": "This store has been closed."},
    "STORE_PENDING_APPROVAL": {"code": "STR007", "message": "Store is pending approval."},
    "STORE_NOT_VERIFIED": {"code": "STR008", "message": "Store is not verified."},
    # Operational errors
    "INVALID_STORE_STATUS": {"code": "STR009", "message": "Invalid store status."},
    "STORE_LIMIT_EXCEEDED": {"code": "STR010", "message": "You have reached the maximum number of stores for your plan."},
    "STORE_NAME_REQUIRED": {"code": "STR011", "message": "Store name is required."},
    "STORE_EMAIL_REQUIRED": {"code": "STR012", "message": "Store email is required."},
    "STORE_EMAIL_INVALID": {"code": "STR013", "message": "Invalid store email format."},
    "STORE_PHONE_INVALID": {"code": "STR014", "message": "Invalid store phone number."},
    "STORE_URL_INVALID": {"code": "STR015", "message": "Invalid store website URL."},
    "STORE_SETTINGS_UPDATE_ERROR": {"code": "STR016", "message": "Error updating store settings."},
}

# Subscription and Billing Error Codes
SUBSCRIPTION_ERROR_CODES = {
    # Subscription basic operations
    "SUBSCRIPTION_NOT_FOUND": {"code": "SUB001", "message": "Subscription not found."},
    "SUBSCRIPTION_CREATION_ERROR": {"code": "SUB002", "message": "Error creating subscription."},
    "SUBSCRIPTION_CANCELLATION_ERROR": {"code": "SUB003", "message": "Error cancelling subscription."},
    "SUBSCRIPTION_UPDATE_ERROR": {"code": "SUB004", "message": "Error updating subscription."},
    # Plan errors
    "PLAN_NOT_FOUND": {"code": "SUB005", "message": "Subscription plan not found."},
    "INVALID_PLAN": {"code": "SUB006", "message": "Invalid subscription plan."},
    "PLAN_INACTIVE": {"code": "SUB007", "message": "Selected plan is inactive."},
    # Subscription status errors
    "SUBSCRIPTION_ACTIVE": {"code": "SUB008", "message": "Subscription is already active."},
    "SUBSCRIPTION_EXPIRED": {"code": "SUB009", "message": "Subscription has expired."},
    "SUBSCRIPTION_INACTIVE": {"code": "SUB010", "message": "Subscription is not active."},
    "SUBSCRIPTION_CANCELLED": {"code": "SUB011", "message": "Subscription has been cancelled."},
    "SUBSCRIPTION_PAST_DUE": {"code": "SUB012", "message": "Subscription payment is past due."},
    "SUBSCRIPTION_SUSPENDED": {"code": "SUB013", "message": "Subscription has been suspended."},
    # Quota and limits
    "QUOTA_EXCEEDED": {"code": "SUB014", "message": "You have exceeded your subscription quota."},
    "REQUEST_LIMIT_EXCEEDED": {"code": "SUB015", "message": "Monthly request limit exceeded."},
    "API_KEY_LIMIT_EXCEEDED": {"code": "SUB016", "message": "API key limit exceeded for your plan."},
    "STORE_LIMIT_EXCEEDED": {"code": "SUB017", "message": "Store limit exceeded for your plan."},
    # Billing and payment
    "INVOICE_NOT_FOUND": {"code": "SUB018", "message": "Invoice not found."},
    "INVOICE_CREATION_ERROR": {"code": "SUB019", "message": "Error creating invoice."},
    "PAYMENT_FAILED": {"code": "SUB020", "message": "Payment processing failed."},
    "PAYMENT_PENDING": {"code": "SUB021", "message": "Payment is pending."},
    "PAYMENT_REFUNDED": {"code": "SUB022", "message": "Payment has been refunded."},
    "REFUND_ERROR": {"code": "SUB023", "message": "Error processing refund."},
    # Billing cycle
    "BILLING_CYCLE_INVALID": {"code": "SUB024", "message": "Invalid billing cycle."},
    "RENEWAL_FAILED": {"code": "SUB025", "message": "Subscription renewal failed."},
    "CANNOT_CANCEL_TRIAL": {"code": "SUB026", "message": "Cannot cancel trial subscription."},
}

# General System and Validation Error Codes
GENERAL_ERROR_CODES = {
    # Request validation
    "INVALID_REQUEST": {"code": "SYS001", "message": "Invalid request parameters."},
    "INVALID_DATA_FORMAT": {"code": "SYS002", "message": "Invalid data format."},
    "MISSING_REQUIRED_FIELD": {"code": "SYS003", "message": "Required field is missing."},
    "VALIDATION_ERROR": {"code": "SYS004", "message": "Validation error."},
    # Resource errors
    "NOT_FOUND": {"code": "SYS005", "message": "The requested resource was not found."},
    "RESOURCE_ALREADY_EXISTS": {"code": "SYS006", "message": "Resource already exists."},
    # HTTP errors
    "METHOD_NOT_ALLOWED": {"code": "SYS007", "message": "HTTP method not allowed for this resource."},
    "BAD_REQUEST": {"code": "SYS008", "message": "Bad request."},
    "CONFLICT": {"code": "SYS009", "message": "Resource conflict detected."},
    # Server errors
    "SERVER_ERROR": {"code": "SYS010", "message": "An unexpected server error occurred."},
    "SYSTEM_ERROR": {"code": "SYS010", "message": "An unexpected server error occurred."},  # Alias for SERVER_ERROR
    "DATABASE_ERROR": {"code": "SYS011", "message": "Database operation failed."},
    "SERVICE_UNAVAILABLE": {"code": "SYS012", "message": "Service is temporarily unavailable."},
    # Operational errors
    "TIMEOUT": {"code": "SYS013", "message": "Request timed out."},
    "RATE_LIMIT_EXCEEDED": {"code": "SYS014", "message": "Rate limit exceeded."},
    # Pagination and filtering
    "INVALID_PAGE": {"code": "SYS015", "message": "Invalid page number."},
    "INVALID_PAGE_SIZE": {"code": "SYS016", "message": "Invalid page size."},
    "INVALID_SORT_FIELD": {"code": "SYS017", "message": "Invalid sort field."},
}

# API Key Management Error Codes
APIKEY_ERROR_CODES = {
    # Basic operations
    "API_KEY_NOT_FOUND": {"code": "API001", "message": "API key not found."},
    "API_KEY_INVALID": {"code": "API002", "message": "Invalid API key provided."},
    "API_KEY_EXPIRED": {"code": "API003", "message": "API key has expired."},
    "API_KEY_SUSPENDED": {"code": "API004", "message": "API key has been suspended."},
    "API_KEY_INACTIVE": {"code": "API005", "message": "API key is inactive."},
    # CRUD operations
    "API_KEY_CREATE_ERROR": {"code": "API006", "message": "Error creating API key."},
    "API_KEY_DELETE_ERROR": {"code": "API007", "message": "Error deleting API key."},
    "API_KEY_UPDATE_ERROR": {"code": "API008", "message": "Error updating API key."},
    "API_KEY_FETCH_ERROR": {"code": "API009", "message": "Error fetching API key details."},
    # Request validation
    "API_KEY_MISSING": {"code": "API010", "message": "API key is missing from request headers."},
    "API_KEY_NAME_REQUIRED": {"code": "API011", "message": "API key name is required."},
    "API_KEY_NAME_DUPLICATE": {"code": "API012", "message": "API key name already exists."},
    # Rate limiting
    "API_RATE_LIMIT_EXCEEDED": {"code": "API013", "message": "API rate limit exceeded."},
    "API_RATE_LIMIT_PER_MINUTE": {"code": "API014", "message": "Per-minute rate limit exceeded."},
    "API_RATE_LIMIT_PER_HOUR": {"code": "API015", "message": "Per-hour rate limit exceeded."},
    "API_RATE_LIMIT_PER_DAY": {"code": "API016", "message": "Per-day rate limit exceeded."},
    # Quotas
    "API_MONTHLY_QUOTA_EXCEEDED": {"code": "API017", "message": "Monthly API quota exceeded."},
    "API_QUOTA_RESET_PENDING": {"code": "API018", "message": "Quota will reset on the next billing cycle."},
    # Permissions and access
    "API_PERMISSION_DENIED": {"code": "API019", "message": "API key doesn't have permission for this operation."},
    "API_KEY_LIMIT_REACHED": {"code": "API020", "message": "Maximum API key limit reached for your plan."},
    "API_DOMAIN_NOT_WHITELISTED": {"code": "API021", "message": "Domain not whitelisted for this API key."},
    "API_IP_NOT_WHITELISTED": {"code": "API022", "message": "IP address not whitelisted for this API key."},
    "API_GENERATION_DISABLED": {"code": "API023", "message": "API key generation is disabled for this user."},
    "API_CUMULATIVE_QUOTA_EXCEEDED": {"code": "API024", "message": "Cumulative user quota exceeded. Cannot create more API keys."},
}

# Audit and Logging Error Codes
AUDIT_ERROR_CODES = {
    "AUDIT_LOG_NOT_FOUND": {"code": "AUD001", "message": "Audit log not found."},
    "AUDIT_LOG_FETCH_ERROR": {"code": "AUD002", "message": "Error fetching audit logs."},
    "AUDIT_LOG_CREATE_ERROR": {"code": "AUD003", "message": "Error creating audit log."},
    "SYSTEM_CONFIG_NOT_FOUND": {"code": "AUD004", "message": "System configuration not found."},
    "SYSTEM_CONFIG_UPDATE_ERROR": {"code": "AUD005", "message": "Error updating system configuration."},
    "SENSITIVE_DATA_ACCESS_BLOCKED": {"code": "AUD006", "message": "Access to sensitive data blocked."},
}

# Analytics and Usage Error Codes
ANALYTICS_ERROR_CODES = {
    "USAGE_LOG_NOT_FOUND": {"code": "ANA001", "message": "Usage log not found."},
    "USAGE_STATS_NOT_FOUND": {"code": "ANA002", "message": "Usage statistics not found."},
    "USAGE_STATS_FETCH_ERROR": {"code": "ANA003", "message": "Error fetching usage statistics."},
    "USAGE_STATS_GENERATE_ERROR": {"code": "ANA004", "message": "Error generating usage statistics."},
    "INVALID_DATE_RANGE": {"code": "ANA005", "message": "Invalid date range specified."},
    "DATE_RANGE_REQUIRED": {"code": "ANA006", "message": "Date range is required."},
}

# API Success Codes
API_SUCCESS_CODES = {
    "API_KEY_CREATED": {"code": "API101", "message": "API key created successfully."},
    "API_KEY_DELETED": {"code": "API102", "message": "API key deleted successfully."},
    "API_KEY_FETCHED": {"code": "API103", "message": "API key details fetched successfully."},
    "API_KEYS_FETCHED": {"code": "API104", "message": "API keys fetched successfully."},
    "API_KEY_UPDATED": {"code": "API105", "message": "API key updated successfully."},
    "API_KEY_REGENERATED": {"code": "API106", "message": "API key regenerated successfully."},
    "VTON_REQUEST_SUBMITTED": {"code": "API107", "message": "VTON request submitted successfully."},
    "VTON_REQUEST_QUEUED": {"code": "API108", "message": "VTON request queued successfully."},
    "VTON_RESULT_FETCHED": {"code": "API109", "message": "VTON result fetched successfully."},
    "VTON_REQUESTS_FETCHED": {"code": "API110", "message": "VTON requests fetched successfully."},
    "VTON_STATUS_FETCHED": {"code": "API111", "message": "VTON status fetched successfully."},
    "USAGE_STATS_FETCHED": {"code": "API112", "message": "Usage statistics fetched successfully."},
    "LIST_FETCHED": {"code": "API113", "message": "List fetched successfully."},
    "USER_QUOTA_FETCHED": {"code": "API114", "message": "User quota information fetched successfully."},
    "USER_QUOTA_UPDATED": {"code": "API115", "message": "User quota updated successfully."},
    "USER_SEARCH_COMPLETED": {"code": "API116", "message": "User search completed successfully."},
    "USER_DETAILS_FETCHED": {"code": "API117", "message": "User details fetched successfully."},
}

# API Error Codes
API_ERROR_CODES = {
    "API_VALIDATION_ERROR": {"code": "API200", "message": "Invalid request parameters."},
    "API_UNSUPPORTED_MEDIA_TYPE": {"code": "API201", "message": "Unsupported media type."},
    "API_INTERNAL_ERROR": {"code": "API202", "message": "Internal API error occurred."},
    "API_SERVICE_UNAVAILABLE": {"code": "API203", "message": "API service is temporarily unavailable."},
    "API_TIMEOUT": {"code": "API204", "message": "API request timed out."},
    "API_PAYLOAD_TOO_LARGE": {"code": "API205", "message": "Request payload is too large."},
    "API_MALFORMED_REQUEST": {"code": "API206", "message": "Malformed API request."},
    "API_ENDPOINT_NOT_FOUND": {"code": "API207", "message": "API endpoint not found."},
    "API_VERSION_DEPRECATED": {"code": "API208", "message": "API version is deprecated."},
    "API_MAINTENANCE_MODE": {"code": "API209", "message": "API is in maintenance mode."},
}

# Combine all response codes into one dictionary for lookup
RESPONSE_CODES = {
    **SUCCESS_CODES,
    **AUTH_ERROR_CODES,
    **USER_ACCOUNT_ERROR_CODES,
    **VTON_ERROR_CODES,
    **FILE_MEDIA_ERROR_CODES,
    **STORE_ERROR_CODES,
    **SUBSCRIPTION_ERROR_CODES,
    **GENERAL_ERROR_CODES,
    **APIKEY_ERROR_CODES,
    **AUDIT_ERROR_CODES,
    **ANALYTICS_ERROR_CODES,
    **API_SUCCESS_CODES,
    **API_ERROR_CODES,
}


def get_response_code(code_key: str) -> dict:
    """
    Get response code by key.
    Args:
        code_key (str): Key for response code.
    Returns:
        dict: Response code dictionary.
    """
    if code_key in RESPONSE_CODES:
        return RESPONSE_CODES[code_key]
    else:
        return {"code": "ERR000", "message": "Unknown error code."}
