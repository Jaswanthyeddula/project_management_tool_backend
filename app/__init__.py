import os
import logging
from flask import Flask, jsonify
from app.config import config_by_name
from app.extensions import db, migrate, jwt, bcrypt, cors, limiter

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def create_app(env=None):
    env = env or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[env]())

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)
    limiter.init_app(app)

    from app import models  # noqa: F401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.models import RevokedToken
        jti = jwt_payload["jti"]
        token = RevokedToken.query.filter_by(jti=jti).first()
        return token is not None


def _register_blueprints(app):
    from app.blueprints.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    from app.blueprints.projects.routes import projects_bp
    app.register_blueprint(projects_bp, url_prefix="/api")
    from app.blueprints.boards.routes import boards_bp
    app.register_blueprint(boards_bp, url_prefix="/api/boards")
    from app.blueprints.tasks.routes import tasks_bp
    app.register_blueprint(tasks_bp, url_prefix="/api")
    from app.blueprints.taskcomments.routes import task_comment_bp
    app.register_blueprint(task_comment_bp, url_prefix="/api")
    from app.blueprints.labels.routes import labels_bp
    app.register_blueprint(labels_bp, url_prefix="/api")
    from app.blueprints.tasklabels.routes import tasklabel_bp
    app.register_blueprint(tasklabel_bp, url_prefix="/api")
    from app.blueprints.notifi.routes import notification_bp
    app.register_blueprint(notification_bp)
    from app.blueprints.ai.routes import ai_task_bp
    app.register_blueprint(ai_task_bp, url_prefix="/api")

def _register_error_handlers(app):
    """Register comprehensive error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(e):
        logger.warning(f"Bad request: {e.description}")
        return {
            "error": "bad_request",
            "message": e.description or "Bad request"
        }, 400

    @app.errorhandler(401)
    def unauthorized(e):
        logger.warning("Unauthorized access attempt")
        return {
            "error": "unauthorized",
            "message": "Authentication required"
        }, 401

    @app.errorhandler(403)
    def forbidden(e):
        logger.warning("Forbidden access attempt")
        return {
            "error": "forbidden",
            "message": "You do not have permission to access this resource"
        }, 403

    @app.errorhandler(404)
    def not_found(e):
        return {
            "error": "not_found",
            "message": "Resource not found"
        }, 404

    @app.errorhandler(422)
    def unprocessable_entity(e):
        logger.warning(f"Unprocessable entity: {e.description}")
        return {
            "error": "unprocessable_entity",
            "message": e.description or "Unprocessable entity"
        }, 422

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        logger.warning("Rate limit exceeded")
        return {
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later."
        }, 429

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Internal server error: {e}", exc_info=True)
        return {
            "error": "server_error",
            "message": "Something went wrong"
        }, 500