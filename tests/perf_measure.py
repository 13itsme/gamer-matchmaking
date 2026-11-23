"""Pomiar czasu obslugi zadan (bez sieci, w procesie testowym).

Uruchomienie:
    TEST_DATABASE_URL=postgresql+psycopg://uzytkownik:haslo@localhost:5432/gm_test python tests/perf_measure.py
Skrypt tworzy 1000 kont w bazie testowej (czyszczonej na starcie) i mierzy mediane, p95 i maksimum.
"""
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import conftest  # noqa: F401,E402  (ustawia zmienne srodowiskowe i konfiguracje)
from conftest import Browser, PASSWORD  # noqa: E402
from app import create_app, db, bcrypt, socketio  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.invitation import Invitation  # noqa: E402
from app.models.message import Message  # noqa: E402
from app.models.profile import Profile  # noqa: E402
from app.models.trust_rating import TrustRating  # noqa: E402
from app.models.trust_score import TrustScore  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_game import UserGame  # noqa: E402

N_USERS, RUNS = 1000, 100
random.seed(7)


def stats(samples):
    s = sorted(samples)
    return statistics.median(s) * 1000, s[int(len(s) * 0.95) - 1] * 1000, s[-1] * 1000


def measure(fn, runs=RUNS):
    fn()  # rozgrzewka
    out = []
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t)
    return stats(out)


def seed(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        games = [Game(name=g["name"], icon_url=g["icon_url"]) for g in Game.get_default_games()]
        db.session.add_all(games)
        db.session.flush()
        pw = bcrypt.generate_password_hash(PASSWORD).decode()
        regions, modes, langs = ["EU_WEST", "EU_EAST", "NA", "ASIA"], ["RANKED", "CASUAL", "CUSTOM"], ["PL", "EN", "RU"]
        for i in range(N_USERS):
            u = User(email=f"u{i}@example.com", password_hash=pw, age=20, rodo_consent=True)
            db.session.add(u)
            db.session.flush()
            db.session.add(Profile(user_id=u.id, nickname=f"Gracz{i:04d}", preferred_language=random.choice(langs),
                                   is_online=random.random() < 0.3))
            db.session.add(TrustScore(user_id=u.id))
            for g in random.sample(games, 2):
                db.session.add(UserGame(user_id=u.id, game_id=g.id, region=random.choice(regions),
                                        game_mode=random.choice(modes)))
        db.session.flush()
        for uid in range(1, 301):  # 300 graczy ma 3-6 ocen
            raters = random.sample(range(1, N_USERS + 1), random.randint(3, 6))
            for r in raters:
                if r != uid:
                    db.session.add(TrustRating(rater_id=r, rated_user_id=uid, stars=random.choice([1, 2, 3, 3])))
        db.session.flush()
        for ts in TrustScore.query.all():
            ts.recalculate()
        db.session.add(Invitation(sender_id=1, receiver_id=2, game_id=1, status="accepted"))
        for i in range(100):
            db.session.add(Message(sender_id=1 + i % 2, receiver_id=2 - i % 2, content=f"wiadomosc {i}"))
        db.session.commit()


def main():
    app = create_app()
    app.config.update(TESTING=True)
    seed(app)
    rows = []

    anon = Browser(app)
    rows.append(("GET /  (strona glowna, statystyki gier)", *measure(lambda: anon.get("/"))))
    rows.append(("GET /api/players?game_id=1 (bez filtrow)", *measure(lambda: anon.get("/api/players?game_id=1"))))
    rows.append(("GET /api/players (region + tryb + jezyk)",
                 *measure(lambda: anon.get("/api/players?game_id=1&region=EU_WEST&game_mode=RANKED&language=PL"))))
    rows.append(("GET /api/players (min_trust=2.5)", *measure(lambda: anon.get("/api/players?game_id=1&min_trust=2.5"))))
    rows.append(("GET /profile/Gracz0001 (widok profilu)", *measure(lambda: anon.get("/profile/Gracz0001"))))

    login_samples = []
    for i in range(30):
        b = Browser(app)
        tok = b.csrf()
        t = time.perf_counter()
        b.c.post("/auth/login", data={"email": f"u{i + 10}@example.com", "password": PASSWORD, "csrf_token": tok})
        login_samples.append(time.perf_counter() - t)
    rows.append(("POST /auth/login (bcrypt, 30 prob)", *stats(login_samples)))

    u1 = Browser(app)
    u1.login("u0@example.com")
    rows.append(("GET /chat/api/history (100 wiadomosci)", *measure(lambda: u1.get("/chat/api/history/2?limit=100"))))
    rows.append(("GET /chat/2 (strona czatu, 100 wiadomosci)", *measure(lambda: u1.get("/chat/2"))))

    counter = iter(range(10 ** 6))
    tok = u1.csrf()

    def send_invitation():
        i = next(counter)
        # kazdy odbiorca tylko raz - unika bledu 409
        u1.c.post("/invitations/send", data={"receiver_id": 10 + (i % 900), "game_id": 1, "csrf_token": tok},
                  headers={"X-Requested-With": "XMLHttpRequest"})

    rows.append(("POST /invitations/send", *measure(send_invitation, runs=90)))

    u2 = Browser(app)
    u2.login("u1@example.com")
    s1 = socketio.test_client(app, flask_test_client=u1.c)
    s2 = socketio.test_client(app, flask_test_client=u2.c)
    s1.emit("join_chat", {"partner_id": 2})
    s2.emit("join_chat", {"partner_id": 1})
    s1.get_received(); s2.get_received()

    def socket_message():
        s1.emit("send_message", {"receiver_id": 2, "content": "pomiar"})
        s1.get_received(); s2.get_received()

    rows.append(("Socket.IO send_message (zapis + rozeslanie)", *measure(socket_message)))

    print(f"\nBaza: {os.environ['DATABASE_URL'].split('@')[-1] if '@' in os.environ['DATABASE_URL'] else os.environ['DATABASE_URL']}, "
          f"konta: {N_USERS}, powtorzenia: {RUNS}\n")
    print("| Operacja | mediana [ms] | p95 [ms] | maks. [ms] |")
    print("|---|---:|---:|---:|")
    for name, med, p95, mx in rows:
        print(f"| {name} | {med:.1f} | {p95:.1f} | {mx:.1f} |")


if __name__ == "__main__":
    main()
