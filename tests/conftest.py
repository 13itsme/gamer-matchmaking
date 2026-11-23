"""Wspolna konfiguracja testow GameMatch.

Domyslnie testy dzialaja na SQLite w pamieci. Aby uruchomic je na PostgreSQL:
    TEST_DATABASE_URL=postgresql+psycopg://uzytkownik:haslo@localhost:5432/gm_test pytest
(baza testowa jest czyszczona przed kazdym testem - nie wskazywac bazy produkcyjnej).
"""
import os
import re

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["FLASK_ENV"] = "development"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite://")

from app.config import DevelopmentConfig  # noqa: E402

DevelopmentConfig.DEBUG = False
DevelopmentConfig.SQLALCHEMY_ECHO = False

from app import create_app, db, bcrypt, socketio  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.profile import Profile  # noqa: E402
from app.models.trust_score import TrustScore  # noqa: E402
from app.models.user_game import UserGame  # noqa: E402
from app.models.invitation import Invitation  # noqa: E402

PASSWORD = "haslo1234"


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture(autouse=True)
def clean_db(app):
    """Czysta baza z czterema grami przed kazdym testem."""
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        for g in Game.get_default_games():
            db.session.add(Game(name=g["name"], icon_url=g["icon_url"]))
        db.session.commit()
    yield
    with app.app_context():
        db.session.remove()


class Browser:
    """Cienka nakladka na klienta testowego Flask: sesja, token CSRF, formularze."""

    def __init__(self, app):
        self.app = app
        self.c = app.test_client()

    def csrf(self):
        html = self.c.get("/").get_data(as_text=True)
        m = re.search(r'name="csrf-token" content="([^"]+)"', html)
        assert m, "brak tokenu CSRF w szablonie bazowym"
        return m.group(1)

    def post(self, url, data=None, **kw):
        data = dict(data or {})
        data.setdefault("csrf_token", self.csrf())
        return self.c.post(url, data=data, **kw)

    def post_json(self, url, payload, **kw):
        return self.c.post(url, json=payload, headers={"X-CSRFToken": self.csrf()}, **kw)

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def login(self, email, password=PASSWORD):
        return self.post("/auth/login", {"email": email, "password": password})


@pytest.fixture
def browser(app):
    return Browser(app)


@pytest.fixture
def make_browser(app):
    return lambda: Browser(app)


@pytest.fixture
def make_user(app):
    """Fabryka uzytkownikow: tworzy konto, profil, wskaznik zaufania i gry."""

    def _make(nickname, games=(), language="EN", online=False, bio=None, age=20):
        with app.app_context():
            u = User(
                email=f"{nickname.lower()}@example.com",
                password_hash=bcrypt.generate_password_hash(PASSWORD).decode(),
                age=age,
                rodo_consent=True,
            )
            db.session.add(u)
            db.session.flush()
            db.session.add(Profile(user_id=u.id, nickname=nickname, preferred_language=language,
                                   is_online=online, bio=bio))
            db.session.add(TrustScore(user_id=u.id))
            for game_name, region, mode in games:
                gid = Game.query.filter_by(name=game_name).one().id
                db.session.add(UserGame(user_id=u.id, game_id=gid, region=region, game_mode=mode))
            db.session.commit()
            return u.id, u.email

    return _make


@pytest.fixture
def game_id(app):
    def _get(name="CS2"):
        with app.app_context():
            return Game.query.filter_by(name=name).one().id

    return _get


@pytest.fixture
def accept_invitation(app, game_id):
    """Tworzy zaakceptowane zaproszenie miedzy dwoma uzytkownikami (odblokowuje czat)."""

    def _do(sender_id, receiver_id, game="CS2"):
        with app.app_context():
            inv = Invitation(sender_id=sender_id, receiver_id=receiver_id,
                             game_id=game_id(game), status="accepted")
            db.session.add(inv)
            db.session.commit()
            return inv.id

    return _do
