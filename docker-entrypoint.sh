#!/bin/sh
set -e

mkdir -p instance

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    flask db upgrade
fi

exec gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-7860} "app:create_app()"
