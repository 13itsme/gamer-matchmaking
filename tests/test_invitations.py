"""Zaproszenia: wysylanie, akceptacja, odrzucenie, kontrola dostepu (FR-6)."""
import pytest

from app import db, socketio
from app.models.invitation import Invitation

AJAX = {"X-Requested-With": "XMLHttpRequest"}


def send(browser, receiver_id, game, message="Gramy?"):
    return browser.post("/invitations/send",
                        {"receiver_id": receiver_id, "game_id": game, "message": message}, headers=AJAX)


@pytest.fixture
def pair(make_user, make_browser):
    a_id, a_mail = make_user("Anna")
    b_id, b_mail = make_user("Marek")
    ba, bb = make_browser(), make_browser()
    ba.login(a_mail)
    bb.login(b_mail)
    return a_id, b_id, ba, bb


def test_send_invitation_creates_pending_record(app, pair, game_id):
    a, b, ba, _ = pair
    r = send(ba, b, game_id("CS2"))
    assert r.status_code == 201 and r.get_json()["success"] is True
    with app.app_context():
        inv = Invitation.query.one()
        assert (inv.sender_id, inv.receiver_id, inv.status) == (a, b, "pending")


def test_send_requires_login(make_browser, game_id):
    r = make_browser().post("/invitations/send", {"receiver_id": 1, "game_id": game_id()}, headers=AJAX)
    assert r.status_code == 401


def test_duplicate_pending_invitation_returns_409(pair, game_id):
    _, b, ba, _ = pair
    assert send(ba, b, game_id("CS2")).status_code == 201
    assert send(ba, b, game_id("CS2")).status_code == 409


def test_invalid_invitation_data_returns_400(pair, game_id):
    a, b, ba, _ = pair
    assert send(ba, a, game_id("CS2")).status_code == 400        # do samego siebie
    assert send(ba, 99999, game_id("CS2")).status_code == 400    # nieistniejacy odbiorca
    assert send(ba, b, 99999).status_code == 400                 # nieistniejaca gra
    assert ba.post("/invitations/send", {"receiver_id": b}, headers=AJAX).status_code == 400


def test_invitation_message_is_truncated_to_500_chars(app, pair, game_id):
    _, b, ba, _ = pair
    send(ba, b, game_id("CS2"), message="x" * 600)
    with app.app_context():
        assert len(Invitation.query.one().message) == 500


def test_receiver_accepts_invitation(app, pair, game_id):
    a, b, ba, bb = pair
    inv_id = send(ba, b, game_id("CS2")).get_json()["invitation_id"]
    r = bb.post(f"/invitations/{inv_id}/accept")
    assert r.status_code == 200 and r.get_json()["chat_url"].endswith(f"/chat/{a}")
    with app.app_context():
        assert db.session.get(Invitation, inv_id).status == "accepted"


def test_receiver_rejects_invitation(app, pair, game_id):
    _, b, ba, bb = pair
    inv_id = send(ba, b, game_id("CS2")).get_json()["invitation_id"]
    assert bb.post(f"/invitations/{inv_id}/reject").status_code == 200
    with app.app_context():
        assert db.session.get(Invitation, inv_id).status == "rejected"


def test_only_receiver_may_accept_or_reject(app, pair, game_id):
    _, b, ba, bb = pair
    inv_id = send(ba, b, game_id("CS2")).get_json()["invitation_id"]
    assert ba.post(f"/invitations/{inv_id}/accept").status_code == 403   # nadawca nie moze akceptowac
    assert ba.post(f"/invitations/{inv_id}/reject").status_code == 403
    with app.app_context():
        assert db.session.get(Invitation, inv_id).status == "pending"


def test_third_party_cannot_accept_invitation(app, pair, game_id, make_user, make_browser):
    _, b, ba, _ = pair
    inv_id = send(ba, b, game_id("CS2")).get_json()["invitation_id"]
    _, c_mail = make_user("Olga")
    bc = make_browser()
    bc.login(c_mail)
    assert bc.post(f"/invitations/{inv_id}/accept").status_code == 403


def test_invitation_cannot_be_processed_twice(pair, game_id):
    _, b, ba, bb = pair
    inv_id = send(ba, b, game_id("CS2")).get_json()["invitation_id"]
    assert bb.post(f"/invitations/{inv_id}/accept").status_code == 200
    assert bb.post(f"/invitations/{inv_id}/accept").status_code == 400
    assert bb.post(f"/invitations/{inv_id}/reject").status_code == 400


def test_unknown_invitation_returns_404(pair):
    assert pair[3].post("/invitations/99999/accept").status_code == 404


def test_new_invitation_is_pushed_via_socketio_to_receiver(app, pair, game_id):
    _, b, ba, bb = pair
    receiver_socket = socketio.test_client(app, flask_test_client=bb.c)
    receiver_socket.get_received()
    send(ba, b, game_id("CS2"), message="Cześć")
    events = [e for e in receiver_socket.get_received() if e["name"] == "new_invitation"]
    assert len(events) == 1
    payload = events[0]["args"][0]
    assert payload["sender_nickname"] == "Anna" and payload["game_name"] == "CS2"


def test_invitations_page_lists_incoming_and_sent(pair, game_id):
    _, b, ba, bb = pair
    send(ba, b, game_id("CS2"))
    assert "Anna" in bb.get("/invitations/").get_data(as_text=True)
    assert "Marek" in ba.get("/invitations/").get_data(as_text=True)
