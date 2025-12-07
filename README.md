# PoraHobeBot

## Project Overview

PoraHobeBot is a web-based platform designed to facilitate the sharing and management of academic notes and resources. It provides a centralized repository for students to upload, browse, and categorize study materials, streamlining the exchange of knowledge. The application features a modern, responsive user interface and robust administrative tools for content moderation.

## Features

### User Features

- **Authentication**: Secure login and registration system supporting OAuth integration with Google and Discord.
- **Note Management**: Users can upload notes in various formats (files or external links).
- **Resource Organization**: Notes are categorized by subject and type (e.g., Lecture, Assignment, Reference) for easy retrieval.
- **Search and Filter**: Advanced filtering capabilities allow users to find specific resources quickly.
- **Profile Management**: Users can view their upload history and manage connected accounts.

### Administrative Features

- **Dashboard**: A comprehensive overview of platform statistics, including total users, notes, and subjects.
- **Content Moderation**: Tools to review and delete inappropriate or irrelevant notes.
- **Taxonomy Management**: Administrators can create, edit, and remove subjects and note classifications.
- **User Management**: Capabilities to manage user roles and permissions.

## Technical Architecture

The application is built using a monolithic architecture with server-side rendering.

- **Backend**: Python (Flask Framework)
- **Database**: SQLAlchemy ORM (SQLite for development, configurable for other RDBMS)
- **Frontend**: Jinja2 Templates, Tailwind CSS
- **Storage**: S3-compatible object storage for file persistence
- **Authentication**: Flask-Login, Flask-Dance (OAuth)

## Installation and Setup

### Prerequisites

- Python 3.13 or higher
- An S3-compatible storage service (e.g., AWS S3, MinIO, Cloudflare R2)
- Google and/or Discord Developer Application credentials (for OAuth support)

### Step 1: Clone the Repository

```bash
git clone https://github.com/spreadsheets600/porahobebot.git
cd porahobebot
```

### Step 2: Install Dependencies

It is recommended to use a virtual environment.

Using `uv` (recommended):

```bash
uv sync
```

Or using `pip`:

```bash
pip install -r requirements.txt
```

*Note: If `requirements.txt` is missing, generate it from `pyproject.toml` or install dependencies manually as listed in the configuration.*

### Step 3: Configuration

Create a `.env` file in the project root directory. You can copy the structure from the provided configuration parameters.

```env
# Core Security
SECRET_KEY=your_secure_random_key

# Database
DATABASE_URL=sqlite:///app.db

# Authentication (Optional if not using OAuth)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_BOT_TOKEN=your_discord_bot_token

# Storage (S3 Compatible)
S3_BUCKET_NAME=your_bucket_name
S3_ENDPOINT=your_s3_endpoint_url
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_KEY=your_secret_key

# Administration
ADMIN_SECRET_CODE=your_admin_secret_code
```

### Step 4: Initialize the Database

Initialize the database schema and apply migrations.

```bash
flask db upgrade
```

### Step 5: Seed Initial Data (Optional)

Populate the database with initial subjects or required data if a seed script is available.

```bash
python seed_subjects.py
```

### Step 6: Run the Application

Start the development server.

```bash
python run.py
```

The application will be accessible at `http://localhost:5000` (or the configured port).

## Deployment

For production environments, it is recommended to use a production-grade WSGI server such as Gunicorn or uWSGI behind a reverse proxy like Nginx.

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

## License

[Insert License Information Here]

## Contributing

Contributions are welcome. Please submit a pull request or open an issue for any enhancements or bug reports.
