"""Rejestracja, logowanie, wylogowanie, usuniecie konta (wymagania FR-1..FR-3)."""
import pytest

from app import db, bcrypt
from app.models.user import User
from app.models.profile import Profile
from app.models.trust_score import TrustScore

VALID = dict(email="nowy@example.com", password="haslo1234", confirm_password="haslo1234",
             nickname="Nowy_Gracz", age="20", rodo_consent="on", preferred_language="PL")


def body(resp):
    return resp.get_data(as_text=True)


def test_registration_creates_user_profile_and_trust_score(app, browser):
    r = browser.post("/auth/register", VALID)
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]
    with app.app_context():
        u = User.query.filter_by(email="nowy@example.com").one()
        assert u.profile.nickname == "Nowy_Gracz"
        assert u.profile.preferred_language == "PL"
        assert u.trust_score is not None and u.trust_score.total_ratings == 0
        assert u.rodo_consent is True


def test_password_is_stored_as_bcrypt_hash(app, browser):
    browser.post("/auth/register", VALID)
    with app.app_context():
        u = User.query.filter_by(email="nowy@example.com").one()
        assert u.password_hash != "haslo1234"
        assert u.password_hash.startswith("$2")
        assert bcrypt.check_password_hash(u.password_hash, "haslo1234")


@pytest.mark.parametrize("change, expected", [
    ({"email": "bez-malpy"}, "Incorrect email"),
    ({"password": "1234567", "confirm_password": "1234567"}, "at least 8 characters"),
    ({"confirm_password": "inne_haslo"}, "the same"),
    ({"nickname": "ab"}, "Nick can be filled"),
    ({"nickname": "zly nick!"}, "Nick can be filled"),
    ({"nickname": "<b>x</b>"}, "Nick can be filled"),
    ({"age": "12"}, "at least 13"),
    ({"rodo_consent": ""}, "agree to data processing"),
])
def test_registration_rejects_invalid_data(app, browser, change, expected):
    data = dict(VALID, **change)
    if data.get("rodo_consent") == "":
        data.pop("rodo_consent")
    r = browser.post("/auth/register", data)
    assert r.status_code == 200
    assert expected in body(r)
    with app.app_context():
        assert User.query.count() == 0


def test_registration_rejects_duplicate_email_and_nickname(app, browser, make_browser):
    browser.post("/auth/register", VALID)
    other = make_browser()
    r = other.post("/auth/register", dict(VALID, nickname="Inny_Gracz"))
    assert "already registered" in body(r)
    r = other.post("/auth/register", dict(VALID, email="inny@example.com"))
    assert "already taken" in body(r)
    with app.app_context():
        assert User.query.count() == 1


def test_login_success_sets_session_and_online_status(app, browser, make_user):
    uid, email = make_user("Anna")
    r = browser.login(email)
    assert r.status_code == 302 and r.headers["Location"].endswith("/")
    with browser.c.session_transaction() as s:
        assert s["user_id"] == uid and s["nickname"] == "Anna"
    with app.app_context():
        assert Profile.query.filter_by(user_id=uid).one().is_online is True


def test_login_wrong_password_and_unknown_email_give_same_message(browser, make_user):
    _, email = make_user("Anna")
    r1 = browser.login(email, "zle_haslo")
    r2 = browser.login("nikt@example.com", "haslo1234")
    assert r1.status_code == 200 and r2.status_code == 200
    assert "Incorrect password or email" in body(r1)
    assert "Incorrect password or email" in body(r2)
    with browser.c.session_transaction() as s:
        assert "user_id" not in s


def test_login_requires_both_fields(browser):
    r = browser.post("/auth/login", {"email": "", "password": ""})
    assert "enter your email and password" in body(r)


def test_logout_clears_session_and_sets_offline(app, browser, make_user):
    uid, email = make_user("Anna")
    browser.login(email)
    r = browser.get("/auth/logout")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]
    with browser.c.session_transaction() as s:
        assert "user_id" not in s
    with app.app_context():
        assert Profile.query.filter_by(user_id=uid).one().is_online is False


def test_protected_pages_redirect_guests_to_login(browser):
    for url in ("/invitations/", "/chat/", "/profile/edit", "/profile/me"):
        r = browser.get(url)
        assert r.status_code == 302 and "/auth/login" in r.headers["Location"], url


def test_protected_json_endpoint_returns_401_for_guests(browser):
    r = browser.post_json("/ratings/rate", {"user_id": 1, "stars": 3})
    assert r.status_code == 401


def test_logged_in_user_is_redirected_away_from_login_page(browser, make_user):
    _, email = make_user("Anna")
    browser.login(email)
    r = browser.get("/auth/login")
    assert r.status_code == 302


def test_delete_account_requires_correct_password_and_cascades(app, browser, make_user):
    uid, email = make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    browser.login(email)
    browser.post("/auth/delete-account", {"password": "zle"})
    with app.app_context():
        assert db.session.get(User, uid) is not None
    browser.post("/auth/delete-account", {"password": "haslo1234"})
    with app.app_context():
        assert db.session.get(User, uid) is None
        assert Profile.query.filter_by(user_id=uid).count() == 0
        assert TrustScore.query.filter_by(user_id=uid).count() == 0
