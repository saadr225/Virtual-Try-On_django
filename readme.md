# Summary of Changes and New User Flow

## Overview

We've transformed the API key management system from an automatic approval system to a **request-based approval workflow** with staff role management. Users now must request API key generation access, which staff/admin approves before they can create keys.

---

## New User Flow

### 1. **User Registration & Login**

- Users can register and login normally
- **NEW**: By default, users **cannot** create API keys
- `api_key_generation_enabled` is set to `False` by default in UserData model

### 2. **API Key Request Submission (Client)**

**Endpoint**: `POST /internal/api/api-key-requests/submit/`

Users submit a request containing:

- `business_name` (required)
- `business_email` (required)
- `use_case` (required) - Why they need API access
- `expected_usage` (required) - Estimated monthly requests
- `website` (optional)
- `additional_info` (optional)

**Status**: Request created with `status: "pending"`

### 3. **Request Review (Staff/Admin)**

Staff can view and manage requests through multiple endpoints:

#### View All Requests

**Endpoint**: `GET /internal/api/staff/api-key-requests/`

- Filter by status: `pending`, `approved`, `rejected`
- Pagination support
- Search functionality

#### View Single Request

**Endpoint**: `GET /internal/api/staff/api-key-requests/{request_id}/`

- Detailed view of specific request

### 4. **Request Approval (Staff/Admin)**

**Endpoint**: `POST /internal/api/staff/api-key-requests/{request_id}/approve/`

Staff provides:

- `max_api_keys` - How many keys user can create (default: 3)
- `user_monthly_quota` - Total monthly quota across all keys (default: 10000)
- `payment_date` (optional) - When payment was received
- `payment_proof` (optional) - File attachment of payment receipt
- `admin_notes` (optional) - Internal notes
- `approved_use_case` (optional) - Approved description

**What happens on approval:**

1. Request status → `approved`
2. User's `api_key_generation_enabled` → `True`
3. User's `max_api_keys` set to approved value
4. User's `user_monthly_quota` set to approved value
5. User can now create API keys (within limits)

### 5. **Request Rejection (Staff/Admin)**

**Endpoint**: `POST /internal/api/staff/api-key-requests/{request_id}/reject/`

Staff provides:

- `rejection_reason` (required) - Why request was rejected
- `admin_notes` (optional)

**What happens on rejection:**

1. Request status → `rejected`
2. User cannot create API keys
3. User can submit a new request later

### 6. **API Key Creation (Client - After Approval)**

**Endpoint**: `POST /internal/api/api-keys/create/`

**NEW Validation:**

- ✅ Checks if user is approved (`api_key_generation_enabled = True`)
- ✅ Checks if user hasn't exceeded `max_api_keys` limit
- ✅ Shows helpful error message if not approved

Users can create keys within their approved quota:

```json
{
  "name": "Production API Key"
}
```

### 7. **View Own Request Status (Client)**

**Endpoints**:

- `GET /internal/api/api-key-requests/my-requests/` - List all requests
- `GET /internal/api/api-key-requests/{request_id}/` - View specific request

Users can track their request status and see approval/rejection details.

### 8. **Quota Management (Client)**

**Endpoint**: `GET /internal/api/quota/me/`

**Enhanced Response** now includes:

- `can_create_more` - Tuple: `(boolean, error_message)`
- Shows if user is approved
- Shows remaining quota and key slots

---

## Role System

### 1. **Superuser/Admin**

- Full system access
- Can approve/reject requests
- Can manage all API keys
- Can modify quotas and rate limits
- Can manage staff users

### 2. **Staff User** (NEW)

- Can view pending API key requests
- Can approve/reject requests
- Can set quotas when approving
- **Cannot** manage other staff users (admin only)
- Identified by: `user.is_staff = True` OR `user.is_superuser = True`

### 3. **Regular User**

- Can submit API key requests
- Can view own request history
- Can create API keys (only after approval)
- Can manage own API keys
- Cannot access admin/staff endpoints

---

## New Models

### APIKeyRequest Model

```python
- user: ForeignKey to User
- business_name: CharField
- business_email: EmailField
- use_case: TextField
- expected_usage: TextField
- website: URLField (optional)
- additional_info: TextField (optional)
- status: CharField (pending/approved/rejected)
- admin_notes: TextField
- approved_by: ForeignKey to User (nullable)
- approved_at: DateTimeField
- rejected_by: ForeignKey to User (nullable)
- rejected_at: DateTimeField
- rejection_reason: TextField
- payment_date: DateField (optional)
- payment_proof: FileField (optional)
- approved_use_case: TextField
- max_api_keys: IntegerField
- user_monthly_quota: IntegerField
```

---

## Updated Models

### UserData Model Changes

```python
# NEW Default Values:
api_key_generation_enabled = False  # Changed from True
max_api_keys = 0  # Changed from 3
user_monthly_quota = 0  # Changed from 10000

# NEW Method:
can_create_api_key() -> (bool, str)
# Returns tuple: (can_create, error_message)
```

---

## New Serializers

1. **APIKeyRequestSerializer** - For creating requests
2. **APIKeyRequestListSerializer** - For listing requests
3. **APIKeyRequestDetailSerializer** - For viewing single request
4. **APIKeyRequestApprovalSerializer** - For approving requests
5. **APIKeyRequestRejectionSerializer** - For rejecting requests

---

## New Permissions

### IsStaffUser

- Custom permission class
- Allows staff and admin users
- Used on all staff request management endpoints

**Permission Hierarchy:**

```
Superuser (highest)
  ↓
Admin (user_type = "admin")
  ↓
Staff (is_staff = True)
  ↓
Regular User (lowest)
```

---

## File Changes

### New Files Created:

1. `app/models/api_key_request.py` - APIKeyRequest model
2. `api/internal_api/serializers/api_key_request_serializers.py` - All request serializers
3. `api/internal_api/views/client_api_request_views.py` - Client request endpoints
4. `api/internal_api/views/admin_api_request_views.py` - Staff request management
5. `api/internal_api/urls/client_api_request_urls.py` - Client URL routes
6. `api/internal_api/urls/admin_api_request_urls.py` - Staff URL routes

### Modified Files:

1. `app/models/__init__.py` - Added APIKeyRequest import
2. `app/models/user_data.py` - Updated defaults, added `can_create_api_key()`
3. `api/internal_api/views/client_api_management_views.py` - Added approval check in `create_api_key()`
4. permissions.py - Added `IsStaffUser` permission
5. `api/internal_api/urls/__init__.py` - Added new URL patterns

---

## Error Messages & Response Codes

### New Response Scenarios:

- **Not Approved**: User tries to create key without approval
  - Returns helpful message with instructions to submit request
- **Validation Errors**: Invalid request data

  - Returns field-specific errors

- **Permission Denied**: Regular user tries to access staff endpoints
  - Returns 403 Forbidden

---

## Migration Required

Run these commands to apply changes:

```bash
python manage.py makemigrations
python manage.py migrate
```

This will create the `APIKeyRequest` table and update `UserData` defaults.

---

## Benefits of New System

1. ✅ **Better Control**: Admin approves who gets API access
2. ✅ **Payment Tracking**: Can record payment details
3. ✅ **Audit Trail**: Full history of requests and approvals
4. ✅ **Quota Management**: Set custom limits per user
5. ✅ **Staff Delegation**: Admins can delegate request management to staff
6. ✅ **User Transparency**: Users can track their request status
7. ✅ **Prevents Abuse**: No automatic API key generation
