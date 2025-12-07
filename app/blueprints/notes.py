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

from app.extensions import db
from app.models import Note, NoteType, Subject
from app.utilities.s3 import upload_to_s3, generate_presigned_url

notes_bp = Blueprint("notes", __name__)


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

    notes = query.order_by(Note.created_at.desc()).all()

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
    )


@notes_bp.route("/preview/<int:id>")
@login_required
def preview(id):
    note = Note.query.get_or_404(id)

    if note.link and not note.original_link:
        note.presigned_url = generate_presigned_url(note.link, expiration=3600)
    else:
        note.presigned_url = note.link

    return render_template("note_preview.html", note=note)


@notes_bp.route("/share/<int:id>")
@login_required
def share(id):
    note = Note.query.get_or_404(id)
    share_url = url_for("notes.preview", id=note.id, _external=True)
    return render_template("note_share.html", note=note, share_url=share_url)


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
