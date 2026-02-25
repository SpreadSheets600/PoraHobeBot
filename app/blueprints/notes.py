from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import requests
import os
import re
from urllib.parse import parse_qs, quote_plus, urlparse

from app.extensions import db
from app.models import Note, NoteType, Subject
from app.utilities.s3 import upload_to_s3, generate_presigned_url

notes_bp = Blueprint("notes", __name__)

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"}
VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "m4v"}
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a", "aac", "flac"}
TEXT_EXTENSIONS = {
    "txt",
    "md",
    "csv",
    "json",
    "log",
    "py",
    "js",
    "ts",
    "html",
    "css",
}
DOC_EXTENSIONS = {"doc", "docx", "ppt", "pptx", "xls", "xlsx"}


def _extract_extension(path_or_url):
    parsed = urlparse(path_or_url or "")
    filename = os.path.basename(parsed.path or path_or_url or "")
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _extract_youtube_embed_url(raw_url):
    try:
        parsed = urlparse(raw_url)
    except Exception:
        return None

    host = parsed.netloc.lower().replace("www.", "").replace("m.", "")
    query = parse_qs(parsed.query)
    path_parts = [p for p in parsed.path.split("/") if p]
    video_id = None
    playlist_id = (query.get("list") or [None])[0]
    start_raw = (query.get("t") or query.get("start") or [None])[0]

    if host == "youtu.be" and path_parts:
        video_id = path_parts[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            video_id = (query.get("v") or [None])[0]
        elif path_parts and path_parts[0] in {"shorts", "embed", "live", "v"}:
            video_id = path_parts[1] if len(path_parts) > 1 else None

    if not video_id and not playlist_id:
        return None

    start_seconds = 0
    if start_raw:
        if str(start_raw).isdigit():
            start_seconds = int(start_raw)
        else:
            match = re.match(
                r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", str(start_raw).strip()
            )
            if match:
                hours = int(match.group(1) or 0)
                minutes = int(match.group(2) or 0)
                seconds = int(match.group(3) or 0)
                start_seconds = (hours * 3600) + (minutes * 60) + seconds

    if video_id:
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        params = []
        if playlist_id:
            params.append(f"list={playlist_id}")
        if start_seconds > 0:
            params.append(f"start={start_seconds}")
        return f"{embed_url}?{'&'.join(params)}" if params else embed_url

    return f"https://www.youtube.com/embed/videoseries?list={playlist_id}"


def _build_preview_data(note):
    if note.original_link:
        external_url = note.link
        youtube_embed = _extract_youtube_embed_url(external_url)
        ext = _extract_extension(external_url)

        if youtube_embed:
            return {"kind": "youtube", "url": external_url, "embed_url": youtube_embed}
        if ext == "pdf":
            return {"kind": "iframe", "url": external_url}
        return {"kind": "external", "url": external_url}

    ext = _extract_extension(note.link)
    file_url = note.presigned_url
    filename = os.path.basename(note.link or "")

    if ext in IMAGE_EXTENSIONS:
        kind = "image"
    elif ext == "pdf":
        kind = "pdf"
    elif ext in VIDEO_EXTENSIONS:
        kind = "video"
    elif ext in AUDIO_EXTENSIONS:
        kind = "audio"
    elif ext in TEXT_EXTENSIONS:
        kind = "text"
    elif ext in DOC_EXTENSIONS:
        kind = "document"
    else:
        kind = "download"

    data = {"kind": kind, "url": file_url, "filename": filename, "ext": ext}
    if kind == "document":
        data["viewer_url"] = (
            f"https://docs.google.com/gview?embedded=1&url={quote_plus(file_url)}"
        )
    return data


@notes_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        subject_id = request.form.get("subject")
        note_type = request.form.get("note_type")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not subject_id:
            return redirect(url_for("notes.upload"))

        if not note_type:
            return redirect(url_for("notes.upload"))

        if not title:
            return redirect(url_for("notes.upload"))

        subject = Subject.query.get(subject_id)
        if not subject:
            return redirect(url_for("notes.upload"))

        note_type_obj = NoteType.query.filter_by(name=note_type).first()
        if not note_type_obj:
            note_type_obj = NoteType(name=note_type)
            db.session.add(note_type_obj)
            db.session.flush()

        created_notes = []

        if note_type == "file":
            files = request.files.getlist("files")
            if not files[0].filename:
                return redirect(url_for("notes.upload"))

            for idx, file in enumerate(files):
                if file.filename:
                    filename = secure_filename(file.filename)
                    s3_key = upload_to_s3(file, filename)

                    note_title = f"{title} - {idx + 1}" if len(files) > 1 else title

                    note = Note(
                        title=note_title,
                        description=description,
                        link=s3_key,
                        original_link=None,
                        note_type_id=note_type_obj.id,
                        subject_id=subject.id,
                        user_id=current_user.id,
                    )
                    db.session.add(note)
                    created_notes.append(note)
        else:
            links = request.form.get("links", "").strip()
            if not links:
                return redirect(url_for("notes.upload"))

            link_list = [l.strip() for l in links.split("\n") if l.strip()]
            for idx, link in enumerate(link_list):
                note_title = f"{title} - {idx + 1}" if len(link_list) > 1 else title

                note = Note(
                    title=note_title,
                    description=description,
                    link=link,
                    original_link=link,
                    note_type_id=note_type_obj.id,
                    subject_id=subject.id,
                    user_id=current_user.id,
                )
                db.session.add(note)
                created_notes.append(note)

        db.session.commit()

        webhook_url = current_app.config.get("DISCORD_WEBHOOK_URL")
        if webhook_url:
            for note in created_notes:
                try:
                    note_url = url_for("notes.preview", id=note.id, _external=True)
                    payload = {
                        "embeds": [
                            {
                                "title": "New Note",
                                "url": note_url,
                                "color": 5814783,
                                "fields": [
                                    {
                                        "name": "Title",
                                        "value": note.title,
                                        "inline": True,
                                    },
                                    {
                                        "name": "Subject",
                                        "value": note.subject.name,
                                        "inline": False,
                                    },
                                    {
                                        "name": "Uploaded By",
                                        "value": note.user.name,
                                        "inline": False,
                                    },
                                ],
                            }
                        ]
                    }
                    requests.post(webhook_url, json=payload, timeout=5)
                except Exception as e:
                    current_app.logger.error(f"Failed to send Discord webhook: {e}")

        return redirect(url_for("notes.list"))

    subjects = Subject.query.all()
    return render_template("upload.html", subjects=subjects)


@notes_bp.route("/list")
@login_required
def list():
    search = request.args.get("search", "").strip()
    subject_id = request.args.get("subject")
    note_type_id = request.args.get("note_type")
    user_id = request.args.get("user")
    sort = request.args.get("sort", "newest")

    query = Note.query

    if search:
        query = query.filter(
            or_(Note.title.ilike(f"%{search}%"), Note.description.ilike(f"%{search}%"))
        )

    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    if note_type_id:
        query = query.filter_by(note_type_id=note_type_id)

    if user_id:
        query = query.filter_by(user_id=user_id)

    if sort == "oldest":
        query = query.order_by(Note.created_at.asc())
    elif sort == "title":
        query = query.order_by(Note.title.asc())
    else:
        query = query.order_by(Note.created_at.desc())

    notes = query.all()

    for note in notes:
        if note.link and not note.original_link:
            note.presigned_url = generate_presigned_url(note.link)
        else:
            note.presigned_url = note.link

    subjects = Subject.query.all()
    note_types = NoteType.query.all()

    return render_template(
        "notes_list.html",
        notes=notes,
        subjects=subjects,
        note_types=note_types,
        search=search,
        selected_subject=subject_id,
        selected_note_type=note_type_id,
        selected_user=user_id,
        selected_sort=sort,
    )


@notes_bp.route("/preview/<int:id>")
@login_required
def preview(id):
    note = Note.query.get_or_404(id)

    if note.link and not note.original_link:
        note.presigned_url = generate_presigned_url(note.link, expiration=3600)
    else:
        note.presigned_url = note.link

    preview_data = _build_preview_data(note)
    return render_template("note_preview.html", note=note, preview=preview_data)


@notes_bp.route("/share/<int:id>")
@login_required
def share(id):
    note = Note.query.get_or_404(id)
    share_url = url_for("notes.preview", id=note.id, _external=True)
    return render_template("note_share.html", note=note, share_url=share_url)


@notes_bp.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    note = Note.query.get_or_404(id)

    if note.user_id != current_user.id:
        return redirect(url_for("notes.my_notes"))

    if request.method == "POST":
        subject_id = request.form.get("subject")
        note_type_name = request.form.get("note_type", "").strip()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        external_link = request.form.get("external_link", "").strip()

        if not subject_id or not note_type_name or not title:
            return redirect(url_for("notes.edit", id=note.id))

        subject = Subject.query.get(subject_id)
        if not subject:
            return redirect(url_for("notes.edit", id=note.id))

        note_type_obj = NoteType.query.filter_by(name=note_type_name).first()
        if not note_type_obj:
            note_type_obj = NoteType(name=note_type_name)
            db.session.add(note_type_obj)
            db.session.flush()

        note.title = title
        note.description = description or None
        note.subject_id = subject.id
        note.note_type_id = note_type_obj.id

        if note.original_link is not None and external_link:
            note.link = external_link
            note.original_link = external_link

        db.session.commit()
        return redirect(url_for("notes.preview", id=note.id))

    subjects = Subject.query.order_by(Subject.name.asc()).all()
    note_types = NoteType.query.order_by(NoteType.name.asc()).all()
    return render_template(
        "note_edit.html",
        note=note,
        subjects=subjects,
        note_types=note_types,
    )


@notes_bp.route("/my-notes")
@login_required
def my_notes():
    notes = (
        Note.query.filter_by(user_id=current_user.id)
        .order_by(Note.created_at.desc())
        .all()
    )

    for note in notes:
        if note.link and not note.original_link:
            note.presigned_url = generate_presigned_url(note.link)
        else:
            note.presigned_url = note.link

    return render_template("my_notes.html", notes=notes)


@notes_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    note = Note.query.get_or_404(id)

    if note.user_id != current_user.id:
        return redirect(url_for("notes.my_notes"))

    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("notes.my_notes"))


@notes_bp.route("/activity")
@login_required
def activity():
    recent_notes = Note.query.order_by(Note.created_at.desc()).limit(20).all()
    return render_template("activity.html", recent_notes=recent_notes)
