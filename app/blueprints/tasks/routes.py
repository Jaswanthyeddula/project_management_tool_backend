import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.task_service import (
    TaskError,
    create_task,
    get_board_tasks,
    get_task_by_id,
    update_task,
    delete_task,
    restore_task,
    move_task,
    assign_task,
)

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/boards/<int:board_id>/tasks", methods=["POST"])
@jwt_required()
def create_task_route(board_id):
    """Create a new task in a board."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        task = create_task(
            user_id=user_id,
            board_id=board_id,
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority", "medium"),
            due_date=data.get("due_date"),
        )
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 201


@tasks_bp.route("/boards/<int:board_id>/tasks", methods=["GET"])
@jwt_required()
def get_board_tasks_route(board_id):
    """Get all tasks in a board."""
    user_id = int(get_jwt_identity())
    status_filter = request.args.get("status")
    try:
        tasks = get_board_tasks(user_id, board_id, status_filter=status_filter)
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify([t.to_dict() for t in tasks]), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["GET"])
@jwt_required()
def get_task_route(task_id):
    """Get a specific task."""
    user_id = int(get_jwt_identity())
    try:
        task = get_task_by_id(user_id, task_id)
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["PATCH"])
@jwt_required()
def update_task_route(task_id):
    """Update a task."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        task = update_task(
            user_id,
            task_id,
            title=data.get("title"),
            description=data.get("description"),
            priority=data.get("priority"),
            due_date=data.get("due_date"),
        )
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@jwt_required()
def delete_task_route(task_id):
    """Delete a task."""
    user_id = int(get_jwt_identity())
    try:
        delete_task(user_id, task_id)
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"message": "Task deleted successfully."}), 200


@tasks_bp.route("/tasks/<int:task_id>/restore", methods=["PATCH"])
@jwt_required()
def restore_task_route(task_id):
    """Restore a deleted task."""
    user_id = int(get_jwt_identity())
    try:
        task = restore_task(user_id, task_id)
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>/move", methods=["PATCH"])
@jwt_required()
def move_task_route(task_id):
    """Move a task to a different status/position."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        task = move_task(
            user_id,
            task_id,
            new_status=data.get("status"),
            new_position=data.get("position"),
        )
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 200


@tasks_bp.route("/tasks/<int:task_id>/assign", methods=["PATCH"])
@jwt_required()
def assign_task_route(task_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        task = assign_task(user_id, task_id, data.get("assignee_id"))
    except TaskError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(task.to_dict()), 200