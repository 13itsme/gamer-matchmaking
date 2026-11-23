"""Profil: edycja, gry gracza, widok publiczny (FR-4)."""
from app import db
from app.models.profile import Profile
from app.models.user_game import UserGame


def login(make_user, make_browser, nick="Anna"):
    uid, mail = make_user(nick)
    b = make_browser()
    b.login(mail)
    return uid, b


def test_unknown_profile_returns_404(browser):
    assert browser.get("/profile/Nikt").status_code == 404


def test_public_profile_is_visible_for_guests(browser, make_user):
    make_user("Anna", bio="Szukam składu")
    r = browser.get("/profile/Anna")
    assert r.status_code == 200 and "Szukam" in r.get_data(as_text=True)


def test_update_profile_fields(app, make_user, make_browser):
    uid, b = login(make_user, make_browser)
    b.post("/profile/edit", {"action": "update_profile", "nickname": "Anna_Nowa", "bio": "Nowy opis",
                             "preferred_language": "PL", "discord_id": "anna#1234", "real_name": "Anna"})
    with app.app_context():
        p = Profile.query.filter_by(user_id=uid).one()
        assert (p.nickname, p.bio, p.preferred_language) == ("Anna_Nowa", "Nowy opis", "PL")
        assert p.user.discord_id == "anna#1234"


def test_update_profile_rejects_invalid_or_taken_nickname(app, make_user, make_browser):
    make_user("Marek")
    uid, b = login(make_user, make_browser)
    for bad in ("Marek", "a b", "x"):
        b.post("/profile/edit", {"action": "update_profile", "nickname": bad, "bio": ""})
    with app.app_context():
        assert Profile.query.filter_by(user_id=uid).one().nickname == "Anna"


def test_bio_longer_than_500_is_rejected(app, make_user, make_browser):
    uid, b = login(make_user, make_browser)
    b.post("/profile/edit", {"action": "update_profile", "nickname": "Anna", "bio": "x" * 501})
    with app.app_context():
        assert Profile.query.filter_by(user_id=uid).one().bio is None


def test_add_and_remove_game(app, make_user, make_browser, game_id):
    uid, b = login(make_user, make_browser)
    gid = game_id("CS2")
    b.post("/profile/edit", {"action": "add_game", "game_id": gid, "region": "NA", "game_mode": "RANKED"})
    with app.app_context():
        ug = UserGame.query.filter_by(user_id=uid).one()
        assert (ug.region, ug.game_mode) == ("NA", "RANKED")
    b.post("/profile/edit", {"action": "add_game", "game_id": gid})           # duplikat
    with app.app_context():
        assert UserGame.query.filter_by(user_id=uid).count() == 1
    b.post("/profile/edit", {"action": "remove_game", "game_id": gid})
    with app.app_context():
        assert UserGame.query.filter_by(user_id=uid).count() == 0


def test_add_game_normalizes_invalid_region_and_mode(app, make_user, make_browser, game_id):
    uid, b = login(make_user, make_browser)
    b.post("/profile/edit", {"action": "add_game", "game_id": game_id("Dota 2"),
                             "region": "MARS", "game_mode": "XXX"})
    with app.app_context():
        ug = UserGame.query.filter_by(user_id=uid).one()
        assert (ug.region, ug.game_mode) == ("EU_WEST", "CASUAL")


def test_add_unknown_game_is_rejected(app, make_user, make_browser):
    uid, b = login(make_user, make_browser)
    b.post("/profile/edit", {"action": "add_game", "game_id": 99999})
    with app.app_context():
        assert UserGame.query.filter_by(user_id=uid).count() == 0
