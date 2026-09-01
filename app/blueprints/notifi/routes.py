from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.notification_service import (
    get_user_notifications,
    get_notification_by_id,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    get_unread_notification_count
)

notification_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/notifications"
)


@notification_bp.route("", methods=["GET"])
@jwt_required()
def get_notifications():
    current_user_id = int(get_jwt_identity())

    unread_only = request.args.get(
        "unread_only",
        "false"
    ).lower() == "true"

    notifications = get_user_notifications(
        user_id=current_user_id,
        unread_only=unread_only
    )

    return jsonify({
        "notifications": [
            notification.to_dict()
            for notification in notifications
        ]
    }), 200


@notification_bp.route("/unread-count", methods=["GET"])
@jwt_required()
def get_unread_count():
    current_user_id = int(get_jwt_identity())

    unread_count = get_unread_notification_count(current_user_id)

    return jsonify({
        "unread_count": unread_count
    }), 200


@notification_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_as_read(notification_id):
    current_user_id = int(get_jwt_identity())

    notification = get_notification_by_id(notification_id)

    if not notification:
        return jsonify({
            "message": "Notification not found"
        }), 404

    if notification.user_id != current_user_id:
        return jsonify({
            "message": "You are not authorized to update this notification"
        }), 403

    updated_notification = mark_notification_as_read(notification)

    return jsonify({
        "message": "Notification marked as read",
        "notification": updated_notification.to_dict()
    }), 200


@notification_bp.route("/read-all", methods=["PATCH"])
@jwt_required()
def mark_all_as_read():
    current_user_id = int(get_jwt_identity())

    mark_all_notifications_as_read(current_user_id)

    return jsonify({
        "message": "All notifications marked as read"
    }), 200
