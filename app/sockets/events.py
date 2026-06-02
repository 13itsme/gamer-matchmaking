from flask import session, request
from flask_socketio import emit, join_room, leave_room
from app import socketio, db
from app.models.message import Message
from app.models.user import User
from app.models.profile import Profile
from app.models.invitation import Invitation
from app.utils.helpers import get_chat_room_id


def get_user_from_session():
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None


# Connect and Disconnect

@socketio.on("connect")
def on_connect():
    user = get_user_from_session()
    if not user:
        return False

    join_room(f"user_{user.id}")

    if user.profile:
        user.profile.is_online = True
        db.session.commit()
        emit("user_status_changed", {
            "user_id": user.id,
            "nickname": user.profile.nickname,
            "is_online": True
        }, broadcast=True)


@socketio.on("disconnect")
def on_disconnect():
    user = get_user_from_session()
    if user:
        leave_room(f"user_{user.id}")
        if user.profile:
            user.profile.is_online = False
            db.session.commit()
            emit("user_status_changed", {
                "user_id": user.id,
                "nickname": user.profile.nickname,
                "is_online": False
            }, broadcast=True)


# Chat

@socketio.on("join_chat")
def on_join_chat(data):
    user = get_user_from_session()
    if not user:
        return

    partner_id = data.get("partner_id")
    if not partner_id:
        return

    invitation = Invitation.query.filter(
        Invitation.status == "accepted",
        (
                ((Invitation.sender_id == user.id) & (Invitation.receiver_id == partner_id)) |
                ((Invitation.sender_id == partner_id) & (Invitation.receiver_id == user.id))
        )
    ).first()

    if not invitation:
        emit("error", {"message": "Access to chat denied"})
        return

    room = get_chat_room_id(user.id, partner_id)
    join_room(room)
    emit("joined_chat", {"room": room, "partner_id": partner_id})


@socketio.on("leave_chat")
def on_leave_chat(data):
    user = get_user_from_session()
    if not user:
        return
    partner_id = data.get("partner_id")
    if partner_id:
        room = get_chat_room_id(user.id, partner_id)
        leave_room(room)


@socketio.on("send_message")
def on_send_message(data):
    user = get_user_from_session()
    if not user:
        emit("error", {"message": "Not logged in"})
        return

    receiver_id = data.get("receiver_id")
    content = (data.get("content") or "").strip()

    if not receiver_id or not content:
        emit("error", {"message": "Missing message data"})
        return

    if len(content) > 2000:
        emit("error", {"message": "Message is too long (max 2000 characters)"})
        return

    receiver = User.query.get(receiver_id)
    if not receiver:
        emit("error", {"message": "Unknown receiver"})
        return

    invitation = Invitation.query.filter(
        Invitation.status == "accepted",
        (
                ((Invitation.sender_id == user.id) & (Invitation.receiver_id == receiver_id)) |
                ((Invitation.sender_id == receiver_id) & (Invitation.receiver_id == user.id))
        )
    ).first()

    if not invitation:
        emit("error", {"message": "User don't have access to chat with this user"})
        return

    message = Message(
        sender_id=user.id,
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(message)
    db.session.commit()

    message_data = message.to_dict()

    room = get_chat_room_id(user.id, receiver_id)
    emit("new_message", message_data, room=room)

    emit("message_notification", {
        "sender_id": user.id,
        "sender_nickname": user.profile.nickname if user.profile else "Gamer",
        "preview": content[:50] + ("..." if len(content) > 50 else "")
    }, room=f"user_{receiver_id}")


@socketio.on("typing")
def on_typing(data):
    user = get_user_from_session()
    if not user:
        return

    partner_id = data.get("partner_id")
    is_typing = data.get("is_typing", False)

    if partner_id:
        room = get_chat_room_id(user.id, partner_id)
        emit("partner_typing", {
            "user_id": user.id,
            "nickname": user.profile.nickname if user.profile else "Gamer",
            "is_typing": is_typing
        }, room=room, include_self=False)
