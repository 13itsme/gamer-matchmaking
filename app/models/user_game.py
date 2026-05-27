from app import db


class UserGame(db.Model):
    __tablename__ = "user_games"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE")
    )
    game_id = db.Column(
        db.Integer,
        db.ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False
    )
    region = db.Column(
        db.String(20),
        nullable=False,
        default="EU_WEST"  # Can be "EU_WEST", "EU_EAST", "NA", "ASIA"
    )
    game_mode = db.Column(
        db.String(20),
        nullable=False,
        default="CASUAL"  # Can be "RANKED", "CASUAL", "CUSTOM"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "game_id", name="uq_user_game"),
    )

    user = db.relationship("User", back_populates="user_games")
    game = db.relationship("Game", back_populates="user_games")

    REGIONS = ["EU_WEST", "EU_EAST", "NA", "ASIA"]
    GAME_MODES = ["RANKED", "CASUAL", "CUSTOM"]

    REGION_LABELS = {
        "EU_WEST": "EU West",
        "EU_EAST": "EU East",
        "NA": "North America",
        "ASIA": "Asia"
    }

    GAME_MODE_LABELS = {
        "RANKED": "Ranked",
        "CASUAL": "Casual",
        "CUSTOM": "Custom"
    }

    def __repr__(self):
        return f"<UserGame user={self.user_id}, games={self.game_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "game_id": self.game_id,
            "game_name": self.game.name if self.game else None,
            "region": self.region,
            "region_label": self.REGION_LABELS.get(self.region, self.region),
            "game_mode": self.game_mode,
            "game_mode_label": self.GAME_MODE_LABELS.get(self.game_mode, self.game_mode)
        }
