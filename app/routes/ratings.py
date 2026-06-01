from flask import Blueprint, request, jsonify, url_for
from app import db
from app.models.trust_rating import TrustRating
from app.models.trust_score import TrustScore
from app.models.user import User
from app.utils.decorators import login_required, get_current_user

ratings_bp = Blueprint("ratings", __name__, url_prefix="/ratings")


@ratings_bp.route("/rate", methods=["POST"])
@login_required
def rate():
    current_user = get_current_user()

    rated_user_id = request.json.get("user_id") if request.is_json else request.form.get("user_id", type=int)
    stars = request.json.get("stars") if request.is_json else request.form.get("stars", type=int)
    comment = ""
    if request.is_json:
        comment = (request.json.get("comment") or "").strip()[:500]
    else:
        comment = request.form.get("comment", "").strip()[:500]

    if not rated_user_id or not stars:
        return jsonify({"error": "Missing required data."}), 400

    if rated_user_id == current_user.id:
        return jsonify({"error": "You can not rate yourself!"}), 400

    if stars not in [1, 2, 3]:
        return jsonify({"error": "Rate must be 1, 2 or 3"}), 400

    rated_user = User.query.get(rated_user_id)
    if not rated_user:
        return jsonify({"error": "User does not exist"}), 400

    existing = TrustRating.query.filter_by(
        rater_id=current_user.id,
        rated_user_id=rated_user_id
    ).first()

    if existing:
        existing.stars = stars
        existing.comment = comment or None
    else:
        rating = TrustRating(
            rater_id=current_user.id,
            rated_user_id=rated_user_id,
            stars=stars,
            comment=comment or None
        )
        db.session.add(rating)
    db.session.flush()

    trust_score = TrustScore.query.get(rated_user_id)
    if not trust_score:
        trust_score = TrustScore(user_id=rated_user_id)
        db.session.add(trust_score)
        db.session.flush()
    trust_score.recalculate()
    db.session.commit()

    return jsonify({
        "success": True,
        "trust_score": trust_score.to_dict(),
        "profile_url": url_for("profile.view", nickname=rated_user.profile.nickname)
    })


@ratings_bp.route("/user/<int:user_id>")
def get_ratings(user_id):
    page = request.args.get("page", 1, type=int)
    per_page = 10

    ratings = (
        TrustRating.query
        .filter_by(rated_user_id=user_id)
        .order_by(TrustRating.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify({
        "ratings": [r.to_dict() for r in ratings.items],
        "total": ratings.total,
        "page": page,
        "pages": ratings.pages
    })
