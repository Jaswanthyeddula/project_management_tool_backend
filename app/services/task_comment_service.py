# from sqlalchemy.exc import SQLAlchemyError
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
    return comment
    # try:
        
    # except SQLAlchemyError as e:
    #     raise CommentError(f"Failed to add comment: {str(e)}", 404)


def get_task_comments(user_id, task_id):
    task = Task.query.filter_by(id=task_id, deleted_at=None).first()
    if not task:
        raise CommentError("Task not found", 404)
    
    try:
        _check_board_access(user_id, task.board_id)
    except Exception:
        raise CommentError("You do not have permission to view comments on this task", 403)

    comments = TaskComment.query.filter_by(task_id=task_id).order_by(TaskComment.created_at.asc()).all()
    return comments
    
    # try:
        
    # except SQLAlchemyError as e:
    #     raise CommentError(f"Failed to fetch comments: {str(e)}", 500) 

def delete_comment(user_id, comment_id):
    comment = TaskComment.query.filter_by(id=comment_id).first()
    if not comment:
        raise CommentError("Comment not found", 404)
    
    task = Task.query.filter_by(id=comment.task_id, deleted_at=None).first()
    if not task:
        raise CommentError("Task not found", 404)
    
    try:
        _check_board_access(user_id, task.board_id)
    except Exception:
        raise CommentError("You do not have permission to delete this comment", 403)
    
    is_author = comment.user_id == int(user_id)
    
    member = _check_board_access(board_id=task.board_id, user_id=user_id)
    is_moderator = member and member.role in ['owner', 'admin']
    
    if not is_author and not is_moderator:
        raise CommentError("You do not have permission to delete this comment", 403)

    db.session.delete(comment)
    db.session.commit()
    return True
    
    # try:
        
    # except SQLAlchemyError as e:
    #     db.session.rollback()
    #     raise CommentError(f"Failed to delete comment: {str(e)}", 500)
