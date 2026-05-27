from app import db


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user_games = db.relationship(
        "UserGame",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    invitations = db.relationship(
        "Invitation",
        back_populates="game",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Game {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon_url": self.icon_url,
            "is_active": self.is_active
        }

    @classmethod
    def get_default_games(cls):
        return [
            {"name": "CS2", "icon_url": "/static/images/games/cs2.png"},
            {"name": "Dota 2", "icon_url": "/static/images/games/dota2.png"},
            {"name": "Apex Legends", "icon_url": "/static/images/games/apex.png"},
            {"name": "Discord Hangout", "icon_url": "/static/images/games/discord.png"},
        ]
