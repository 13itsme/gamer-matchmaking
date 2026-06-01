from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db
from app.models.user import User
from app.models.profile import Profile
from app.models.user_game import UserGame
from app.models.game import Game
from app.utils.decorators import login_required, get_current_user
from app.utils.helpers import save_avatar, delete_avatar, sanitize_nickname

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<nickname>")
def view(nickname):
    profile = Profile.query.filter_by(nickname=nickname).first_or_404()
    user = profile.user
    user_game = UserGame.query.filter_by(user_id=user.id).all()

    current_user = get_current_user()
    already_rated = False
    existing_rating = None
    can_rate = False

    if current_user and current_user.id != user.id:
        from app.models.trust_rating import TrustRating
        existing_rating = TrustRating.query.filter_by(
            rater_id=current_user.id,
            rated_user_id=user.id
        ).first()
        already_rated = existing_rating is not None
        can_rate = True

    return render_template(
        "profile/view.html",
        profile=profile,
        user=user,
        user_games=user_game,
        trust_score=user.trust_score,
        can_rate=can_rate,
        already_rated=already_rated,
        existing_rating=existing_rating,
        current_user=current_user
    )


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    current_user = get_current_user()
    profile = current_user.profile
    all_games = Game.query.filter_by(is_active=True).all()
    user_game_ids = {ug.game_id for ug in current_user.user_games}

    if request.method == "GET":
        return render_template(
            "profile/edit.html",
            user=current_user,
            profile=profile,
            all_games=all_games,
            user_game_ids=user_game_ids,
            user_games=list(current_user.user_games)
        )

    action = request.form.get("action", "update_profile")

    if action == "update_profile":
        return _update_profile(current_user, profile)
    elif action == "add_game":
        return _add_game(current_user)
    elif action == "remove_game":
        return _remove_game(current_user)
    return redirect(url_for("profile.edit"))


def _update_profile(user, profile):
    nickname = request.form.get("nickname", "").strip()
    bio = request.form.get("bio", "").strip()
    preferred_language = request.form.get("preferred_language", "EN")
    discord_id = request.form.get("discord_id", "").strip()
    real_name = request.form.get("real_name", "").strip()

    errors = []

    if nickname != profile.nickname:
        clean_nickname = sanitize_nickname(nickname)
        if not clean_nickname:
            errors.append("Nickname must have only letters, digits and '-', '_' marks.")
        elif Profile.query.filter_by(nickname=clean_nickname).first():
            errors.append("This nickname is already taken!")
        else:
            profile.nickname = clean_nickname
            session["nickname"] = clean_nickname

    if len(bio) > 500:
        errors.append("Max length of your bio can be 500 characters.")
    else:
        profile.bio = bio or None

    if preferred_language in ["PL", "EN", "RU"]:
        profile.preferred_language = preferred_language

    user.discord_id = discord_id or None
    user.real_name = real_name or None

    if "avatar" in request.files:
        avatar_file = request.files["avatar"]
        if avatar_file and avatar_file.filename:
            old_url = profile.avatar_url
            new_url = save_avatar(avatar_file)
            if new_url:
                delete_avatar(old_url)
                profile.avatar_url = new_url
            else:
                errors.append("PNG, JPG, GIF, WebP formats only (max 2mb)")

    if errors:
        for error in errors:
            flash(error, "error")
    else:
        db.session.commit()
        flash("Profile has been successfully updated!", "success")

    return redirect(url_for("profile.edit"))


def _add_game(user):
    game_id = request.form.get("game_id", type=int)
    region = request.form.get("region", "EU_WEST")
    game_mode = request.form.get("game_mode", "CASUAL")

    if not game_id:
        flash("Select game.", "error")
        return redirect(url_for("profile.edit"))

    existing = UserGame.query.filter_by(user_id=user.id, game_id=game_id).first()
    if existing:
        flash("This game is already in your profile.", "warning")
        return redirect(url_for("profile.edit"))

    game = Game.query.get(game_id)
    if not game or not game.is_active:
        flash("Unknown game.", "error")
        return redirect(url_for("profile.edit"))

    if region not in UserGame.REGIONS:
        region = "EU_WEST"
    if game_mode not in UserGame.GAME_MODES:
        game_mode = "CASUAL"

    user_game = UserGame(user_id=user.id, game_id=game_id, region=region, game_mode=game_mode)
    db.session.add(user_game)
    db.session.commit()
    flash(f"{game.name} added in your profile!", "success")
    return redirect(url_for("profile.edit"))


def _remove_game(user):
    game_id = request.form.get("game_id", type=int)
    user_game = UserGame.query.filter_by(user_id=user.id, game_id=game_id).first()
    if user_game:
        db.session.delete(user_game)
        db.session.commit()
        flash("The game was deleted from your profile.", "info")
    return redirect(url_for("profile.edit"))


@profile_bp.route("/me")
@login_required
def me():
    current_user = get_current_user()
    return redirect(url_for("profile.view", nickname=current_user.profile.nickname))
