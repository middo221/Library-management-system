"""Local development settings.

Defaults to SQLite so a fresh clone runs without Postgres; set ``DB_ENGINE`` (or run
docker compose) to use Postgres instead.
"""

from decouple import config

from .base import *
from .base import BASE_DIR, REST_FRAMEWORK

DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = ["*"]

if config("DB_ENGINE", default="") == "":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

CORS_ALLOW_ALL_ORIGINS = True

# Manifest storage requires collectstatic, which is noise in development.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"anon": "1000/hour", "user": "10000/hour", "auth": "60/min"},
}
