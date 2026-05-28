from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app import db, bcrypt
from app.models.user import User
from app.models.profile import Profile
from app.models.trust_score import TrustScore
from app.utils.decorators import guest_only, login_required
from app.utils.helpers import validate_age, sanitize_nickname