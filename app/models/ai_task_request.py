# app/models/ai_task_request.py

from datetime import datetime, timezone
from app.models.types import UTCDateTime

from app.extensions import db


class AITaskRequest(db.Model):
    __tablename__ = "ai_task_requests"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    requested_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    created_task_id = db.Column(
        db.Integer,
        db.ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        unique=True
    )

    requested_by_name_snapshot = db.Column(
        db.String(255),
        nullable=True
    )

    raw_input = db.Column(
        db.Text,
        nullable=False
    )

    llm_provider = db.Column(
        db.String(50),
        nullable=True
    )

    llm_model = db.Column(
        db.String(150),
        nullable=True
    )

    llm_response_raw = db.Column(
        db.Text,
        nullable=True
    )

    parsed_payload = db.Column(
        db.JSON,
        nullable=True
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="processing",
        index=True
    )

    error_code = db.Column(
        db.String(100),
        nullable=True
    )

    error_message = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    completed_at = db.Column(
        UTCDateTime(),
        nullable=True
    )

    project = db.relationship(
        "Project",
        back_populates="ai_task_requests",
        foreign_keys=[project_id]
    )

    requester = db.relationship(
        "User",
        back_populates="ai_task_requests",
        foreign_keys=[requested_by_id]
    )

    created_task = db.relationship(
        "Task",
        back_populates="ai_task_request",
        foreign_keys=[created_task_id]
    )

    def mark_failed(self, failure_status, error_code, error_message):
        """
        Mark this request as terminally unsuccessful.

        failure_status must be a failure state such as:
        - parse_failed
        - validation_failed
        - assignee_not_found
        - assignee_ambiguous
        - llm_failed
        - task_creation_failed
        """

        allowed_failure_statuses = {
            "parse_failed",
            "validation_failed",
            "assignee_not_found",
            "assignee_ambiguous",
            "llm_failed",
            "task_creation_failed"
        }

        if failure_status not in allowed_failure_statuses:
            raise ValueError(
                f"Invalid failure status: '{failure_status}'."
            )

        self.status = failure_status
        self.error_code = error_code
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)

    def mark_success(self, task_id):
        """
        Mark this request as successfully converted into a Task.
        """

        self.status = "success"
        self.created_task_id = task_id
        self.error_code = None
        self.error_message = None
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(
        self,
        include_input=False,
        include_llm_metadata=False,
        include_raw_llm_response=False
    ):
        """
        Serialize this request for an API response.

        Safe default:
        - Includes status, parsed output, errors, and timestamps.
        - Excludes raw user input.
        - Excludes raw LLM response.
        - Excludes provider/model metadata.

        Use include_input=True only when the caller is allowed to view the
        original prompt. Use include_raw_llm_response=True only for internal
        admin/debug endpoints.
        """

        data = {
            "id": self.id,
            "project_id": self.project_id,
            "requested_by_id": self.requested_by_id,
            "requested_by_name": self.requested_by_name_snapshot,
            "created_task_id": self.created_task_id,
            "status": self.status,
            "parsed_payload": self.parsed_payload,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),
            "completed_at": (
                self.completed_at.isoformat()
                if self.completed_at else None
            )
        }

        if include_input:
            data["raw_input"] = self.raw_input

        if include_llm_metadata:
            data["llm_provider"] = self.llm_provider
            data["llm_model"] = self.llm_model

        if include_raw_llm_response:
            data["llm_response_raw"] = self.llm_response_raw

        return data