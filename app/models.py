from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin

from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)


class OAuth(OAuthConsumerMixin, db.Model):
    __table_args__ = (
        db.UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_provider_user"
        ),
    )

    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    provider_user_id = db.Column(db.String(256), nullable=False)

    user = db.relationship(
        User,
        backref=db.backref("oauth_accounts", cascade="all, delete-orphan"),
    )


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    notes = db.relationship("Note", back_populates="subject", lazy=True)


class NoteType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    notes = db.relationship("Note", back_populates="note_type", lazy=True)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    link = db.Column(db.String(500), nullable=True)
    original_link = db.Column(db.String(500), nullable=True)

    note_type_id = db.Column(db.Integer, db.ForeignKey("note_type.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subject.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    created_at = db.Column(
        db.DateTime, nullable=False, default=db.func.current_timestamp()
    )

    user = db.relationship("User", backref=db.backref("notes", lazy=True))
    subject = db.relationship("Subject", back_populates="notes")
    note_type = db.relationship("NoteType", back_populates="notes")
