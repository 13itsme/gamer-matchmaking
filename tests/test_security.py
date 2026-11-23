"""Bezpieczenstwo: CSRF, XSS, SQL injection, open redirect, ciasteczka sesji."""
import pytest

from app.utils.helpers import allowed_file


# ---- CSRF ---------------------------------------------------------------
def test_form_post_without_csrf_token_is_rejected(browser, make_user):
    _, email = make_user("Anna")
    r = browser.c.post("/auth/login", data={"email": email, "password": "haslo1234"})
    assert r.status_code == 400
    with browser.c.session_transaction() as s:
        assert "user_id" not in s


def test_json_post_without_csrf_header_is_rejected(browser, make_user):
    _, email = make_user("Anna")
    other_id, _ = make_user("Marek")
    browser.login(email)
    r = browser.c.post("/ratings/rate", json={"user_id": other_id, "stars": 3})
    assert r.status_code == 400


def test_json_post_with_valid_csrf_header_is_accepted(browser, make_user):
    _, email = make_user("Anna")
    other_id, _ = make_user("Marek")
    browser.login(email)
    r = browser.post_json("/ratings/rate", {"user_id": other_id, "stars": 3})
    assert r.status_code == 200


def test_forged_csrf_token_is_rejected(browser):
    r = browser.c.post("/auth/register", data={"csrf_token": "falszywy"})
    assert r.status_code == 400


# ---- XSS ----------------------------------------------------------------
def test_bio_is_escaped_in_profile_page(browser, make_user):
    make_user("Anna", bio='<script>alert("xss")</script>')
    html = browser.get("/profile/Anna").get_data(as_text=True)
    assert '<script>alert("xss")</script>' not in html
    assert "&lt;script&gt;" in html


def test_html_in_nickname_is_rejected_at_registration(app, browser):
    from app.models.user import User
    data = dict(email="x@example.com", password="haslo1234", confirm_password="haslo1234",
                nickname="<img src=x onerror=alert(1)>", age="20", rodo_consent="on")
    r = browser.post("/auth/register", data)
    assert r.status_code == 200
    with app.app_context():
        assert User.query.count() == 0


# ---- SQL injection ------------------------------------------------------
def test_sql_injection_in_login_does_not_authenticate(browser, make_user):
    make_user("Anna")
    r = browser.login("' OR '1'='1' --", "' OR '1'='1")
    assert r.status_code == 200
    with browser.c.session_transaction() as s:
        assert "user_id" not in s


def test_sql_injection_in_search_filters_is_harmless(browser, make_user, game_id):
    make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    gid = game_id("CS2")
    r = browser.get(f"/api/players?game_id={gid}&region=' OR 1=1 --&language=EN'; DROP TABLE users;--")
    assert r.status_code == 200
    assert r.get_json()["total"] == 1
    r = browser.get("/api/players?game_id=1 OR 1=1")
    assert r.status_code == 400
    assert browser.get(f"/api/players?game_id={gid}").get_json()["total"] == 1  # tabela users nadal istnieje


# ---- Open redirect ------------------------------------------------------
@pytest.mark.parametrize("target", [
    "https://evil.example/", "//evil.example", "/\\evil.example", "http://evil.example/x",
    "javascript:alert(1)",
])
def test_login_ignores_external_redirect_targets(browser, make_user, target):
    _, email = make_user("Anna")
    r = browser.post(f"/auth/login?next={target}", {"email": email, "password": "haslo1234"})
    assert r.status_code == 302
    assert "evil" not in r.headers["Location"] and "javascript" not in r.headers["Location"]


@pytest.mark.parametrize("target", ["/profile/me", "http://localhost/invitations/"])
def test_login_follows_local_redirect_targets(browser, make_user, target):
    _, email = make_user("Anna")
    r = browser.post(f"/auth/login?next={target}", {"email": email, "password": "haslo1234"})
    assert r.status_code == 302 and r.headers["Location"].endswith(("/profile/me", "/invitations/"))


# ---- Sesja, pliki -------------------------------------------------------
def test_session_cookie_is_httponly_and_samesite_lax(browser, make_user):
    _, email = make_user("Anna")
    r = browser.login(email)
    cookie = "; ".join(r.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


@pytest.mark.parametrize("name, ok", [("a.png", True), ("a.JPG", True), ("a.webp", True),
                                       ("a.exe", False), ("a.php", False), ("noext", False), ("a.svg", False)])
def test_avatar_extension_whitelist(app, name, ok):
    with app.app_context():
        assert allowed_file(name) is ok
