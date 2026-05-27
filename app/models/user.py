from datetime import datetime
from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    real_name = db.Column(db.String(100), nullable=True)
    discord_id = db.Column(db.String(100), nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    rodo_consent = db.Column(db.Boolean, default=False, nullable=False)

    profile = db.relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )
    user_games = db.relationship(
        "UserGame",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    sent_invitations = db.relationship(
        "Invitation",
        foreign_keys="Invitation.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    received_invitations = db.relationship(
        "Invitation",
        foreign_keys="Invitation.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan"
    )
    sent_messages= db.relationship(
        "Message",
        foreign_keys="Message.sender_id",
        back_populates="sender",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    received_messages = db.relationship(
        "Message",
        foreign_keys="Message.receiver_id",
        back_populates="receiver",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    given_ratings = db.relationship(
        "TrustRating",
        foreign_keys="TrustRating.rater_id",
        back_populates="rater",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    received_ratings = db.relationship(
        "TrustRating",
        foreign_keys="TrustRating.rated_user_id",
        back_populates="rated_user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    trust_score = db.relationship(
        "TrustScore",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select"
    )

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "real_name": self.real_name,
            "discord_id": self.discord_id,
            "registration_date": self.registration_date.isoformat() if self.registration_date else None,
            "is_verified": self.is_verified
        }