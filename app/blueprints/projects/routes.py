import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.project_service import (
    create_project, 
    get_user_projects, 
    get_projects_by_id,
    update_project, 
    delete_project, 
    restore_project,
    get_project_stats, 
    get_project_members, 
    add_member,
    update_member_role, 
    remove_member, 
    ProjectError
)

logger = logging.getLogger(__name__)

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/projects", methods=["POST"])
@jwt_required()
def create_project_route():
    """Create a new project."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        project = create_project(user_id, data.get("name"), data.get("description"))
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(project.to_dict()), 201


@projects_bp.route("/projects", methods=["GET"])
@jwt_required()
def get_user_projects_route():
    """Get all projects for the current user."""
    user_id = int(get_jwt_identity())
    projects = get_user_projects(user_id)
    return jsonify([p.to_dict() for p in projects]), 200


@projects_bp.route("/projects/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project_route(project_id):
    """Get a specific project."""
    user_id = int(get_jwt_identity())
    try:
        project = get_projects_by_id(user_id, project_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(project.to_dict()), 200


@projects_bp.route("/projects/<int:project_id>", methods=["PATCH"])
@jwt_required()
def update_project_route(project_id):
    """Update a project."""
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        project = update_project(user_id, project_id, data.get("name"), data.get("description"))
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(project.to_dict()), 200


@projects_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project_route(project_id):
    """Delete a project."""
    user_id = int(get_jwt_identity())
    try:
        delete_project(user_id, project_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"message": "Project deleted."}), 200


@projects_bp.route("/projects/<int:project_id>/restore", methods=["PATCH"])
@jwt_required()
def restore_project_route(project_id):
    """Restore a deleted project."""
    user_id = int(get_jwt_identity())
    try:
        project = restore_project(user_id, project_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(project.to_dict()), 200


@projects_bp.route("/projects/<int:project_id>/stats", methods=["GET"])
@jwt_required()
def get_project_stats_route(project_id):
    """Get project statistics."""
    user_id = int(get_jwt_identity())
    try:
        stats = get_project_stats(user_id, project_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(stats), 200


@projects_bp.route("/projects/<int:project_id>/members", methods=["GET"])
@jwt_required()
def get_project_members_route(project_id):
    """Get project members."""
    user_id = int(get_jwt_identity())
    try:
        members = get_project_members(user_id, project_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(members), 200


@projects_bp.route("/projects/<int:project_id>/members", methods=["POST"])
@jwt_required()
def add_member_route(project_id):
    """Add a member to a project."""
    requester_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        member = add_member(project_id, requester_id, data.get("user_id"), data.get("role", "member"))
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(member), 201


@projects_bp.route("/projects/<int:project_id>/members/<int:member_user_id>", methods=["PATCH"])
@jwt_required()
def update_member_role_route(project_id, member_user_id):
    """Update a member's role."""
    requester_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    try:
        member = update_member_role(project_id, requester_id, member_user_id, data.get("role"))
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify(member), 200


@projects_bp.route("/projects/<int:project_id>/members/<int:member_user_id>", methods=["DELETE"])
@jwt_required()
def remove_member_route(project_id, member_user_id):
    """Remove a member from a project."""
    requester_id = int(get_jwt_identity())
    try:
        remove_member(project_id, requester_id, member_user_id)
    except ProjectError as e:
        return jsonify({"error": e.message}), e.status_code
    return jsonify({"message": "Member removed."}), 200