# One image, one container, the whole application.
#
#   Stage 1 builds the React SPA.
#   Stage 2 installs the Django backend and copies the build in beside it, where WhiteNoise
#           serves the hashed assets and a catch-all view hands deep links to React Router.
#
#   docker build -t library .
#   docker run --rm -p 8000:8000 library
#
# The API lives at /api/v1, the docs at /api/docs, and the SPA at /.

# ---------------------------------------------------------------------------- frontend ---
FROM node:20-alpine AS frontend

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Same-origin in the container: no host or port to bake in.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# ----------------------------------------------------------------------------- backend ---
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./frontend_dist

# Run as an unprivileged user; the SQLite fallback needs a writable working directory.
RUN adduser --disabled-password --gecos "" --uid 10001 library \
    && mkdir -p /app/staticfiles \
    && chown -R library:library /app
USER library

# Baked in so the build never needs the real secret; runtime overrides it from the environment.
RUN DJANGO_SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

COPY --chown=library:library docker/entrypoint.sh /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
