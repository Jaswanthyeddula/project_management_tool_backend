# app/routes/ai_task_routes.py

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import (
    AITaskRequest,
    Board,
    Project,
    ProjectMember,
    Task,
    User,
)
from app.services.ai_task_parser import (
    GeminiLLMError,
    GeminiParseError,
    parse_task_from_text,
)
from app.services.ai_task_validation_service import (
    AITaskValidationError,
    resolve_assignee_by_name,
    validate_ai_task_payload,
)


ai_task_bp = Blueprint(
    "ai_task_bp",
    __name__,
    url_prefix="/api"
)


@ai_task_bp.post(
    "/projects/<int:project_id>/boards/<int:board_id>/ai-tasks"
)
@jwt_required()
def create_task_from_ai(project_id, board_id):
    """
    Convert natural-language text into a Task.

    Request:
    {
      "input": "Fix the login bug by Friday, high priority, assign it to Priya"
    }
    """

    current_user = get_current_user()
    if isinstance(current_user, tuple):
        return current_user

    raw_input = get_raw_input()
    if isinstance(raw_input, tuple):
        return raw_input

    project = db.session.get(Project, project_id)
    if not project:
        return error_response(
            error="PROJECT_NOT_FOUND",
            message="Project not found.",
            status_code=404
        )

    board = db.session.get(Board, board_id)
    if not board:
        return error_response(
            error="BOARD_NOT_FOUND",
            message="Board not found.",
            status_code=404
        )

    if board.project_id != project.id:
        return error_response(
            error="BOARD_PROJECT_MISMATCH",
            message="This board does not belong to the specified project.",
            status_code=422
        )

    membership = ProjectMember.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first()

    if not membership:
        return error_response(
            error="FORBIDDEN",
            message="You are not a member of this project.",
            status_code=403
        )

    if not can_create_tasks(membership):
        return error_response(
            error="FORBIDDEN",
            message="You do not have permission to create tasks in this project.",
            status_code=403
        )

    ai_request = create_ai_request(
        project_id=project.id,
        current_user=current_user,
        raw_input=raw_input
    )

    if isinstance(ai_request, tuple):
        return ai_request

    try:
        raw_llm_response, parsed_payload = parse_task_from_text(
            raw_input=raw_input,
            current_date=datetime.now(timezone.utc).date(),
            timezone_name=getattr(project, "timezone", None) or "Asia/Kolkata"
        )

    except GeminiLLMError as exc:
        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="llm_failed",
            error_code="GEMINI_REQUEST_FAILED",
            error_message=str(exc)
        )

        return error_response(
            error="AI_SERVICE_UNAVAILABLE",
            message="The AI service could not process the task request.",
            status_code=503,
            request_id=ai_request.id
        )

    except GeminiParseError as exc:
        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="parse_failed",
            error_code="INVALID_STRUCTURED_OUTPUT",
            error_message=str(exc)
        )

        return error_response(
            error="AI_PARSE_FAILED",
            message="The AI response could not be interpreted as task data.",
            status_code=422,
            request_id=ai_request.id
        )

    except Exception:
        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="llm_failed",
            error_code="UNEXPECTED_AI_ERROR",
            error_message="Unexpected error while calling the AI provider."
        )

        return error_response(
            error="AI_SERVICE_UNAVAILABLE",
            message="The AI service could not process the task request.",
            status_code=503,
            request_id=ai_request.id
        )

    try:
        ai_request.llm_response_raw = serialize_for_audit(raw_llm_response)
        ai_request.parsed_payload = parsed_payload
        db.session.commit()

    except Exception:
        db.session.rollback()

        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="task_creation_failed",
            error_code="AI_AUDIT_UPDATE_FAILED",
            error_message="Could not save the AI extraction result."
        )

        return error_response(
            error="AI_AUDIT_UPDATE_FAILED",
            message="Could not save the AI extraction result.",
            status_code=500,
            request_id=ai_request.id
        )

    try:
        validated_data = validate_ai_task_payload(parsed_payload)

    except AITaskValidationError as exc:
        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="validation_failed",
            error_code=exc.code,
            error_message=exc.message
        )

        return error_response(
            error="AI_VALIDATION_FAILED",
            message=exc.message,
            status_code=422,
            request_id=ai_request.id,
            ai_task_request=ai_request.to_dict()
        )

    assignee, assignee_error = resolve_assignee_by_name(
        project_id=project.id,
        assignee_name=validated_data["assignee_name"]
    )

    if assignee_error:
        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status=assignee_error["status"],
            error_code=assignee_error["code"],
            error_message=assignee_error["message"]
        )

        return error_response(
            error=assignee_error["code"],
            message=assignee_error["message"],
            status_code=422,
            request_id=ai_request.id,
            ai_task_request=ai_request.to_dict(),
            assignee_options=assignee_error.get("options", [])
        )

    return create_task_and_mark_success(
        ai_request=ai_request,
        board=board,
        current_user=current_user,
        validated_data=validated_data,
        assignee=assignee
    )


def create_ai_request(project_id, current_user, raw_input):
    """
    Persist the audit record before making the Gemini request.
    """

    requester_name_snapshot = (
        getattr(current_user, "name", None)
        or getattr(current_user, "username", None)
        or f"User {current_user.id}"
    )

    ai_request = AITaskRequest(
        project_id=project_id,
        requested_by_id=current_user.id,
        requested_by_name_snapshot=requester_name_snapshot,
        raw_input=raw_input,
        llm_provider="gemini",
        llm_model="gemini-2.5-flash",
        status="processing",
        created_at=datetime.now(timezone.utc)
    )

    try:
        db.session.add(ai_request)
        db.session.commit()
        return ai_request

    except Exception:
        db.session.rollback()

        return error_response(
            error="AI_REQUEST_CREATION_FAILED",
            message="Could not create the AI task request audit record.",
            status_code=500
        )


def create_task_and_mark_success(
    ai_request,
    board,
    current_user,
    validated_data,
    assignee
):
    """
    Create Task and update AITaskRequest to success in one transaction.
    """

    try:
        task = Task(
            board_id=board.id,
            title=validated_data["title"],
            description=validated_data["description"],
            due_date=validated_data["due_date"],
            priority=validated_data["priority"],
            assignee_id=assignee.id if assignee else None,
            created_by=current_user.id,
            status="todo"
        )

        db.session.add(task)
        db.session.flush()

        ai_request.mark_success(task.id)

        db.session.commit()

        return jsonify({
            "message": "Task created successfully from AI input.",
            "task": task.to_dict(),
            "ai_task_request": ai_request.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        mark_failed_and_commit(
            ai_request=ai_request,
            failure_status="task_creation_failed",
            error_code="TASK_CREATION_FAILED",
            error_message="The validated AI task could not be saved."
        )

        return error_response(
            error="TASK_CREATION_FAILED",
            message="The task could not be created.",
            status_code=500,
            request_id=ai_request.id
        )


def mark_failed_and_commit(
    ai_request,
    failure_status,
    error_code,
    error_message
):
    """
    Roll back any failed database transaction, reload the request record,
    mark it with a terminal failure status, and commit that audit outcome.
    """

    try:
        db.session.rollback()

        fresh_ai_request = db.session.get(
            AITaskRequest,
            ai_request.id
        )

        if not fresh_ai_request:
            return

        fresh_ai_request.mark_failed(
            failure_status=failure_status,
            error_code=error_code,
            error_message=error_message
        )

        db.session.commit()

    except Exception:
        db.session.rollback()


def get_current_user():
    """
    JWT identity convention in this project: str(user.id).
    """

    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return error_response(
            error="UNAUTHORIZED",
            message="Invalid authentication identity.",
            status_code=401
        )

    current_user = db.session.get(User, user_id)

    if not current_user:
        return error_response(
            error="UNAUTHORIZED",
            message="User account no longer exists.",
            status_code=401
        )

    return current_user


def get_raw_input():
    body = request.get_json(silent=True) or {}
    raw_input = body.get("input")

    if not isinstance(raw_input, str):
        return error_response(
            error="VALIDATION_ERROR",
            message="The 'input' field must be a string.",
            status_code=400
        )

    raw_input = raw_input.strip()

    if not raw_input:
        return error_response(
            error="VALIDATION_ERROR",
            message="The 'input' field cannot be empty.",
            status_code=400
        )

    if len(raw_input) > 2000:
        return error_response(
            error="VALIDATION_ERROR",
            message="The 'input' field must be 2000 characters or fewer.",
            status_code=400
        )

    return raw_input


def can_create_tasks(membership):
    """
    Match the role values used by your existing ProjectMember model.
    """

    return membership.role in {"owner", "admin", "member"}


def serialize_for_audit(value):
    """
    A safe audit serializer for a dict, Pydantic model, SDK object, or string.

    Do not expose this stored raw output in the normal frontend API response.
    """

    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        import json
        return json.dumps(value, ensure_ascii=False, default=str)

    if hasattr(value, "model_dump"):
        import json
        return json.dumps(
            value.model_dump(),
            ensure_ascii=False,
            default=str
        )

    return str(value)


def error_response(error, message, status_code, **extra):
    response_body = {
        "error": error,
        "message": message
    }

    response_body.update(extra)

    return jsonify(response_body), status_code