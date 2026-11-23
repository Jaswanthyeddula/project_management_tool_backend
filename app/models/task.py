from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)

    board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.Enum("todo", "in_progress", "done", name="task_status"),
        default="todo",
        nullable=False,
    )
    priority = db.Column(
        db.Enum("low", "medium", "high", "urgent", name="task_priority"),
        default="medium",
        nullable=False,
    )

    position = db.Column(db.Float, default=1000, nullable=False)
    due_date = db.Column(UTCDateTime(), nullable=True)

    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(UTCDateTime(), nullable=True)

    board = db.relationship("Board", back_populates="tasks")
    assignee = db.relationship("User", foreign_keys=[assignee_id])
    creator = db.relationship("User", foreign_keys=[created_by])
    comments = db.relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    labels = db.relationship("Label", secondary="task_labels", back_populates="tasks")
    ai_task_request = db.relationship("AITaskRequest", back_populates="created_task", uselist=False)

    def to_dict(self):
        return {
            "id": self.id,
            "board_id": self.board_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee_id": self.assignee_id,
            "created_by": self.created_by,
            "position": self.position,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_via_ai": self.ai_task_request is not None,
        }