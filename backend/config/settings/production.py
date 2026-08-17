"""Production settings. Every secret comes from the environment."""

from decouple import Csv, config

from .base import *

DEBUG = False
SECRET_KEY = config("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
X_FRAME_OPTIONS = "DENY"
