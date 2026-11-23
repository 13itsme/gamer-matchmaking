"""Czat w czasie rzeczywistym (Socket.IO) i historia wiadomosci (FR-7)."""
import pytest

from app import socketio
from app.models.message import Message
from app.models.profile import Profile


@pytest.fixture
def chat_pair(make_user, make_browser, accept_invitation):
    a_id, a_mail = make_user("Anna")
    b_id, b_mail = make_user("Marek")
    ba, bb = make_browser(), make_browser()
    ba.login(a_mail)
    bb.login(b_mail)
    accept_invitation(a_id, b_id)
    return a_id, b_id, ba, bb


def names(received):
    return [e["name"] for e in received]


def test_chat_page_forbidden_without_accepted_invitation(make_user, make_browser):
    a_id, a_mail = make_user("Anna")
    b_id, _ = make_user("Marek")
    ba = make_browser()
    ba.login(a_mail)
    assert ba.get(f"/chat/{b_id}").status_code == 403


def test_pending_invitation_does_not_unlock_chat(app, make_user, make_browser, game_id):
    from app import db
    from app.models.invitation import Invitation
    a_id, a_mail = make_user("Anna")
    b_id, _ = make_user("Marek")
    with app.app_context():
        db.session.add(Invitation(sender_id=a_id, receiver_id=b_id, game_id=game_id("CS2")))
        db.session.commit()
    ba = make_browser()
    ba.login(a_mail)
    assert ba.get(f"/chat/{b_id}").status_code == 403


def test_chat_page_is_available_after_acceptance_and_marks_read(app, chat_pair):
    a, b, ba, bb = chat_pair
    with app.app_context():
        from app import db
        db.session.add(Message(sender_id=b, receiver_id=a, content="Hej"))
        db.session.commit()
    r = ba.get(f"/chat/{b}")
    assert r.status_code == 200 and "Hej" in r.get_data(as_text=True)
    with app.app_context():
        assert Message.query.filter_by(receiver_id=a, is_read=False).count() == 0


def test_chat_is_not_accessible_for_third_party(make_user, make_browser, chat_pair):
    a, b, _, _ = chat_pair
    _, c_mail = make_user("Olga")
    bc = make_browser()
    bc.login(c_mail)
    assert bc.get(f"/chat/{a}").status_code == 403
    assert bc.get(f"/api/history/{a}".replace("/api", "/chat/api")).get_json() == {"messages": [], "has_more": False}


def test_history_api_returns_chronological_messages_with_limit(app, chat_pair):
    a, b, ba, _ = chat_pair
    with app.app_context():
        from app import db
        for i in range(5):
            db.session.add(Message(sender_id=a if i % 2 == 0 else b, receiver_id=b if i % 2 == 0 else a,
                                   content=f"m{i}"))
        db.session.commit()
    data = ba.get(f"/chat/api/history/{b}?limit=3").get_json()
    assert [m["content"] for m in data["messages"]] == ["m2", "m3", "m4"]
    assert data["has_more"] is True


def test_unread_counter(app, chat_pair):
    a, b, ba, _ = chat_pair
    with app.app_context():
        from app import db
        db.session.add_all([Message(sender_id=b, receiver_id=a, content="1"),
                            Message(sender_id=b, receiver_id=a, content="2")])
        db.session.commit()
    assert ba.get("/chat/api/unread-count").get_json()["unread_count"] == 2


# ---- Socket.IO ----------------------------------------------------------
def test_socket_connection_refused_for_guest(app, make_browser):
    sock = socketio.test_client(app, flask_test_client=make_browser().c)
    assert not sock.is_connected()


def test_socket_connect_sets_online_and_disconnect_sets_offline(app, chat_pair):
    a, _, ba, _ = chat_pair
    sock = socketio.test_client(app, flask_test_client=ba.c)
    assert sock.is_connected()
    with app.app_context():
        assert Profile.query.filter_by(user_id=a).one().is_online is True
    sock.disconnect()
    with app.app_context():
        assert Profile.query.filter_by(user_id=a).one().is_online is False


def test_join_chat_allowed_only_with_accepted_invitation(app, chat_pair, make_user, make_browser):
    a, b, ba, _ = chat_pair
    sa = socketio.test_client(app, flask_test_client=ba.c)
    sa.get_received()
    sa.emit("join_chat", {"partner_id": b})
    ev = sa.get_received()
    assert "joined_chat" in names(ev)
    assert ev[0]["args"][0]["room"] == f"chat_{min(a, b)}_{max(a, b)}"

    c_id, c_mail = make_user("Olga")
    bc = make_browser()
    bc.login(c_mail)
    sc = socketio.test_client(app, flask_test_client=bc.c)
    sc.get_received()
    sc.emit("join_chat", {"partner_id": a})
    assert names(sc.get_received()) == ["error"]


def test_message_is_saved_and_delivered_to_both_participants(app, chat_pair):
    a, b, ba, bb = chat_pair
    sa = socketio.test_client(app, flask_test_client=ba.c)
    sb = socketio.test_client(app, flask_test_client=bb.c)
    sa.emit("join_chat", {"partner_id": b})
    sb.emit("join_chat", {"partner_id": a})
    sa.get_received(); sb.get_received()

    sa.emit("send_message", {"receiver_id": b, "content": "Cześć, gramy?"})
    ra, rb = sa.get_received(), sb.get_received()
    assert "new_message" in names(ra) and "new_message" in names(rb)
    assert "message_notification" in names(rb)
    with app.app_context():
        m = Message.query.one()
        assert (m.sender_id, m.receiver_id, m.content) == (a, b, "Cześć, gramy?")


@pytest.mark.parametrize("content", ["", "   ", None])
def test_empty_message_is_rejected(app, chat_pair, content):
    a, b, ba, _ = chat_pair
    s = socketio.test_client(app, flask_test_client=ba.c)
    s.get_received()
    s.emit("send_message", {"receiver_id": b, "content": content})
    assert names(s.get_received()) == ["error"]
    with app.app_context():
        assert Message.query.count() == 0


def test_message_length_limit_2000(app, chat_pair):
    a, b, ba, _ = chat_pair
    s = socketio.test_client(app, flask_test_client=ba.c)
    s.emit("join_chat", {"partner_id": b})
    s.get_received()
    s.emit("send_message", {"receiver_id": b, "content": "x" * 2001})
    assert names(s.get_received()) == ["error"]
    s.emit("send_message", {"receiver_id": b, "content": "x" * 2000})
    assert "new_message" in names(s.get_received())
    with app.app_context():
        assert Message.query.count() == 1


def test_message_without_accepted_invitation_is_rejected(app, make_user, make_browser):
    a_id, a_mail = make_user("Anna")
    b_id, _ = make_user("Marek")
    ba = make_browser()
    ba.login(a_mail)
    s = socketio.test_client(app, flask_test_client=ba.c)
    s.get_received()
    s.emit("send_message", {"receiver_id": b_id, "content": "hej"})
    assert names(s.get_received()) == ["error"]
    with app.app_context():
        assert Message.query.count() == 0
