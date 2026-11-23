from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.task_comment import TaskComment
from app.models.task import Task
from app.services.task_service import _check_board_access

class CommentError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def add_comment(user_id, task_id, content):
    if not content or not content.strip():
        raise CommentError("Comment content cannot be empty", 400)
    if len(content) > 5000:
        raise CommentError("Comment content exceeds maximum length of 5000 characters", 400)
    
    task = Task.query.filter_by(id=task_id, deleted_at=None).first()
    if not task:
        raise CommentError("Task not found", 404)
    try:
        _check_board_access(user_id, task.board_id)
    except Exception:
        raise CommentError("You do not have permission to comment on this task", 403)

    comment = TaskComment(
        task_id=task_id,
        user_id=user_id,
        content=content.strip()
    )
    db.session.add(comment)
    db.session.commit()

    # Notify task assignee or creator about the new comment
    notify_user_id = task.assignee_id if (task.assignee_id and task.assignee_id != user_id) else (task.created_by if task.created_by != user_id else None)
    if notify_user_id:
        try:
            from app.services.notification_service import create_notification
            create_notification(
                user_id=notify_user_id,
                notification_type="task_comment",
                message=f"New comment on task: '{task.title}'",
                related_task_id=task.id
            )
        except Exception:
            pass

    return comment


def get_task_comments(user_id, task_id):
    task = Task.query.filter_by(id=task_id, deleted_at=None).first()
    if not task:
        raise CommentError("Task not found", 404)
    
    try:
        _check_board_access(user_id, task.board_id)
    except Exception:
        raise CommentError("You do not have permission to view comments on this task", 403)

    # Use joinedload to avoid N+1 queries when accessing comment.user.name
    comments = (
        TaskComment.query
        .options(joinedload(TaskComment.user))
        .filter_by(task_id=task_id)
        .order_by(TaskComment.created_at.asc())
        .all()
    )
    return comments


def delete_comment(user_id, comment_id):
    comment = TaskComment.query.filter_by(id=comment_id).first()
    if not comment:
        raise CommentError("Comment not found", 404)
    
    task = Task.query.filter_by(id=comment.task_id, deleted_at=None).first()
    if not task:
        raise CommentError("Task not found", 404)
    
    try:
        member = _check_board_access(user_id, task.board_id)
    except Exception:
        raise CommentError("You do not have permission to delete this comment", 403)
    
    is_author = comment.user_id == int(user_id)
    is_moderator = member and member.role in ['owner', 'admin']
    
    if not is_author and not is_moderator:
        raise CommentError("You do not have permission to delete this comment", 403)

    db.session.delete(comment)
    db.session.commit()
    return True
