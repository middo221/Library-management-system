"""Test settings — SQLite, fast hashing, throttling off."""

from .base import *
from .base import REST_FRAMEWORK

DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"anon": "10000/hour", "user": "10000/hour", "auth": "10000/hour"},
}
