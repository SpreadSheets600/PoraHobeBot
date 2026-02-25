import os
from urllib.parse import parse_qs, urlparse, urlunparse


def _normalize_sqlitecloud_uri(raw_uri):
    uri = (raw_uri or "").strip()
    if not uri:
        return ""

    # If a malformed value includes extra text before sqlitecloud://, keep only
    # the driver URL portion.
    idx = uri.find("sqlitecloud://")
    if idx > 0:
        uri = uri[idx:]

    if not uri.startswith("sqlitecloud://"):
        return uri

    parsed = urlparse(uri)
    query = parse_qs(parsed.query)

    # Some copied strings accidentally place the actual URL in the apikey query.
    apikey_values = query.get("apikey", [])
    if apikey_values and apikey_values[0].startswith("sqlitecloud://"):
        nested = apikey_values[0]
        nested_idx = nested.find("sqlitecloud://")
        if nested_idx >= 0:
            return _normalize_sqlitecloud_uri(nested[nested_idx:])

    db_name = os.environ.get("SQLITECLOUD_DB_NAME", "").strip()
    path = parsed.path or ""
    if path in ("", "/") and db_name:
        path = f"/{db_name}"

    return urlunparse(
        (parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment)
    )


def _default_database_uri():
    explicit = os.environ.get("DATABASE_URL")
    if explicit:
        return _normalize_sqlitecloud_uri(explicit)

    sqlitecloud_host = os.environ.get("SQLITECLOUD_HOST", "").strip()
    sqlitecloud_api_key = os.environ.get("SQLITECLOUD_API_KEY", "").strip()
    sqlitecloud_db_name = os.environ.get("SQLITECLOUD_DB_NAME", "porahobe").strip()
    if sqlitecloud_host and sqlitecloud_api_key:
        host = sqlitecloud_host.replace("sqlitecloud://", "").replace("https://", "")
        host = host.split("?")[0].split("/")[0].split(":443")[0]
        return f"sqlitecloud://{host}:8860/{sqlitecloud_db_name}?apikey={sqlitecloud_api_key}"

    if os.path.isdir("/data"):
        # Hugging Face Spaces persistent volume.
        return "sqlite:////data/porahobebot.db"

    # Local/dev fallback.
    return "sqlite:///instance/app.db"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"

    SQLALCHEMY_DATABASE_URI = _default_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google OAuth
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")

    # Discord OAuth
    DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
    DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
    DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID")
    DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

    # S3 Storage Configuration
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT")
    S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID")

    # Admin
    ADMIN_SECRET_CODE = os.environ.get("ADMIN_SECRET_CODE") or "admin123"
