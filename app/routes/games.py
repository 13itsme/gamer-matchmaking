from flask import Blueprint, render_template, request, jsonify, session
from sqlalchemy import and_
from app import db
from app.models.game import Game
from app.models.user_game import UserGame
from app.models.profile import Profile
from app.models.user import User
from app.models.trust_score import TrustScore
from app.utils.decorators import get_current_user

games_bp = Blueprint("games", __name__)


@games_bp.route("/")
def index():
    games = Game.query.filter_by(is_active=True).all()

    game_stats = {}
    for game in games:
        count = UserGame.query.filter_by(game_id=game.id).count()
        online_count = (
            UserGame.query
            .join(User, UserGame.user_id == User.id)
            .join(Profile, User.id == Profile.user_id)
            .filter(UserGame.game_id == game.id, Profile.is_online == True)
            .count()
        )
        game_stats[game.id] = {"total": count, "online": online_count}

    current_user = get_current_user()
    return render_template(
        "index.html",
        games=games,
        game_stats=game_stats,
        current_user=current_user
    )


@games_bp.route("/game/<int:game_id>")
def category(game_id):
    game = Game.query.get_or_404(game_id)
    current_user = get_current_user()

    return render_template(
        "games/category.html",
        game=game,
        regions=UserGame.REGIONS,
        region_labels=UserGame.REGION_LABELS,
        game_modes=UserGame.GAME_MODES,
        game_mode_labels=UserGame.GAME_MODE_LABELS,
        languages=[("PL", "Polski"), ("EN", "English"), ("RU", "Русский")],
        current_user=current_user
    )


@games_bp.route("/api/players")
def api_players():
    game_id = request.args.get("game_id", type=int)
    region = request.args.get("region", "")
    language = request.args.get("language", "")
    game_mode = request.args.get("game_mode", "")
    min_trust = request.args.get("min_trust", type=float, default=0)
    page = request.args.get("page", 1, type=int)
    per_page = 12

    if not game_id:
        return jsonify({"error": "Incorrect game_id"}), 400

    current_user_id = session.get("user_id")

    query = (
        UserGame.query
        .join(User, UserGame.user_id == User.id)
        .join(Profile, User.id == Profile.user_id)
        .filter(UserGame.game_id == game_id)
    )

    if current_user_id:
        query = query.filter(UserGame.user_id != current_user_id)

    if region and region in UserGame.REGIONS:
        query = query.filter(UserGame.region == region)

    if language and language in ["PL", "EN", "RU"]:
        query = query.filter(Profile.preferred_language == language)

    if game_mode and game_mode in UserGame.GAME_MODES:
        query = query.filter(UserGame.game_mode == game_mode)

    if min_trust > 0:
        query = (
            query
            .join(TrustScore, User.id == TrustScore.user_id)
            .filter(
                TrustScore.total_ratings >= TrustScore.MIN_RATINGS_TO_SHOW,
                TrustScore.average_stars >= min_trust
            )
        )

    query = query.order_by(Profile.is_online.desc(), User.id.desc())

    total = query.count()
    user_games = query.offset((page-1) * per_page).limit(per_page).all()

    players = []
    for ug in user_games:
        player_data = {
            "user_id": ug.user_id,
            "nickname": ug.user.profile.nickname,
            "avatar_url": ug.user.profile.avatar_url or "/static/uploads/avatars/default.png",
            "bio": ug.user.profile.bio,
            "is_online": ug.user.profile.is_online,
            "preferred_language": ug.user.profile.preferred_language,
            "region": ug.region,
            "region_label": UserGame.REGION_LABELS.get(ug.region, ug.region),
            "game_mode": ug.game_mode,
            "game_mode_label": UserGame.GAME_MODE_LABELS.get(ug.game_mode, ug.game_mode),
            "discord_id": ug.user.discord_id,
            "trust_score": ug.user.trust_score.to_dict() if ug.user.trust_score else None
        }
        players.append(player_data)

    return jsonify({
        "players": players,
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
        "has_next": page * per_page < total
    })
