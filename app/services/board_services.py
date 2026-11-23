from app.extensions import db
from app.models.board import Board
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from datetime import datetime, timezone


class BoardError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _check_project_membership(user_id, project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        raise BoardError("Project not found.", 404)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if not member:
        raise BoardError("User is not a member of the project.", 403)

    return member


def create_board(user_id, project_id, name, description=None):
    if not name or not name.strip():
        raise BoardError("Board name is required.", 400)

    member = _check_project_membership(user_id, project_id)
    if member.role == "viewer":
        raise BoardError("User does not have permission to create a board.", 403)

    board = Board(name=name.strip(), description=description, project_id=project_id)
    db.session.add(board)
    db.session.commit()
    return board


def get_project_boards(user_id, project_id):
    _check_project_membership(user_id, project_id)

    boards = (
        Board.query
        .filter_by(project_id=project_id, deleted_at=None)
        .order_by(Board.position.asc())
        .all()
    )

    return boards


def get_board_by_id(user_id, board_id):
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise BoardError("Board not found.", 404)

    _check_project_membership(user_id, board.project_id)
    return board


def update_board(user_id, board_id, name=None, description=None):
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise BoardError("Board not found.", 404)
    member = _check_project_membership(user_id, board.project_id)
    if member.role == "viewer":
        raise BoardError("User does not have permission to update the board.", 403)
    if name is not None:
        stripped = name.strip()
        if not stripped:
            raise BoardError("Board name cannot be empty.", 400)
        board.name = stripped
        
    if description is not None:
        board.description = description
    db.session.commit()
    return board


def delete_board(user_id, board_id):
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise BoardError("Board not found.", 404)
    member = _check_project_membership(user_id, board.project_id)
    if member.role not in ["admin", "owner"]:
        raise BoardError("User does not have permission to delete the board.", 403)
    board.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return True


def restore_board(user_id, board_id):
    board = Board.query.filter_by(id=board_id).first()
    if not board:
        raise BoardError("Board not found.", 404)
    
    member = _check_project_membership(user_id, board.project_id)
    if member.role != "owner":
        raise BoardError("User does not have permission to restore the board.", 403)
    if board.deleted_at is None:
        raise BoardError("Board is not deleted.", 400)
    board.deleted_at = None
    db.session.commit()
    return board


def get_deleted_boards(user_id, project_id):
    _check_project_membership(user_id, project_id)
    boards = Board.query.filter_by(project_id=project_id).filter(Board.deleted_at.isnot(None)).all()
    return boards


def reorder_board(user_id, board_id, new_order):
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise BoardError("Board not found.", 404)
    member = _check_project_membership(user_id, board.project_id)
    if member.role == "viewer":
        raise BoardError("User does not have permission to reorder the board.", 403)
    try:
        new_order = float(new_order)
    except (ValueError, TypeError):
        raise BoardError("Invalid order value.", 400)
    if new_order < 0:
        raise BoardError("Order value cannot be negative.", 400)
    board.position = new_order
    db.session.commit()
    return board


def duplicate_board(user_id, board_id):
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise BoardError("Board not found.", 404)
    member = _check_project_membership(user_id, board.project_id)
    if member.role == "viewer":
        raise BoardError("User does not have permission to duplicate the board.", 403)
    new_board = Board(
        name=f"{board.name} (Copy)",
        description=board.description,
        project_id=board.project_id,
        position=board.position + 1
    )
    db.session.add(new_board)
    db.session.flush()

    # Duplicate active tasks from original board into new board
    for original_task in board.tasks:
        if original_task.deleted_at is None:
            new_task = Task(
                board_id=new_board.id,
                title=original_task.title,
                description=original_task.description,
                status=original_task.status,
                priority=original_task.priority,
                position=original_task.position,
                due_date=original_task.due_date,
                created_by=user_id
            )
            db.session.add(new_task)

    db.session.commit()
    return new_board
