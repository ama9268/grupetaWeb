#!/bin/sh
set -e

if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "RUN_MIGRATIONS=true -> aplicando migraciones..."
    python manage.py migrate --noinput
fi

exec "$@"
