from datetime import datetime
from app import db


class Invitation(db.Model):
    __tablename__ = "invitations"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    game_id = db.Column(
        db.Integer,
        db.ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False
    )

    message = db.Column(db.String(500), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"

    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_invitations"
    )
    receiver = db.relationship(
        "User",
        foreign_keys=[receiver_id],
        back_populates="received_invitations"
    )
    game = db.relationship("Game", back_populates="invitations")

    def __repr__(self):
        return f"<Invitation {self.sender_id}->{self.receiver_id} [{self.status}]>"

    def to_dict(self):
        return{
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_nickname": self.sender.profile.nickname if self.sender and self.sender.profile else None,
            "receiver_id": self.receiver_id,
            "receiver_nickname": self.receiver.profile.nickname if self.receiver and self.receiver.profile else None,
            "game_id": self.game_id,
            "game_name": self.game.name if self.game else None,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }