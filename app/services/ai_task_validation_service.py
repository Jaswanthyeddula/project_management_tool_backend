from datetime import datetime

from app.models import ProjectMember, User


class AITaskValidationError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


ALLOWED_PRIORITIES = {"low", "medium", "high", "urgent"}


def validate_ai_task_payload(parsed_payload):
    """
    Validates and normalizes the raw dict returned by parse_task_from_text.
    Raises AITaskValidationError on any invalid field.
    Returns a cleaned dict: title, description, due_date (date obj or None),
    priority (str), assignee_name (str or None).
    """
    title = (parsed_payload.get("title") or "").strip()
    if not title:
        raise AITaskValidationError(
            "MISSING_TITLE",
            "The AI could not extract a task title from your input."
        )

    description = (parsed_payload.get("description") or "").strip() or None

    raw_due_date = (parsed_payload.get("due_date") or "").strip()
    due_date = None
    if raw_due_date:
        try:
            due_date = datetime.strptime(raw_due_date, "%Y-%m-%d").date()
        except ValueError:
            raise AITaskValidationError(
                "INVALID_DUE_DATE",
                f"'{raw_due_date}' is not a valid YYYY-MM-DD date."
            )

    raw_priority = (parsed_payload.get("priority") or "").strip().lower()
    priority = raw_priority if raw_priority in ALLOWED_PRIORITIES else "medium"
    # Note: falls back to "medium" (the Task model's default) rather than
    # failing validation, since an unrecognized/missing priority isn't
    # a reason to block task creation.

    assignee_name = (parsed_payload.get("assignee_name") or "").strip() or None

    return {
        "title": title,
        "description": description,
        "due_date": due_date,
        "priority": priority,
        "assignee_name": assignee_name
    }


def resolve_assignee_by_name(project_id, assignee_name):
    """
    Resolves an assignee name to a single User within the given project.

    Returns (user_or_none, error_dict_or_none).
    If assignee_name is None, returns (None, None) — no assignee requested.
    """
    if not assignee_name:
        return None, None

    matches = (
        User.query
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(
            ProjectMember.project_id == project_id,
            User.name.ilike(f"%{assignee_name}%")
        )
        .all()
    )

    if len(matches) == 0:
        return None, {
            "status": "assignee_not_found",
            "code": "ASSIGNEE_NOT_FOUND",
            "message": f"No project member matching '{assignee_name}' was found."
        }

    if len(matches) > 1:
        return None, {
            "status": "assignee_ambiguous",
            "code": "ASSIGNEE_AMBIGUOUS",
            "message": f"Multiple project members match '{assignee_name}'.",
            "options": [{"id": u.id, "name": u.name} for u in matches]
        }

    return matches[0], None