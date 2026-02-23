---
title: PoraHobeBot
sdk: docker
app_port: 7860
---

# PoraHobeBot (Hugging Face Space)

Flask application for sharing and organizing notes.

## Environment variables (Space Settings -> Variables and secrets)

- `SECRET_KEY`
- `DATABASE_URL` (optional, defaults to SQLite)
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
- DB migrations run at startup by default. Set `RUN_MIGRATIONS=0` to skip.
