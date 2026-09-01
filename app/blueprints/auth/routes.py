import logging
from datetime import datetime, timezone
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, decode_token
)
from flask import Blueprint, request, jsonify

from app.extensions import db, limiter
from app.services.auth_service import register_user, AuthError, authenticate_user
from app.models import User, RevokedToken

logger = logging.getLogger(__name__)

auth_bp = Blueprint("users", __name__)


@auth_bp.route("/register", methods=['POST'])
@limiter.limit("10 per minute")
def register_route():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    try:
        user = register_user(data.get("name"), data.get("email"), data.get("password"))

    except AuthError as e:
        return jsonify({"error": e.message}), e.status_code

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    logger.info(f"User registration successful: {user.email}")
    return jsonify({"user": user.to_dict(), "access_token": access_token, "refresh_token": refresh_token}), 201


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login_route():
    """Authenticate a user and return tokens."""
    data = request.get_json(silent=True) or {}
    try:
        user = authenticate_user(data.get("email"), data.get("password"))
    except AuthError as e:
        return jsonify({"error": e.message}), e.status_code

    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    logger.info(f"User login successful: {user.email}")
    return jsonify({"user": user.to_dict(), "access_token": access_token, "refresh_token": refresh_token}), 200


@auth_bp.route("/refresh", methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    identity = get_jwt_identity()
    logger.info(f"Token refresh for user: {identity}")
    return jsonify({"access_token": create_access_token(identity=identity)}), 200


@auth_bp.route("/me", methods=['GET'])
@jwt_required()
def me():
    """Get current user information."""
    user = User.query.get_or_404(int(get_jwt_identity()))
    return jsonify(user.to_dict()), 200


def _revoke_token(jti, exp_timestamp):
    """Insert a token's jti into the revocation table if not already revoked."""
    existing = RevokedToken.query.filter_by(jti=jti).first()
    if existing:
        return
    revoked = RevokedToken(
        jti=jti,
        expires_at=datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    )
    db.session.add(revoked)


@auth_bp.route("/logout", methods=['POST'])
@jwt_required()
def logout():
    """Revoke the current access token and, if provided, its refresh token."""
    access_claims = get_jwt()
    _revoke_token(access_claims["jti"], access_claims["exp"])

    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")

    if refresh_token:
        try:
            refresh_claims = decode_token(refresh_token)
            if refresh_claims.get("type") == "refresh":
                _revoke_token(refresh_claims["jti"], refresh_claims["exp"])
        except Exception:
            logger.warning("Logout received an invalid or malformed refresh_token")

    db.session.commit()
    logger.info(f"User logged out: {get_jwt_identity()}")
    return jsonify({"message": "Logged out successfully."}), 200