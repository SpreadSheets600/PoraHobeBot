import os
from werkzeug.utils import secure_filename
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    send_from_directory,
    flash,
    render_template,
)
import requests
import sqlite3

from utils.database import get_note_by_id, update_note

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "docx",
    "pptx",
    "txt",
    "zip",
    "rar",
    "csv",
    "xlsx",
    "mp4",
    "mp3",
}
DB_PATH = "notes.db"
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")  # Set this in your .env

SUBJECT_CHANNELS = {
    "c": 1387809784031608994,
    "dsa": 1387809822279208990,
    "math": 1387810459930988687,
    "python": 1387809701865197689,
    "economics": 1387810261527691344,
    "electronics": 1387810558153068594,
    "computer organization": 1387810527983567040,
}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "supersecretkey"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_note_to_db(title, file_url, channel_id, user_id, subject):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    import datetime

    timestamp = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO notes (title, content, file_url, channel_id, user_id, timestamp, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, "", file_url, str(channel_id), str(user_id), timestamp, subject),
    )
    conn.commit()
    conn.close()


def send_to_discord_channel(subject, file_url, filename, user_id=None):
    channel_id = SUBJECT_CHANNELS.get(subject.lower())
    if not channel_id:
        return False

    content = f"📄 Note Uploaded For **{subject.title()}**: [Download here]({file_url})"
    if user_id:
        content += f"\nUploaded by: <@{user_id}>"

    data = {"content": content}

    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json=data)

    return True


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        subject = request.form.get("subject", "").strip().lower()
        user_id = request.form.get("user_id", "").strip() or None
        file = request.files.get("file")

        if not subject or subject not in SUBJECT_CHANNELS:
            flash("Invalid or missing subject.")
            return redirect(request.url)

        if not file or file.filename == "":
            flash("No file selected.")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("File type not allowed.")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(save_path)
        file_url = url_for("uploaded_file", filename=filename, _external=True)

        save_note_to_db(
            filename, file_url, SUBJECT_CHANNELS[subject], user_id or "web", subject
        )
        send_to_discord_channel(subject, file_url, filename, user_id)
        flash("File uploaded and sent to Discord!")
        return redirect(request.url)
    return render_template_string(
        """
        <h2>Upload Note</h2>
        <form method=post enctype=multipart/form-data>
          Subject: <input name=subject required> (e.g. math, dsa, etc.)<br>
          Discord User ID (optional): <input name=user_id><br>
          File: <input type=file name=file required><br>
          <input type=submit value=Upload>
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>
          {% endif %}
        {% endwith %}
    """
    )


@app.route("/edit_note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    conn = sqlite3.connect(DB_PATH)
    message = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        file_url = request.form.get("file_url", "").strip()
        tags = request.form.get("tags", "").strip()

        update_note(
            conn, note_id, title=title, content=content, file_url=file_url, tags=tags
        )
        message = "Note updated successfully!"
    note = get_note_by_id(conn, note_id)
    conn.close()
    if not note:
        return render_template_string(
            "<h2>Note not found.</h2><a href='/notes'>Back to Notes List</a>"
        )
    return render_template("edit_note.html", note=note, message=message)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
