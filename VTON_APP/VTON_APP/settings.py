from datetime import timedelta
import os
from pathlib import Path
from dotenv import load_dotenv
from app.utils.middleware import RequestLoggingMiddleware

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-ih*8oi)ve^r++cr@-(5n)_y4j=^zf%soxebz+r^xi4+$kt!!f7"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ============================================================================
# Debug Flags - Control verbose logging and debugging features
# ============================================================================
DEBUG_FLAGS = {
    # Middleware Logging
    "LOG_REQUESTS": os.getenv("DEBUG_LOG_REQUESTS", "False") == "True",  # Log all incoming requests
    "LOG_RESPONSES": os.getenv("DEBUG_LOG_RESPONSES", "False") == "True",  # Log all responses
    "LOG_REQUEST_HEADERS": os.getenv("DEBUG_LOG_REQUEST_HEADERS", "False") == "True",  # Log request headers
    "LOG_REQUEST_BODY": os.getenv("DEBUG_LOG_REQUEST_BODY", "False") == "True",  # Log request body
    "LOG_QUERY_PARAMS": os.getenv("DEBUG_LOG_QUERY_PARAMS", "False") == "True",  # Log query parameters
    # Database Logging
    "LOG_DATABASE_QUERIES": os.getenv("DEBUG_LOG_DATABASE_QUERIES", "False") == "True",  # Log all SQL queries
    # API Logging
    "LOG_API_KEY_VALIDATION": os.getenv("DEBUG_LOG_API_KEY_VALIDATION", "False") == "True",  # Log API key validation
    # VTON Processing
    "LOG_VTON_PROCESSING": os.getenv("DEBUG_LOG_VTON_PROCESSING", str(DEBUG)) == "True",  # Log VTON processing details
    # Performance Metrics
    "LOG_PERFORMANCE_METRICS": os.getenv("DEBUG_LOG_PERFORMANCE_METRICS", "False") == "True",  # Log response times
}

# Host URL for generating public URLs (e.g., https://yourdomain.com/)
HOST_URL = os.getenv("HOST_URL", "http://localhost:8000/")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    # User-defined apps
    "app",  # Core business logic & models
    "api.client_api",  # External API for third-party integrations
    "api.internal_api",  # Internal API for frontend
]

MIDDLEWARE = [
    "app.utils.middleware.RequestLoggingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # Keep for Django admin
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",  # Keep for Django admin
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# CORS settings - Allow credentials for JWT tokens in cookies (if needed)
CORS_ALLOW_CREDENTIALS = False  # Set to True only if storing JWT in httpOnly cookies
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",  # Required for JWT Bearer tokens
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-requested-with",
]

CORS_ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_URL"),
    os.environ.get("FRONTEND_URL_WWW"),
]


if os.environ.get("DEBUG"):
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"^null$",
    ]

ROOT_URLCONF = "VTON_APP.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates"), os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "VTON_APP.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "vton_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "your_password"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
        # Add these critical settings:
        "ATOMIC_REQUESTS": True,  # Wrap each request in transaction
        "CONN_HEALTH_CHECKS": True,  # Django 4.1+ - check connection health
    }
}

# Add database connection pooling settings
DATABASES["default"]["OPTIONS"]["keepalives"] = 1
DATABASES["default"]["OPTIONS"]["keepalives_idle"] = 30
DATABASES["default"]["OPTIONS"]["keepalives_interval"] = 10
DATABASES["default"]["OPTIONS"]["keepalives_count"] = 5

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

# Simple JWT settings - Enhanced security configuration
SIMPLE_JWT = {
    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),  # Shorter lifetime for better security
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # 7 days refresh
    # Token rotation and blacklisting
    "ROTATE_REFRESH_TOKENS": True,  # Rotate refresh tokens on use
    "BLACKLIST_AFTER_ROTATION": True,  # Blacklist old tokens after rotation
    "UPDATE_LAST_LOGIN": True,  # Update user's last_login on token generation
    # Algorithm and signing
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    # Token types and claims
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    # Token classes
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    # Security settings
    "JTI_CLAIM": "jti",  # JWT ID claim for blacklisting
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=30),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=7),
    # Token obtain/refresh settings
    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
# Add STATIC_ROOT for production
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Media files (uploaded files(images, videos, etc))
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# WhiteNoise configuration for efficient static and media file serving
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG  # Only auto-refresh in development
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0  # 1 year cache in production
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Stop Django from adding a trailing slash to URLs
APPEND_SLASH = False

# For requests to Vertex AI
REQUESTS_TIMEOUT = 120  # seconds

# Security settings for production
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False  # Don't save on every request

# File upload settings (critical for VTON)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "clean": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
            "datefmt": "%H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "clean",
        },
        "console_verbose": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["require_debug_true"],
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "django.log",
            "formatter": "verbose",
        },
        "file_errors": {
            "class": "logging.FileHandler",
            "filename": "errors.log",
            "formatter": "verbose",
            "level": "ERROR",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Django core loggers
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file_errors"],
            "level": "ERROR",  # Only log request errors
            "propagate": False,
        },
        "django.server": {
            "handlers": [],  # Disable django.server logging (we use our middleware)
            "level": "CRITICAL",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console_verbose"],
            "level": "DEBUG" if DEBUG_FLAGS.get("LOG_DATABASE_QUERIES") else "WARNING",
            "propagate": False,
        },
        # Application loggers
        "api": {
            "handlers": ["console", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "api.client_api": {
            "handlers": ["console", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "api.internal_api": {
            "handlers": ["console", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "app": {
            "handlers": ["console", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        # Middleware loggers
        "app.utils.middleware": {
            "handlers": ["console", "file_errors"],
            "level": "DEBUG" if (DEBUG_FLAGS.get("LOG_REQUESTS") or DEBUG_FLAGS.get("LOG_RESPONSES")) else "INFO",
            "propagate": False,
        },
        "api.client_api.utils.middleware": {
            "handlers": ["console_verbose"] if DEBUG_FLAGS.get("LOG_API_KEY_VALIDATION") else ["console"],
            "level": "DEBUG" if DEBUG_FLAGS.get("LOG_API_KEY_VALIDATION") else "WARNING",
            "propagate": False,
        },
    },
}

# Middleware optimization - add this after MIDDLEWARE definition
MIDDLEWARE_CLASSES = MIDDLEWARE  # For compatibility

# Add caching (critical for performance)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_table",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
            "CULL_FREQUENCY": 3,
        },
    }
}
