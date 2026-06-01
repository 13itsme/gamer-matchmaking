from flask import Blueprint, render_template, request, jsonify, session
from app.models.message import Message
from app.models.user import User
from app.models.invitation import Invitation
from app.utils.decorators import login_required, get_current_user

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")


@chat_bp.route("/<int:partner_id>")
@login_required
def chat_view(partner_id):
    current_user = get_current_user()
    partner = User.query.get_or_404(partner_id)

    invitation = Invitation.query.filter(
        Invitation.status == "accepted",
        (
                (Invitation.sender_id == current_user.id) & (Invitation.receiver_id == partner_id) |
                (Invitation.sender_id == partner_id) & (Invitation.receiver_id == current_user.id)
        )
    ).first()

    if not invitation:
        from flask import abort
        abort(403)

    messages = (
        Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == partner.id)) |
            ((Message.sender_id == partner_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at.asc()).limit(100).all()
    )

    Message.query.filter_by(
        sender_id=partner_id,
        receiver_id=current_user.id,
        is_read=False
    ).update({"is_read": True})

    from app import db
    db.session.commit()

    return render_template(
        "chat/chat.html",
        partner=partner,
        partner_profile=partner.profile,
        messages=messages,
        current_user=current_user
    )


@chat_bp.route("/api/history/<int:partner_id>")
@login_required
def api_history(partner_id):
    current_user = get_current_user()
    before_id = request.args.get("before_id", type=int)
    limit = min(request.args.get("limit", 50, type=int), 100)

    query = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.receiver_id == current_user.id))
    )

    if before_id:
        query = query.filter(Message.id < before_id)

    messages = query.order_by(Message.created_at.desc()).limit(limit).all()
    messages.reverse()

    return jsonify({
        "messages": [m.to_dict() for m in messages],
        "has_more": len(messages) == limit
    })

@chat_bp.route("/api/unread-count")
@login_required
def unread_count():

    current_user = get_current_user()
    count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()
    return jsonify({"unread_count": count})