#!/bin/sh
set -e

mkdir -p instance

# One-time migration for Spaces: move legacy ephemeral SQLite DB to persistent /data.
if [ -d "/data" ]; then
    TARGET_DB="/data/porahobebot.db"
    if [ ! -f "$TARGET_DB" ]; then
        for CANDIDATE in "/home/user/app/app.db" "/home/user/app/instance/app.db" "app.db" "instance/app.db"; do
            if [ -f "$CANDIDATE" ]; then
                echo "Migrating legacy database from $CANDIDATE to $TARGET_DB"
                cp "$CANDIDATE" "$TARGET_DB"
                break
            fi
        done
    fi
fi

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
