# VTON API Structure Documentation

## 📁 New Project Structure

Your Django project now has **nested API apps** for better organization:

```
VTON_APP/
├── app/                          # Core Business Logic
│   ├── models/                   # All data models
│   │   ├── __init__.py
│   │   ├── user_models.py        # UserData, APIKey
│   │   ├── store_models.py       # Store
│   │   ├── vton_models.py        # VTONRequest
│   │   ├── subscription_models.py # SubscriptionPlan, Subscription, Invoice
│   │   ├── analytics_models.py   # APIUsageLog, DailyUsageStats
│   │   └── audit_models.py       # AuditLog, SystemConfiguration
│   ├── Controllers/              # Business logic
│   │   ├── VTONController.py
│   │   └── HelpersController.py
│   └── admin.py                  # Django admin
│
├── api/                          # API Directory (not an app itself)
│   ├── client_api/              # External API (Third-party clients)
│   │   ├── models.py            # VTONRequest (legacy, can be migrated)
│   │   ├── serializers.py       # API request/response serializers
│   │   ├── views/
│   │   │   └── semantic_views.py # VTON endpoints
│   │   ├── urls.py              # URL routing
│   │   └── apps.py              # App config
│   │
│   └── internal_api/            # Internal API (Your frontend)
│       ├── models.py            # VTONRequest (legacy, can be migrated)
│       ├── serializers.py       # Admin serializers
│       ├── views/
│       │   └── semantic_views.py # VTON endpoints
│       ├── urls.py              # URL routing
│       └── apps.py              # App config
│
└── VTON_APP/                    # Project settings
    ├── settings.py
    ├── urls.py
    └── wsgi.py
```

## 🔌 API Endpoints

### External API (client_api) - Third-party Integrations

**Base URL:** `/api/v1/`

| Endpoint                               | Method | Description          |
| -------------------------------------- | ------ | -------------------- |
| `/api/v1/virtual-tryon/process/`       | POST   | Process VTON request |
| `/api/v1/virtual-tryon/<uuid>/status/` | GET    | Get request status   |
| `/api/v1/virtual-tryon/requests/`      | GET    | List recent requests |

**Authentication:** API Key (to be implemented)  
**Rate Limiting:** To be implemented  
**Use Case:** Third-party apps, mobile apps, integrations

### Internal API (internal_api) - Frontend Dashboard

**Base URL:** `/internal/api/`

| Endpoint                                     | Method | Description          |
| -------------------------------------------- | ------ | -------------------- |
| `/internal/api/virtual-tryon/process/`       | POST   | Process VTON request |
| `/internal/api/virtual-tryon/<uuid>/status/` | GET    | Get request status   |
| `/internal/api/virtual-tryon/requests/`      | GET    | List recent requests |

**Authentication:** Django Session/JWT  
**Permissions:** Admin users  
**Use Case:** Your frontend dashboard, admin panel

## ⚙️ Configuration Changes

### settings.py

```python
INSTALLED_APPS = [
    # ...
    "app",                    # Core business logic & models
    "api.client_api",        # External API
    "api.internal_api",      # Internal API
]
```

### urls.py

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("app.urls")),

    # External API - Third-party clients
    path("api/v1/", include("api.client_api.urls")),

    # Internal API - Your frontend
    path("internal/api/", include("api.internal_api.urls")),
]
```

### App Configurations

**client_api/apps.py:**

```python
class ClientApiConfig(AppConfig):
    name = 'api.client_api'
    verbose_name = 'Client API (External)'
```

**internal_api/apps.py:**

```python
class InternalApiConfig(AppConfig):
    name = 'api.internal_api'
    verbose_name = 'Internal API (Frontend)'
```

## 🎯 Import Patterns

### From API Views (Correct)

```python
# In client_api/views/semantic_views.py
from api.client_api.models import VTONRequest
from api.client_api.serializers import VTONSerializer, VTONResponseSerializer
from app.Controllers.VTONController import VTONController
from app.Controllers.HelpersController import FileController
```

### From Core App Models

```python
# In app/Controllers/
from app.models import UserData, Store, VTONRequest, APIKey
```

## 📊 Database Models

All models are centralized in `app/models/`:

- **User Management:** UserData, APIKey
- **Store Management:** Store
- **VTON Requests:** VTONRequest
- **Subscriptions:** SubscriptionPlan, Subscription, Invoice
- **Analytics:** APIUsageLog, DailyUsageStats
- **Audit:** AuditLog, SystemConfiguration

## 🚀 Next Steps

### 1. Consolidate Models (Recommended)

Currently, `VTONRequest` exists in both:

- `api/client_api/models.py`
- `api/internal_api/models.py`
- `app/models/vton_models.py`

**Recommendation:** Keep only `app/models/vton_models.py` and update API apps to import from there.

### 2. Add Authentication

- **client_api:** Implement API key authentication
- **internal_api:** Use Django session/JWT authentication

### 3. Add Rate Limiting

Implement throttling for `client_api` to prevent abuse.

### 4. Add Permissions

Create custom permission classes for each API:

- `client_api/permissions.py` - API key validation
- `internal_api/permissions.py` - Admin/staff permissions

## ✅ Verification

Run these commands to verify everything works:

```bash
# Check for configuration errors
python manage.py check

# Create/apply migrations
python manage.py makemigrations
python manage.py migrate

# Run development server
python manage.py runserver
```

## 🔄 Migration Path

If you want to consolidate models to `app/`:

1. Delete models from `api/client_api/models.py` and `api/internal_api/models.py`
2. Update imports in serializers and views to use `from app.models import VTONRequest`
3. Run `python manage.py makemigrations` and `python manage.py migrate`

## 📝 Benefits of This Structure

✅ **Separation of Concerns:** External vs internal APIs clearly separated  
✅ **Scalability:** Easy to add more API apps  
✅ **Security:** Different authentication for different audiences  
✅ **Maintainability:** Each API has its own namespace  
✅ **Django Standard:** Follows Django's recommended app organization
