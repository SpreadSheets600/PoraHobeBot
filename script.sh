#!/usr/bin/env bash
set -euo pipefail

APP_MODULE="run.py"
MIGRATION_MESSAGE="Auto Migration Sync"

export OAUTHLIB_INSECURE_TRANSPORT=1

echo "[Script] Ensuring Migrations Are Up To Date ..."
uv run flask --app "$APP_MODULE" db migrate -m "$MIGRATION_MESSAGE"

echo "[Script] Applying Migrations ..."
uv run flask --app "$APP_MODULE" db upgrade

echo "[Script] Starting Development Server ..."
uv run "$APP_MODULE"
