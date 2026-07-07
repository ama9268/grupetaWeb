#!/bin/sh
set -e

# Normalizar a minúsculas: en Dokploy es fácil poner "True"/"TRUE" (estilo
# Python) y la comparación de shell es sensible a mayúsculas. Aceptamos
# true/1/yes en cualquier caja para no saltarnos las migraciones por eso.
RUN_MIGRATIONS_LC=$(echo "${RUN_MIGRATIONS:-}" | tr '[:upper:]' '[:lower:]')
if [ "$RUN_MIGRATIONS_LC" = "true" ] || [ "$RUN_MIGRATIONS_LC" = "1" ] || [ "$RUN_MIGRATIONS_LC" = "yes" ]; then
    echo "RUN_MIGRATIONS=$RUN_MIGRATIONS -> aplicando migraciones..."
    python manage.py migrate --noinput
fi

exec "$@"
