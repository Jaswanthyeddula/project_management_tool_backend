from app.extensions import db
from app.models.Tasklabel import TaskLabels
from app.models.label import Label
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task


class TasklabelError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _check_project_access(user_id, project_id, allowed_roles=None):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        raise TasklabelError("Project not found.", 404)

    member = ProjectMember.query.filter_by(project_id=project.id, user_id=int(user_id)).first()
    if not member:
        raise TasklabelError("User is not a member of the project.", 403)
    if allowed_roles and member.role not in allowed_roles:
        raise TasklabelError("You do not have permission to modify task labels.", 403)
    return member


def _get_task_and_project(task_id):
    task = Task.query.filter_by(id=task_id, deleted_at=None).first()
    if not task:
        raise TasklabelError("Task not found.", 404)
    return task, task.board.project_id


def assign_labels_to_task(task_id, label_ids, user_id):
    if not isinstance(label_ids, list) or not label_ids:
        raise TasklabelError("label_ids must be a non-empty list.", 400)
    if not all(isinstance(label_id, int) for label_id in label_ids):
        raise TasklabelError("Each label ID must be an integer.", 400)

    task, project_id = _get_task_and_project(task_id)
    _check_project_access(user_id, project_id, allowed_roles=("owner", "admin", "member"))
    label_ids = list(set(label_ids))
    labels = Label.query.filter(
        Label.id.in_(label_ids),
        Label.project_id == project_id,
        Label.deleted_at.is_(None),
    ).all()
    found_ids = {label.id for label in labels}
    missing_ids = set(label_ids) - found_ids
    if missing_ids:
        raise TasklabelError(f"Labels not found in this project: {sorted(missing_ids)}", 404)

    existing_ids = {
        row.label_id for row in TaskLabels.query.filter(
            TaskLabels.task_id == task.id,
            TaskLabels.label_id.in_(label_ids),
        ).all()
    }
    for label_id in found_ids - existing_ids:
        db.session.add(TaskLabels(task_id=task.id, label_id=label_id))
    db.session.commit()
    return [label.to_dict() for label in sorted(labels, key=lambda label: label.id)]


def remove_label_from_task(task_id, label_id, user_id):
    task, project_id = _get_task_and_project(task_id)
    _check_project_access(user_id, project_id, allowed_roles=("owner", "admin", "member"))
    task_label = TaskLabels.query.filter_by(task_id=task.id, label_id=label_id).first()
    if not task_label:
        raise TasklabelError("Label is not assigned to this task.", 404)
    db.session.delete(task_label)
    db.session.commit()
    return True


def get_label_from_task(task_id, user_id):
    task, project_id = _get_task_and_project(task_id)
    _check_project_access(user_id, project_id)
    return [label.to_dict() for label in task.labels if label.deleted_at is None]


def filter_task_by_label(project_id, label_ids, user_id):
    _check_project_access(user_id, project_id)
    if not label_ids:
        return []
    tasks = (
        Task.query
        .join(TaskLabels, Task.id == TaskLabels.task_id)
        .join(Label, Label.id == TaskLabels.label_id)
        .join(Task.board)
        .filter(
            Label.project_id == project_id,
            Label.deleted_at.is_(None),
            TaskLabels.label_id.in_(label_ids),
            Task.deleted_at.is_(None),
        )
        .distinct()
        .all()
    )
    return [task.to_dict() for task in tasks]
