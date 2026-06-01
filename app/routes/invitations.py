from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db, socketio
from app.models.invitation import Invitation
from app.models.user import User
from app.models.game import Game
from app.utils.decorators import login_required, get_current_user

invitations_bp = Blueprint("invitations", __name__, url_prefix="/invitations")


@invitations_bp.route("/")
@login_required
def list_invitations():
    current_user = get_current_user()

    incoming = (
        Invitation.query
        .filter_by(receiver_id=current_user.id, status="pending")
        .order_by(Invitation.created_at.desc())
        .all()
    )
    outgoing = (
        Invitation.query
        .filter_by(sender_id=current_user.id)
        .order_by(Invitation.created_at.desc())
        .limit(20)
        .all()
    )

    return render_template(
        "invitations/list.html",
        incoming=incoming,
        outgoing=outgoing,
        current_user=current_user
    )


@invitations_bp.route("/send", methods=["POST"])
@login_required
def send():
    current_user = get_current_user()
    receiver_id = request.form.get("receiver_id", type=int)
    game_id = request.form.get("game_id", type=int)
    message = request.form.get("message", "").strip()[:500]

    is_ajax = request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not receiver_id or not game_id:
        if is_ajax:
            return jsonify({"error": "Missing data"}), 400
        flash("Incorrect data.", "error")
        return redirect(url_for("invitations.list_invitations"))

    receiver = User.query.get(receiver_id)
    if not receiver or receiver_id == current_user.id:
        if is_ajax:
            return jsonify({"error": "Unknown receiver"}), 400
        flash("Unknown receiver.", "error")
        return redirect(url_for("invitations.list_invitations"))

    game = Game.query.get(game_id)
    if not game:
        if is_ajax:
            return jsonify({"error": "Unknown game"}), 400
        flash("Unknown game.", "error")
        return redirect(url_for("invitations.list_invitations"))

    existing = Invitation.query.filter_by(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending"
    ).first()
    if existing:
        if is_ajax:
            return jsonify({"error": "Invitation has already been sent", "invitation_id": existing.id}), 409
        flash("Invitation has already been sent.", "warning")
        return redirect(url_for("invitations.list_invitations"))

    invitation = Invitation(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        game_id=game_id,
        message=message or None
    )
    db.session.add(invitation)
    db.session.commit()

    socketio.emit(
        "new_invitation",
        {
            "invitation_id": invitation.id,
            "sender_nickname": current_user.profile.nickname,
            "game_name": game.name,
            "message": message
        },
        room=f"user_{receiver_id}"
    )

    if is_ajax:
        return jsonify({"success": True, "invitation_id": invitation.id}), 201

    flash(f"Invitation has been sent to {receiver.profile.nickname}!", "success")
    return redirect(url_for("invitations.list_invitations"))

@invitations_bp.route("/<int:invitation_id>/accept", methods=["POST"])
@login_required
def accept(invitation_id):
    current_user = get_current_user()
    invitation = Invitation.query.get_or_404(invitation_id)

    if invitation.receiver_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    if invitation.status != "pending":
        return jsonify({"error": "Invitation already processed"}), 400

    invitation.status = Invitation.STATUS_ACCEPTED
    db.session.commit()

    socketio.emit(
        "invitation_accepted",
        {
            "invitation_id": invitation.id,
            "accepter_nickname": current_user.profile.nickname,
            "chat_partner_id": current_user.id
        },
        room=f"user_{invitation.sender_id}"
    )

    return jsonify({
        "success": True,
        "chat_url": url_for("chat.chat_view", partner_id=invitation.sender_id)
    })

@invitations_bp.route("/<int:invitation_id>/reject", methods=["POST"])
@login_required
def reject(invitation_id):
    current_user = get_current_user()
    invitation = Invitation.query.get_or_404(invitation_id)

    if invitation.receiver_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403
    if invitation.status != "pending":
        return jsonify({"error": "Invitation already processed"}), 400

    invitation.status = Invitation.STATUS_REJECTED
    db.session.commit()

    return jsonify({"success": True})
