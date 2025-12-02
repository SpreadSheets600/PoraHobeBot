from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin

from .extensions import db


class User(UserMixin, db.Model):
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    id = db.Column(db.Integer, primary_key=True)


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
