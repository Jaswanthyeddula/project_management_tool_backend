
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity


from app.services import label_service
from app.services.label_service import (

    create_label,
    _check_project_access,
    LabelError,
    get_labels_for_projects,
    update_labels_for_projects,
    delete_labels_for_projects,
    
)
labels_bp = Blueprint("labels", __name__)

@labels_bp.route("/projects/<int:project_id>/labels", methods=["POST"])
@jwt_required()
def create_label_route(project_id):
    user_id  = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    try:
        label = create_label(
            project_id=project_id,
            user_id=user_id,
            name=data.get("name"),
            color=data.get("color")

        )
    except LabelError as e:
        return jsonify({"error":e.message}), e.status_code

    return jsonify({"label": label.to_dict()}), 201

@labels_bp.route("/projects/<int:project_id>/labels", methods=["GET"])
@jwt_required()
def get_label_route(project_id):
    user_id = int(get_jwt_identity())
    
    try:
        labels = get_labels_for_projects(project_id, user_id)
    except LabelError as e:
        return jsonify ({"error": e.message}), e.status_code
    return jsonify({"labels": labels  }), 200

@labels_bp.route("/labels/<int:label_id>", methods=["PATCH"])
@jwt_required()
def update_label_route(label_id):
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        label = update_labels_for_projects(label_id=label_id, user_id=user_id, name=data.get("name"), color=data.get("color"))
    except LabelError as e :
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"label": label.to_dict()}), 201

@labels_bp.route("/labels/<int:label_id>", methods=["DELETE"])
@jwt_required()
def delete_label_route(label_id):
    user_id = int(get_jwt_identity())
    try:
        result = delete_labels_for_projects(user_id, label_id)
    except LabelError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(result), 200


