from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required
from functools import wraps

from app.extensions import db
from app.models import Note, NoteType, Subject, User

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return redirect(url_for("admin.verify"))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/")
@admin_required
def dashboard():
    users_count = User.query.count()
    notes_count = Note.query.count()
    subjects_count = Subject.query.count()
    note_types_count = NoteType.query.count()
    
    return render_template(
        "admin/dashboard.html",
        users_count=users_count,
        notes_count=notes_count,
        subjects_count=subjects_count,
        note_types_count=note_types_count
    )


@admin_bp.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if code == current_app.config["ADMIN_SECRET_CODE"]:
            current_user.is_admin = True
            db.session.commit()
            return redirect(url_for("admin.dashboard"))
        else:
            pass
    
    return render_template("admin/verify.html")


@admin_bp.route("/subjects")
@admin_required
def subjects():
    subjects = Subject.query.all()
    return render_template("admin/subjects.html", subjects=subjects)


@admin_bp.route("/subjects/add", methods=["POST"])
@admin_required
def add_subject():
    name = request.form.get("name", "").strip()
    if name:
        existing = Subject.query.filter_by(name=name).first()
        if not existing:
            subject = Subject(name=name)
            db.session.add(subject)
            db.session.commit()
        else:
            pass
    return redirect(url_for("admin.subjects"))


@admin_bp.route("/subjects/delete/<int:id>", methods=["POST"])
@admin_required
def delete_subject(id):
    subject = Subject.query.get_or_404(id)
    db.session.delete(subject)
    db.session.commit()
    return redirect(url_for("admin.subjects"))


@admin_bp.route("/note-types")
@admin_required
def note_types():
    note_types = NoteType.query.all()
    return render_template("admin/note_types.html", note_types=note_types)


@admin_bp.route("/note-types/add", methods=["POST"])
@admin_required
def add_note_type():
    name = request.form.get("name", "").strip()
    if name:
        existing = NoteType.query.filter_by(name=name).first()
        if not existing:
            note_type = NoteType(name=name)
            db.session.add(note_type)
            db.session.commit()
        else:
            pass
    return redirect(url_for("admin.note_types"))


@admin_bp.route("/note-types/delete/<int:id>", methods=["POST"])
@admin_required
def delete_note_type(id):
    note_type = NoteType.query.get_or_404(id)
    db.session.delete(note_type)
    db.session.commit()
    return redirect(url_for("admin.note_types"))


@admin_bp.route("/notes")
@admin_required
def notes():
    notes = Note.query.order_by(Note.created_at.desc()).all()
    return render_template("admin/notes.html", notes=notes)


@admin_bp.route("/notes/delete/<int:id>", methods=["POST"])
@admin_required
def delete_note(id):
    note = Note.query.get_or_404(id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("admin.notes"))


@admin_bp.route("/users")
@admin_required
def users():
    users = User.query.all()
    return render_template("admin/users.html", users=users)


@admin_bp.route("/users/toggle-admin/<int:id>", methods=["POST"])
@admin_required
def toggle_admin(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        pass
    else:
        user.is_admin = not user.is_admin
        db.session.commit()
    return redirect(url_for("admin.users"))
