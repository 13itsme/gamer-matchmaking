"""System zaufania: oceny 1-3, jedna ocena na pare, widocznosc wskaznika od 3 ocen (FR-8)."""
import pytest

from app import db
from app.models.trust_rating import TrustRating
from app.models.trust_score import TrustScore


@pytest.fixture
def raters(make_user, make_browser):
    target_id, _ = make_user("Cel")
    out = []
    for n in ("R1", "R2", "R3", "R4"):
        _, mail = make_user(n)
        b = make_browser()
        b.login(mail)
        out.append(b)
    return target_id, out


def test_rating_updates_trust_score(app, raters):
    target, (r1, *_) = raters
    r = r1.post_json("/ratings/rate", {"user_id": target, "stars": 3, "comment": "Super"})
    assert r.status_code == 200
    with app.app_context():
        ts = db.session.get(TrustScore, target)
        assert (ts.total_ratings, ts.green_count, ts.average_stars) == (1, 1, 3.0)


def test_score_is_hidden_below_three_ratings_and_visible_from_three(raters):
    target, (r1, r2, r3, _) = raters
    assert r1.post_json("/ratings/rate", {"user_id": target, "stars": 3}).get_json()["trust_score"]["is_visible"] is False
    assert r2.post_json("/ratings/rate", {"user_id": target, "stars": 2}).get_json()["trust_score"]["is_visible"] is False
    ts = r3.post_json("/ratings/rate", {"user_id": target, "stars": 3}).get_json()["trust_score"]
    assert ts["is_visible"] is True
    assert ts["average_stars"] == 2.67 and ts["green_count"] == 2 and ts["orange_count"] == 1


def test_one_rating_per_pair_is_updated_not_duplicated(app, raters):
    target, (r1, *_) = raters
    r1.post_json("/ratings/rate", {"user_id": target, "stars": 1})
    r1.post_json("/ratings/rate", {"user_id": target, "stars": 3, "comment": "Zmiana zdania"})
    with app.app_context():
        assert TrustRating.query.filter_by(rated_user_id=target).count() == 1
        assert TrustRating.query.filter_by(rated_user_id=target).one().stars == 3


def test_cannot_rate_yourself(make_user, make_browser):
    uid, mail = make_user("Anna")
    b = make_browser()
    b.login(mail)
    assert b.post_json("/ratings/rate", {"user_id": uid, "stars": 3}).status_code == 400


@pytest.mark.parametrize("payload", [{"stars": 0}, {"stars": 4}, {"stars": -1}, {"stars": "abc"}, {}])
def test_invalid_stars_are_rejected(app, raters, payload):
    target, (r1, *_) = raters
    r = r1.post_json("/ratings/rate", dict(payload, user_id=target))
    assert r.status_code == 400
    with app.app_context():
        assert TrustRating.query.count() == 0


def test_unknown_user_is_rejected(raters):
    _, (r1, *_) = raters
    assert r1.post_json("/ratings/rate", {"user_id": 99999, "stars": 3}).status_code == 400


def test_comment_is_truncated_to_500(app, raters):
    target, (r1, *_) = raters
    r1.post_json("/ratings/rate", {"user_id": target, "stars": 2, "comment": "k" * 800})
    with app.app_context():
        assert len(TrustRating.query.one().comment) == 500


def test_dominant_color(app, raters):
    target, (r1, r2, r3, r4) = raters
    for b, s in ((r1, 1), (r2, 1), (r3, 2), (r4, 3)):
        b.post_json("/ratings/rate", {"user_id": target, "stars": s})
    with app.app_context():
        assert db.session.get(TrustScore, target).get_dominant_color() == "red"


def test_ratings_listing_api_paginates(raters):
    target, (r1, r2, *_) = raters
    r1.post_json("/ratings/rate", {"user_id": target, "stars": 3})
    r2.post_json("/ratings/rate", {"user_id": target, "stars": 2})
    data = r1.get(f"/ratings/user/{target}").get_json()
    assert data["total"] == 2 and data["page"] == 1 and len(data["ratings"]) == 2
