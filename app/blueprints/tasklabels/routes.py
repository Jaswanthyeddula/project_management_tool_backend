from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.TaskLabel_service import (
    assign_labels_to_task,
    get_label_from_task,
    remove_label_from_task,
    filter_task_by_label,
    TasklabelError,
    _check_project_access
)

tasklabel_bp = Blueprint("task_labels", __name__)


@tasklabel_bp.route("/tasks/<int:task_id>/labels", methods=["POST"])
@jwt_required()
def assign_labels_to_task_route(task_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    label_ids = data.get("label_ids")

    try:
        labels = assign_labels_to_task(task_id, label_ids, user_id)
    except TasklabelError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"labels": labels}), 200


@tasklabel_bp.route("/tasks/<int:task_id>/labels", methods=["GET"])
@jwt_required()
def get_label_from_task_route(task_id):
    user_id = int(get_jwt_identity())

    try:
        labels = get_label_from_task(task_id, user_id)
    except TasklabelError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"labels": labels}), 200


@tasklabel_bp.route("/tasks/<int:task_id>/labels/<int:label_id>", methods=["DELETE"])
@jwt_required()
def remove_label_from_task_route(task_id, label_id):
    user_id = int(get_jwt_identity())

    try:
        result = remove_label_from_task(task_id, label_id, user_id)
    except TasklabelError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"removed": result}), 200


@tasklabel_bp.route("/projects/<int:project_id>/tasks/filter", methods=["GET"])
@jwt_required()
def filter_task_by_label_route(project_id):
    user_id = int(get_jwt_identity())

    label_ids_param = request.args.get("label_ids", "")
    try:
        label_ids = [int(x) for x in label_ids_param.split(",") if x]
    except ValueError:
        return jsonify({"error": "label_ids must be a comma-separated list of integers."}), 400

    try:
        tasks = filter_task_by_label(project_id, label_ids, user_id)
    except TasklabelError as e:
        return jsonify({"error": e.message}), e.status_code

    return jsonify({"tasks": tasks}), 200
