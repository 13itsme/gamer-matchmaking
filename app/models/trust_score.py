from datetime import datetime
from app import db


class TrustScore(db.Model):
    __tablename__ = "trust_scores"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    total_ratings = db.Column(db.Integer, default=0, nullable=False)
    average_stars = db.Column(db.Float, default=0.0, nullable=False)

    green_count = db.Column(db.Integer, default=0, nullable=False)  # 3 stars
    orange_count = db.Column(db.Integer, default=0, nullable=False)  # 2 stars
    red_count = db.Column(db.Integer, default=0, nullable=False)  # 1 star

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    MIN_RATINGS_TO_SHOW = 5

    user = db.relationship("User", back_populates="trust_score")

    def __repr__(self):
        return f"<TrustScore user={self.user_id} avg={self.average_stars:.1f} [{self.total_ratings} ratings]>"

    def is_visible(self):
        return self.total_ratings >= self.MIN_RATINGS_TO_SHOW

    def recalculate(self):
        from app.models.trust_rating import TrustRating

        ratings = TrustRating.query.filter_by(rated_user_id=self.user_id).all()

        self.total_ratings = len(ratings)
        self.green_count = sum(1 for r in ratings if r.stars == 3)
        self.orange_count = sum(1 for r in ratings if r.stars == 2)
        self.red_count = sum(1 for r in ratings if r.stars == 1)
        self.average_stars = sum(r.stars for r in ratings) / self.total_ratings if ratings else 0.0
        self.updated_at = datetime.utcnow()


    def get_dominant_color(self):

        if not self.is_visible():
            return "unknown"
        if self.green_count >= self.orange_count and self.green_count >= self.red_count:
            return "green"
        elif self.orange_count >= self.red_count:
            return "orange"
        return "red"

    def to_dict(self):
        visible = self.is_visible()
        return {
            "user_id": self.user_id,
            "is_visible": visible,
            "total_ratings": self.total_ratings,
            "average_stars": round(self.average_stars, 2) if visible else None,
            "green_count": self.green_count if visible else None,
            "orange_count": self.orange_count if visible else None,
            "red_count": self.red_count if visible else None,
            "dominant_color": self.get_dominant_color(),
            "min_ratings_needed": max(0, self.MIN_RATINGS_TO_SHOW - self.total_ratings),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }