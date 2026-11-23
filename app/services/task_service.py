import logging
from typing import Optional, Union
from datetime import date, datetime, timezone
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Project, User
from app.models.board import Board
from app.models.project_member import ProjectMember
from app.models.task import Task

logger = logging.getLogger(__name__)


class TaskError(Exception):
    """Custom exception for task-related errors."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _check_board_access(user_id: int, board_id: int) -> ProjectMember:
    """
    Verify that a user has access to a board.
    
    Args:
        user_id: ID of the user
        board_id: ID of the board
        
    Returns:
        ProjectMember: The user's membership record
        
    Raises:
        TaskError: If board not found or user lacks access
    """
    board = Board.query.filter_by(id=board_id, deleted_at=None).first()
    if not board:
        raise TaskError("Board not found.", 404)

    member = ProjectMember.query.filter_by(project_id=board.project_id, user_id=user_id).first()
    if not member:
        logger.warning(f"User {user_id} attempted to access board {board_id} without permission")
        raise TaskError("User is not a member of the project.", 403)

    return member


def create_task(
    user_id: int, 
    board_id: int, 
    title: str, 
    description: Optional[str] = None, 
    priority: str = "medium", 
    due_date: Optional[Union[str, datetime, date]] = None
) -> Task:
    """
    Create a new task in a board.
    
    Args:
        user_id: ID of the user creating the task
        board_id: ID of the board to add task to
        title: Task title
        description: Task description (optional)
        priority: Task priority (low, medium, high, urgent)
        due_date: Task due date in ISO format (optional)
        
    Returns:
        Task: The newly created task
        
    Raises:
        TaskError: If validation fails or user lacks permission
    """
    if not title or not title.strip():
        logger.warning(f"Task creation attempt by user {user_id} with empty title")
        raise TaskError("Title should not be empty.", 400)
    
    member = _check_board_access(user_id, board_id)
    if member.role == "viewer":
        logger.warning(f"Viewer {user_id} attempted to create task in board {board_id}")
        raise TaskError("Viewer Cannot create task", 403)
    
    valid_priorities = ("low", "medium", "high", "urgent")
    if priority not in valid_priorities:
        raise TaskError("Priority must be low, medium, high, or urgent.", 400)
    
    if due_date is not None:
        try:
            due_date = datetime.fromisoformat(due_date) if isinstance(due_date, str) else due_date
        except ValueError:
            raise TaskError("Due date must use ISO format (YYYY-MM-DD).", 400)
        if not isinstance(due_date, (datetime, date)):
            raise TaskError("Due date must use ISO format (YYYY-MM-DD).", 400)
    
    max_position = db.session.query(db.func.max(Task.position)).filter_by(
        board_id=board_id,
        deleted_at=None,
    ).scalar()
    position = (max_position or 0.0) + 1000.0
    
    task = Task(
        board_id=board_id,
        title=title.strip(),
        description=description,
        priority=priority,
        due_date=due_date,
        created_by=user_id,
        position=position,
    )
    
    try:
        db.session.add(task)
        db.session.commit()
        logger.info(f"Task {task.id} created by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create task: {str(e)}", exc_info=True)
        raise TaskError("Failed to create task.", 500)
    
    return task


def get_board_tasks(user_id: int, board_id: int, status_filter: Optional[str] = None) -> list[Task]:
    """
    Get all tasks in a board, optionally filtered by status.
    
    Args:
        user_id: ID of the user
        board_id: ID of the board
        status_filter: Filter by status (optional)
        
    Returns:
        List[Task]: List of tasks in the board
        
    Raises:
        TaskError: If user lacks access
    """
    _check_board_access(user_id, board_id)

    query = (
        Task.query
        .options(selectinload(Task.ai_task_request))
        .filter_by(board_id=board_id, deleted_at=None)
    )

    if status_filter is not None:
        query = query.filter_by(status=status_filter)

    tasks = query.order_by(Task.position.asc()).all()
    return tasks


def _get_task_and_member(user_id: int, task_id: int) -> tuple[Task, ProjectMember]:
    """Helper to fetch a task and verify user access in a single unified check."""
    task = Task.query.filter_by(id=task_id, deleted_at=None).first()
    if not task:
        logger.warning(f"Task {task_id} not found")
        raise TaskError("Task is not Found", 404)
    member = _check_board_access(user_id, task.board_id)
    return task, member


def get_task_by_id(user_id: int, task_id: int) -> Task:
    """
    Get a specific task if user has access.
    
    Args:
        user_id: ID of the user
        task_id: ID of the task
        
    Returns:
        Task: The requested task
        
    Raises:
        TaskError: If task not found or user lacks access
    """
    task, _ = _get_task_and_member(user_id, task_id)
    return task


def update_task(
    user_id: int, 
    task_id: int, 
    title: Optional[str] = None, 
    description: Optional[str] = None, 
    priority: Optional[str] = None, 
    due_date: Optional[Union[str, datetime]] = None
) -> Task:
    """
    Update task details.
    
    Args:
        user_id: ID of the user making the update
        task_id: ID of the task
        title: New title (optional)
        description: New description (optional)
        priority: New priority (optional)
        due_date: New due date (optional)
        
    Returns:
        Task: The updated task
        
    Raises:
        TaskError: If user lacks permission or validation fails
    """
    task, member = _get_task_and_member(user_id, task_id)

    is_privileged = member.role in ("owner", "admin")
    is_assignee = task.assignee_id == user_id
    is_creator = task.created_by == user_id

    if not (is_privileged or is_assignee or is_creator):
        logger.warning(f"User {user_id} attempted to update task {task_id} without permission")
        raise TaskError("You do not have permission to update this task.", 403)

    if title is not None:
        title = title.strip()
        if not title:
            raise TaskError("Task title cannot be empty.", 400)
        task.title = title

    if description is not None:
        task.description = description

    if priority is not None:
        valid_priorities = ("low", "medium", "high", "urgent")
        if priority not in valid_priorities:
            raise TaskError("Priority must be low, medium, high, or urgent.", 400)
        task.priority = priority

    if due_date is not None:
        try:
            task.due_date = datetime.fromisoformat(due_date)
        except (TypeError, ValueError):
            raise TaskError("Due date must use ISO format (YYYY-MM-DD).", 400)

    try:
        db.session.commit()
        logger.info(f"Task {task_id} updated by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update task {task_id}: {str(e)}", exc_info=True)
        raise TaskError("Failed to update task.", 500)

    return task


def delete_task(user_id: int, task_id: int) -> bool:
    """
    Soft delete a task.
    
    Args:
        user_id: ID of the user deleting
        task_id: ID of the task
        
    Returns:
        bool: True if successful
        
    Raises:
        TaskError: If user lacks permission or task not found
    """
    task, member = _get_task_and_member(user_id, task_id)
    
    if member.role not in ("owner", "admin"):
        logger.warning(f"User {user_id} attempted to delete task {task_id} without permission")
        raise TaskError("Access is denied, You cannot delete the task.", 403)
    
    task.deleted_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        logger.info(f"Task {task_id} deleted by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete task {task_id}: {str(e)}", exc_info=True)
        raise TaskError("Failed to delete task.", 500)
    
    return True


def restore_task(user_id: int, task_id: int) -> Task:
    """
    Restore a soft-deleted task.
    
    Args:
        user_id: ID of the user restoring
        task_id: ID of the task
        
    Returns:
        Task: The restored task
        
    Raises:
        TaskError: If user lacks permission, task not found, or nothing to restore
    """
    task = Task.query.filter_by(id=task_id).first()
    if not task:
        logger.warning(f"Task {task_id} not found for restore")
        raise TaskError("Task not found", 404)
    
    member = _check_board_access(user_id, task.board_id)
    
    if member.role != "owner":
        logger.warning(f"User {user_id} attempted to restore task {task_id} without permission")
        raise TaskError("You cannot restore the task", 403)
    
    if task.deleted_at is None:
        raise TaskError("There is no task to restore.", 400)
    
    task.deleted_at = None
    
    try:
        db.session.commit()
        logger.info(f"Task {task_id} restored by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to restore task {task_id}: {str(e)}", exc_info=True)
        raise TaskError("Failed to restore task.", 500)
    
    return task


def move_task(user_id: int, task_id: int, new_status: str, new_position: Union[int, float, str]) -> Task:
    """
    Move a task to a different status and/or position.
    
    Args:
        user_id: ID of the user moving the task
        task_id: ID of the task
        new_status: New status (todo, in_progress, done)
        new_position: New position (numeric)
        
    Returns:
        Task: The updated task
        
    Raises:
        TaskError: If user lacks permission or validation fails
    """
    task, member = _get_task_and_member(user_id, task_id)

    if member.role == "viewer":
        logger.warning(f"Viewer {user_id} attempted to move task {task_id}")
        raise TaskError("You do not have permission to move this task.", 403)

    valid_statuses = ("todo", "in_progress", "done")
    if new_status not in valid_statuses:
        raise TaskError("Status must be todo, in_progress, or done.", 400)

    try:
        new_position = float(new_position)
    except (TypeError, ValueError):
        raise TaskError("Position must be a valid number.", 400)

    if new_position < 0:
        raise TaskError("Position cannot be negative.", 400)

    task.status = new_status
    task.position = new_position

    try:
        db.session.commit()
        logger.info(f"Task {task_id} moved by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to move task {task_id}: {str(e)}", exc_info=True)
        raise TaskError("Failed to move task.", 500)

    return task


def assign_task(user_id: int, task_id: int, assignee_id: Optional[int]) -> Task:
    """
    Assign a task to a user.
    
    Args:
        user_id: ID of the user assigning
        task_id: ID of the task
        assignee_id: ID of the user to assign to (None to unassign)
        
    Returns:
        Task: The updated task
        
    Raises:
        TaskError: If user lacks permission or assignee not found
    """
    task, member = _get_task_and_member(user_id, task_id)

    if member.role not in ("owner", "admin"):
        logger.warning(f"User {user_id} attempted to assign task {task_id} without permission")
        raise TaskError(
            "Only project owners and admins can assign tasks.",
            403
        )
    
    if assignee_id is not None:
        assignee = ProjectMember.query.filter_by(
            project_id=task.board.project_id,
            user_id=assignee_id
        ).first()

        if not assignee:
            logger.warning(f"Attempted to assign task to non-member user {assignee_id}")
            raise TaskError("Assignee must be a member of this project.", 400)

    old_assignee_id = task.assignee_id
    task.assignee_id = assignee_id
    
    try:
        db.session.commit()
        logger.info(f"Task {task_id} assigned by user {user_id}")

        # Send notification to the newly assigned user (if not self-assigning)
        if assignee_id and assignee_id != user_id and assignee_id != old_assignee_id:
            try:
                from app.services.notification_service import create_notification
                create_notification(
                    user_id=assignee_id,
                    notification_type="task_assigned",
                    message=f"You were assigned to task: '{task.title}'",
                    related_task_id=task.id
                )
            except Exception as notify_err:
                logger.warning(f"Failed to create notification for task assignment: {notify_err}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to assign task {task_id}: {str(e)}", exc_info=True)
        raise TaskError("Failed to assign task.", 500)

    return task
