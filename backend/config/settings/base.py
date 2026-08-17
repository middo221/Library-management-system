"""Settings shared by every environment.

Environment-specific overrides live in ``local.py`` and ``production.py``.
Nothing secret belongs in this file — read it from the environment instead.
"""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --------------------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "domains.common",
    "domains.accounts",
    "domains.catalog",
    "domains.circulation",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --------------------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.postgresql"),
        "NAME": config("DB_NAME", default="library"),
        "USER": config("DB_USER", default="library"),
        "PASSWORD": config("DB_PASSWORD", default="library"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# The container image drops the built SPA here. When it exists, WhiteNoise serves the
# hashed asset files and a catch-all view hands every other path to the client router, so
# one container serves the whole application. In local development this directory is absent
# and the Vite dev server takes that job instead.
FRONTEND_DIST = Path(config("FRONTEND_DIST", default=str(BASE_DIR / "frontend_dist")))
if FRONTEND_DIST.is_dir():
    WHITENOISE_ROOT = FRONTEND_DIST
    WHITENOISE_INDEX_FILE = True

# --------------------------------------------------------------------------------------
# DRF
# --------------------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "domains.common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "EXCEPTION_HANDLER": "domains.common.handlers.domain_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_ANON", default="100/hour"),
        "user": config("THROTTLE_USER", default="1000/hour"),
        "auth": config("THROTTLE_AUTH", default="5/min"),
    },
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "SIGNING_KEY": config("JWT_SIGNING_KEY", default=SECRET_KEY),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Library Management System API",
    "DESCRIPTION": "Circulation, catalogue and membership API. All errors use a single envelope.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "CopyStatus": "domains.catalog.models.COPY_STATUS_CHOICES",
        "ReservationStatus": "domains.circulation.models.RESERVATION_STATUS_CHOICES",
        "FineReason": "domains.circulation.models.FINE_REASON_CHOICES",
        "UserRole": "domains.accounts.models.USER_ROLE_CHOICES",
    },
}

# --------------------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = False

# --------------------------------------------------------------------------------------
# Circulation policy — every number the services depend on lives here, not inline.
# --------------------------------------------------------------------------------------

CIRCULATION = {
    "MAX_ACTIVE_LOANS": config("MAX_ACTIVE_LOANS", default=5, cast=int),
    "LOAN_PERIOD_DAYS": config("LOAN_PERIOD_DAYS", default=14, cast=int),
    "MAX_RENEWALS": config("MAX_RENEWALS", default=2, cast=int),
    "OVERDUE_FINE_PER_DAY": Decimal(config("OVERDUE_FINE_PER_DAY", default="0.50")),
    "DEFAULT_REPLACEMENT_COST": Decimal(config("DEFAULT_REPLACEMENT_COST", default="30.00")),
    "HOLD_SHELF_DAYS": config("HOLD_SHELF_DAYS", default=3, cast=int),
    "UNPAID_FINE_BLOCK_THRESHOLD": Decimal(config("UNPAID_FINE_BLOCK_THRESHOLD", default="10.00")),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {"handlers": ["console"], "level": config("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "library": {
            "level": config("LOG_LEVEL", default="INFO"),
            "handlers": ["console"],
            "propagate": False,
        },
    },
}
