from datetime import datetime
from app import db


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE")
    )
    receiver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE")
    )
    content = db.Column(db.String(2000), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_messages"
    )
    receiver = db.relationship(
        "User",
        foreign_keys=[receiver_id],
        back_populates="received_messages"
    )

    def __repr__(self):
        return f"<Message {self.sender_id}->{self.receiver_id} [{self.created_at}]>"

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_nickname": self.sender.profile.nickname if self.sender and self.sender.profile else 'Unknown',
            "sender_avatar": self.sender.profile.avatar_url if self.sender and self.sender.profile else None,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
