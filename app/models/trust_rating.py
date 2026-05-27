from datetime import datetime
from app import db


class TrustRating(db.Model):
    __tablename__ = "trust_ratings"

    id = db.Column(db.Integer, primary_key=True)
    rater_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    rated_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    stars = db.Column(db.Integer, nullable=False)  # Can be 1, 2 or 3 stars
    comment = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("rater_id", "rated_user_id", name="uq_rating_pair"),
        db.CheckConstraint("stars >= 1 AND stars <= 3", name="ck_stars_range"),
    )

    STARS_MEANING = {
        1: {"label": "Negative", "color": "red", "description": "Bad experience"},
        2: {"label": "Neutral", "color": "orange", "description": "Average player"},
        3: {"label": "Positive", "color": "green", "description": "Great player, recommended"},
    }

    rater = db.relationship(
        "User",
        foreign_keys=[rater_id],
        back_populates="given_ratings"
    )
    rated_user = db.relationship(
        "User",
        foreign_keys=[rated_user_id],
        back_populates="received_ratings"
    )

    def __repr__(self):
        return f"<TrustRating {self.rater_id}->{self.rated_user_id} [{self.stars}★]>"

    def to_dict(self):
        return {
            "id": self.id,
            "rater_id": self.rater_id,
            "rater_nickname": self.rater.profile.nickname if self.rater and self.rater.profile else "Unknown",
            "rated_user_id": self.rated_user_id,
            "stars": self.stars,
            "stars_info": self.STARS_MEANING.get(self.stars, {}),
            "comment": self.comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
