from app import db


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    nickname = db.Column(db.String(50), unique=True, nullable=False, index=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    preferred_language = db.Column(
        db.String(5),
        nullable=False,
        default="EN"  # Can be "PL", "EN", "RU"
    )
    is_online = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile {self.nickname}>"

    def to_dict(self, include_trust=False):
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url or "/static/uploads/avatars/default.png",
            "bio": self.bio,
            "preferred_language": self.preferred_language,
            "is_online": self.is_online
        }
        if include_trust and self.user and self.user.trust_score:
            data["trust_score"] = self.user.trust_score.to_dict()
        return data
