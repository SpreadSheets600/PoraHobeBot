---
title: PoraHobeBot
sdk: docker
app_port: 7860
---

# PoraHobeBot (Hugging Face Space)

Flask application for sharing and organizing notes.

## Environment variables (Space Settings -> Variables and secrets)

- `SECRET_KEY`
- `DATABASE_URL` (recommended: `sqlite:////data/porahobebot.db`)
- `SQLITECLOUD_HOST` (optional alternative to `DATABASE_URL`)
- `SQLITECLOUD_DB_NAME` (optional, default `porahobe`)
- `SQLITECLOUD_API_KEY` (optional alternative to `DATABASE_URL`)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `DISCORD_CLIENT_ID`
- `DISCORD_CLIENT_SECRET`
- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`
- `DISCORD_WEBHOOK_URL`
- `S3_BUCKET_NAME`
- `S3_ENDPOINT`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_KEY`
- `ADMIN_SECRET_CODE`

## Notes

- The app listens on port `7860`.
- Enable Persistent Storage for your Space and keep the database on `/data`.
- If `DATABASE_URL` is unset, the app now auto-uses `/data/porahobebot.db` when `/data` exists.
- Startup includes a one-time copy from legacy paths (`app.db`, `instance/app.db`) into `/data/porahobebot.db` if the `/data` DB is missing.
- If you cannot use Space persistent storage, set `SQLITECLOUD_HOST`, `SQLITECLOUD_DB_NAME`, and `SQLITECLOUD_API_KEY`.
- DB migrations run at startup by default. Set `RUN_MIGRATIONS=0` to skip.
- If `migrations/` is missing, startup falls back to `db.create_all()` by default.
- Set `RUN_CREATE_ALL_IF_NO_MIGRATIONS=0` to disable that fallback.
