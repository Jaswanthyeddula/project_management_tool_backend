from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.board_services import (
    BoardError,
    create_board,
    get_project_boards,
    get_board_by_id,
    update_board,
    delete_board,
    restore_board,
    get_deleted_boards,
    reorder_board,
    duplicate_board,
)

boards_bp = Blueprint("boards", __name__)
@boards_bp.route("/project/<int:project_id>", methods=["POST"])
@jwt_required()
def create_board_route(project_id):
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        board = create_board(
            user_id,
            project_id,
            data.get("name"),
            data.get("description")
        )

        return jsonify(board.to_dict()), 201

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/project/<int:project_id>", methods=["GET"])
@jwt_required()
def get_boards(project_id):
    try:
        user_id = int(get_jwt_identity())

        boards = get_project_boards(user_id, project_id)

        return jsonify({
            "boards": [board.to_dict() for board in boards]
        }), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/<int:board_id>", methods=["GET"])
@jwt_required()
def get_board_route(board_id):
    try:
        user_id = int(get_jwt_identity())

        board = get_board_by_id(user_id, board_id)

        return jsonify(board.to_dict()), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/<int:board_id>", methods=["PATCH"])
@jwt_required()
def update_board_route(board_id):
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        board = update_board(
            user_id,
            board_id,
            data.get("name"),
            data.get("description")
        )

        return jsonify(board.to_dict()), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/<int:board_id>", methods=["DELETE"])
@jwt_required()
def delete_board_route(board_id):
    try:
        user_id = int(get_jwt_identity())

        delete_board(user_id, board_id)

        return jsonify({"message": "Board deleted successfully."}), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code


@boards_bp.route("/<int:board_id>/restore", methods=["PATCH"])
@jwt_required()
def restore_board_route(board_id):
    
    try:
        user_id = int(get_jwt_identity())
        board = restore_board(user_id, board_id)
    except BoardError as e:
            return jsonify({"error": e.message}), e.status_code
    return jsonify(board.to_dict()), 200


@boards_bp.route("/project/<int:project_id>/deleted", methods=["GET"])
@jwt_required()
def get_deleted_boards_route(project_id):
    try:
        user_id = int(get_jwt_identity())

        boards = get_deleted_boards(user_id, project_id)

        return jsonify({
            "boards": [board.to_dict() for board in boards]
        }), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/<int:board_id>/reorder", methods=["PATCH"])
@jwt_required()
def reorder_board_route(board_id):
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json(silent=True) or {}

        board = reorder_board(
            user_id,
            board_id,
            data.get("new_order")
        )

        return jsonify(board.to_dict()), 200

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code

@boards_bp.route("/<int:board_id>/duplicate", methods=["POST"])
@jwt_required()
def duplicate_board_route(board_id):
    try:
        user_id = int(get_jwt_identity())

        board = duplicate_board(user_id, board_id)

        return jsonify(board.to_dict()), 201

    except BoardError as e:
        return jsonify({"error": e.message}), e.status_code
            
