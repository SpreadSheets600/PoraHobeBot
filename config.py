import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///app.db"
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
