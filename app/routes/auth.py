from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db, bcrypt
from app.models.user import User
from app.models.profile import Profile
from app.models.trust_score import TrustScore
from app.utils.decorators import guest_only, login_required
from app.utils.helpers import validate_age, sanitize_nickname

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
@guest_only
def register():
    if request.method == "GET":
        return render_template("auth/register.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    nickname = request.form.get("nickname", "").strip()
    real_name = request.form.get("real_name", "").strip()
    age = request.form.get("age", "")
    discord_id = request.form.get("discord_id", "").strip()
    preferred_language = request.form.get("preferred_language", "EN")
    rodo_consent = request.form.get("rodo_consent") == "on"

    errors = []

    if not email or "@" not in email:
        errors.append("Incorrect email")

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if password != confirm_password:
        errors.append("Passwords aren't the same")

    clean_nickname = sanitize_nickname(nickname)
    if not clean_nickname:
        errors.append("Nick can be filled only by letters, digits and '-', '_' marks (3-50 long)")

    if age and not validate_age(age):
        errors.append("You must be at least 13 y.o")

    if not rodo_consent:
        errors.append("You must agree to data processing policy")

    if preferred_language not in ["PL", "EN", "RU"]:
        preferred_language = "EN"

    # Email and Nickname must be Unique
    if User.query.filter_by(email=email).first():
        errors.append("This email is already registered")

    if Profile.query.filter_by(nickname=clean_nickname).first():
        errors.append("This nickname is already taken")

    if errors:
        for error in errors:
            flash(error, "error")
        return render_template("auth/register.html", form_data=request.form)

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    user = User(
        email=email,
        password_hash=password_hash,
        real_name=real_name or None,
        age=int(age) if age else None,
        discord_id=discord_id or None,
        rodo_consent=True
    )
    db.session.add(user)
    db.session.flush()

    profile = Profile(
        user_id=user.id,
        nickname=clean_nickname,
        preferred_language=preferred_language
    )
    db.session.add(profile)

    trust_score = TrustScore(user_id=user.id)
    db.session.add(trust_score)

    db.session.commit()

    flash("Profile has been successfully created!", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
@guest_only
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Please, enter your email and password", "error")
        return render_template("auth/login.html")

    user = User.query.filter_by(email=email).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        flash("Incorrect password or email", "error")
        return render_template("auth/login.html")

    session.permanent = True
    session["user_id"] = user.id
    session["nickname"] = user.profile.nickname if user.profile else "Gamer"

    if user.profile:
        user.profile.is_online = True
        db.session.commit()

    flash(f"Hello {session['nickname']}!", "success")
    next_page = request.args.get("next")
    return redirect(next_page or url_for("games.index"))


@auth_bp.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user and user.profile:
            user.profile.is_online = False
            db.session.commit()
    session.clear()
    flash("You have been successfully logged out", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    user_id = session.get("user_id")
    password = request.form.get("password", "")

    user = User.query.get(user_id)
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        flash("Incorrect password. Account wasn't deleted", "error")
        return redirect(url_for("profile.edit"))

    db.session.delete(user)
    db.session.commit()
    session.clear()

    flash("Your account has been successfully deleted", "info")
    return redirect(url_for("auth.login"))