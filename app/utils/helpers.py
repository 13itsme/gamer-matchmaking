import os
import uuid
from flask import current_app


def allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_avatar(file):
    if not file or not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    return f"/static/uploads/avatars/{filename}"

def delete_avatar(avatar_url):
    if not avatar_url or "default" in avatar_url:
        return
    relative_path = avatar_url.lstrip("/")
    full_path = os.path.join(current_app.root_path, "..", relative_path)
    full_path = os.path.normpath(full_path)
    if os.path.exists(full_path):
        os.remove(full_path)


def validate_age(age):
    try:
        age = int(age)
        return 13<= age <= 120
    except (TypeError, ValueError):
        return False

def sanitize_nickname(nickname):
    import re
    if not nickname:
        return None
    nickname = nickname.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]{3,50}$", nickname):
        return None
    return nickname

def get_chat_room_id(user_id_1, user_id_2):
    ids = sorted([user_id_1, user_id_2])
    return f"chat_{ids[0]}_{ids[1]}"

def format_datetime(dt):
    if not dt:
        return ""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt

    if delta.days == 0:
        if delta.seconds < 60:
            return "just now"
        elif delta.seconds < 3600:
            mins = delta.seconds // 60
            return f"{mins} minutes ago"
        else:
            hours = delta.seconds // 3600
            return f"{hours} hours ago"
    elif delta.days == 1:
        return "yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        return dt.strftime("%d.%m.%Y")