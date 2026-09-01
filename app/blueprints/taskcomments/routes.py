from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.task_comment_service import (
    add_comment,
    get_task_comments,
    delete_comment,
    CommentError
)

task_comment_bp = Blueprint("task_comments", __name__)


@task_comment_bp.route("/tasks/<int:task_id>/comments", methods=["POST"])
@jwt_required()
def add_comment_route(task_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    content = data.get("content")

    try:
        comment = add_comment(user_id, task_id, content)
    except CommentError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"comment": comment.to_dict()}), 201


@task_comment_bp.route("/tasks/<int:task_id>/comments", methods=["GET"])
@jwt_required()
def get_task_comments_route(task_id):
    user_id = int(get_jwt_identity())

    try:
        comments = get_task_comments(user_id, task_id)
    except CommentError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"comments": [c.to_dict() for c in comments]}), 200

@task_comment_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def delete_comment_route(comment_id):
    user_id = int(get_jwt_identity())

    try:
        result = delete_comment(user_id, comment_id)
    except CommentError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"deleted": result}), 200
