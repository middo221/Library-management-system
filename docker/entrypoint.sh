#!/bin/sh
# Wait for the database (when one is configured), migrate, optionally seed, then hand over.
set -e

if [ -n "$DB_HOST" ]; then
  echo "Waiting for database at $DB_HOST:${DB_PORT:-5432} ..."
  attempts=0
  until python -c "
import os, socket, sys
host, port = os.environ['DB_HOST'], int(os.environ.get('DB_PORT', 5432))
sys.exit(0 if socket.socket().connect_ex((host, port)) == 0 else 1)
" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 60 ]; then
      echo "Database did not become reachable in time." >&2
      exit 1
    fi
    sleep 1
  done
fi

echo "Applying migrations ..."
python manage.py migrate --noinput

if [ "$SEED_DEMO_DATA" = "true" ]; then
  echo "Seeding demo data ..."
  python manage.py seed_demo
fi

exec "$@"
