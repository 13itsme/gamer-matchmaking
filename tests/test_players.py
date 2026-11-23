"""Wyszukiwanie graczy z filtrami (FR-5)."""
from app import db
from app.models.trust_rating import TrustRating
from app.models.trust_score import TrustScore


def search(browser, gid, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    r = browser.get(f"/api/players?game_id={gid}" + (f"&{q}" if q else ""))
    assert r.status_code == 200
    return r.get_json()


def nicks(data):
    return [p["nickname"] for p in data["players"]]


def test_missing_game_id_returns_400(browser):
    assert browser.get("/api/players").status_code == 400


def test_returns_only_players_of_selected_game(browser, make_user, game_id):
    make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    make_user("Marek", games=[("Dota 2", "EU_WEST", "CASUAL")])
    assert nicks(search(browser, game_id("CS2"))) == ["Anna"]
    assert nicks(search(browser, game_id("Dota 2"))) == ["Marek"]


def test_current_user_is_excluded(browser, make_user, game_id):
    _, email = make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    make_user("Marek", games=[("CS2", "EU_WEST", "CASUAL")])
    browser.login(email)
    assert nicks(search(browser, game_id("CS2"))) == ["Marek"]


def test_filters_region_mode_language(browser, make_user, game_id):
    make_user("Anna", games=[("CS2", "EU_WEST", "RANKED")], language="PL")
    make_user("Marek", games=[("CS2", "NA", "CASUAL")], language="EN")
    make_user("Olga", games=[("CS2", "EU_WEST", "CASUAL")], language="EN")
    g = game_id("CS2")
    assert nicks(search(browser, g, region="NA")) == ["Marek"]
    assert sorted(nicks(search(browser, g, region="EU_WEST"))) == ["Anna", "Olga"]
    assert nicks(search(browser, g, game_mode="RANKED")) == ["Anna"]
    assert nicks(search(browser, g, language="PL")) == ["Anna"]
    assert nicks(search(browser, g, region="EU_WEST", game_mode="CASUAL", language="EN")) == ["Olga"]


def test_invalid_filter_values_are_ignored(browser, make_user, game_id):
    make_user("Anna", games=[("CS2", "EU_WEST", "RANKED")])
    assert nicks(search(browser, game_id("CS2"), region="MARS", game_mode="XXX", language="ZZ")) == ["Anna"]


def test_online_players_are_listed_first(browser, make_user, game_id):
    make_user("Offline1", games=[("CS2", "EU_WEST", "CASUAL")], online=False)
    make_user("Online1", games=[("CS2", "EU_WEST", "CASUAL")], online=True)
    make_user("Offline2", games=[("CS2", "EU_WEST", "CASUAL")], online=False)
    assert nicks(search(browser, game_id("CS2")))[0] == "Online1"


def test_pagination_12_per_page(browser, make_user, game_id):
    for i in range(15):
        make_user(f"Gracz{i:02d}", games=[("CS2", "EU_WEST", "CASUAL")])
    g = game_id("CS2")
    p1, p2 = search(browser, g), search(browser, g, page=2)
    assert len(p1["players"]) == 12 and p1["total"] == 15 and p1["pages"] == 2 and p1["has_next"] is True
    assert len(p2["players"]) == 3 and p2["has_next"] is False
    assert not set(nicks(p1)) & set(nicks(p2))


def _rate(app, rated_id, stars_list):
    with app.app_context():
        for i, stars in enumerate(stars_list):
            rater_email = f"rater{i}_{rated_id}@example.com"
            from app.models.user import User
            rater = User(email=rater_email, password_hash="x", rodo_consent=True)
            db.session.add(rater)
            db.session.flush()
            db.session.add(TrustRating(rater_id=rater.id, rated_user_id=rated_id, stars=stars))
        db.session.flush()
        TrustScore.query.get(rated_id).recalculate()
        db.session.commit()


def test_min_trust_requires_at_least_three_ratings(app, browser, make_user, game_id):
    a, _ = make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    m, _ = make_user("Marek", games=[("CS2", "EU_WEST", "CASUAL")])
    make_user("Olga", games=[("CS2", "EU_WEST", "CASUAL")])
    _rate(app, a, [3, 3, 3])      # srednia 3.0, widoczny
    _rate(app, m, [3, 3])         # tylko 2 oceny: wskaznik ukryty
    g = game_id("CS2")
    assert nicks(search(browser, g, min_trust=2.5)) == ["Anna"]
    assert sorted(nicks(search(browser, g))) == ["Anna", "Marek", "Olga"]


def test_min_trust_threshold_uses_average(app, browser, make_user, game_id):
    a, _ = make_user("Anna", games=[("CS2", "EU_WEST", "CASUAL")])
    m, _ = make_user("Marek", games=[("CS2", "EU_WEST", "CASUAL")])
    _rate(app, a, [3, 3, 2])      # srednia 2.67
    _rate(app, m, [2, 2, 1])      # srednia 1.67
    g = game_id("CS2")
    assert nicks(search(browser, g, min_trust=2)) == ["Anna"]
    assert sorted(nicks(search(browser, g, min_trust=1.5))) == ["Anna", "Marek"]
