#!/bin/sh
set -e

mkdir -p instance

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    if [ -d migrations ]; then
        flask db upgrade
    else
        echo "migrations/ not found, skipping flask db upgrade."
        if [ "${RUN_CREATE_ALL_IF_NO_MIGRATIONS:-1}" = "1" ]; then
            echo "Running db.create_all() fallback."
            python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
        fi
    fi
fi

exec gunicorn --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT:-7860} "app:create_app()"
