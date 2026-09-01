from app.extensions import db
from datetime import datetime, timezone
from app.models import TaskLabels
from app.models.project import Project
from app.models.label import Label
from app.models.project_member import ProjectMember



class LabelError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def _check_project_access(user_id, board_id):
    project  = Project.query.filter_by(id=board_id, deleted_at=None).first()
    if not project:
        raise LabelError("project not found.", 404)

    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if not member:
        raise LabelError("User is not a member of the project.", 403)

    return member

def create_label(project_id, name, color, user_id):
    member = _check_project_access(user_id, project_id)
    if member.role not in ["owner", "admin"]:
        raise LabelError("You cannot create the label", 403)
    if not isinstance(name, str) or not name.strip():
        raise LabelError("Label name is required.", 400)
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        raise LabelError("Color must be a hex value such as #ff0000.", 400)
    name = name.strip()
    existing = Label.query.filter_by(project_id=project_id, name=name, deleted_at=None).first()
    if existing:
        raise LabelError("A Label with this name in the project already exists", 409)
    label = Label(project_id=project_id, name=name, color=color, created_by=user_id)
    db.session.add(label)
    db.session.commit()
    return label

def get_labels_for_projects(project_id, user_id):
    _check_project_access(user_id, project_id)
    labels = Label.query.filter_by(project_id=project_id, deleted_at=None).all()
    return [label.to_dict() for label in labels]

def update_labels_for_projects(label_id, user_id, name=None, color=None):
    label = Label.query.filter_by(id=label_id, deleted_at=None).first()
    if not label:
        raise LabelError("Label not Found", 404)
    member = _check_project_access(user_id, label.project_id)
    if member.role not in ["owner", "admin"]:
        raise LabelError("You cannot update  the label", 403)
    if name is not None and (not isinstance(name, str) or not name.strip()):
        raise LabelError("Label name cannot be empty.", 400)
    if color is not None and (not isinstance(color, str) or len(color) != 7 or not color.startswith("#")):
        raise LabelError("Color must be a hex value such as #ff0000.", 400)
    if name and name!= label.name:
        existing = Label.query.filter_by(project_id = label.project_id, name=name, deleted_at=None).first()
        if existing:
            raise LabelError("A Label with this name in this Project already exisits", 409)
        label.name = name.strip()

    if color:
        label.color = color

    db.session.commit()
    return label

def delete_labels_for_projects(user_id, label_id):
    label = Label.query.filter_by(id=label_id, deleted_at=None).first()
    if not label:
        raise LabelError("Label not Found", 404)
    member = _check_project_access(user_id, label.project_id)
    if member.role not in ["owner", "admin"]:
        raise LabelError("You cannot delete the label.", 403)

    affected_count = TaskLabels.query.filter_by(label_id=label.id).count()
    label.deleted_at = datetime.now(timezone.utc)
    db.session.commit()
    return { "label": label.to_dict(), "affected_tasks": affected_count}


    
    
    
