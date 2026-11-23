import logging
from typing import Optional
from datetime import datetime, timezone

from app.extensions import db
from app.models import Project, User
from app.models.board import Board
from app.models.project_member import ProjectMember

logger = logging.getLogger(__name__)


class ProjectError(Exception):
    """Custom exception for project-related errors."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def create_project(user_id: int, name: Optional[str], description: Optional[str] = None) -> Project:
    """
    Create a new project and add the creator as owner.
    
    Args:
        user_id: ID of the user creating the project
        name: Project name
        description: Project description (optional)
        
    Returns:
        Project: The newly created project
        
    Raises:
        ProjectError: If name is empty or project creation fails
    """
    if not name or not name.strip():
        logger.warning(f"Project creation attempt by user {user_id} with empty name")
        raise ProjectError("Project name is required.", 400)

    try:
        project = Project(name=name.strip(), description=description, owner_id=user_id)
        db.session.add(project)
        db.session.flush()

        member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role="owner"
        )
        db.session.add(member)
        db.session.commit()
        logger.info(f"Project created: {project.id} by user {user_id}")
        return project
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create project: {str(e)}", exc_info=True)
        raise ProjectError("Failed to create project.", 500)


def get_user_projects(user_id: int) -> list[Project]:
    """
    Get all projects for a specific user.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List[Project]: List of projects the user is a member of
    """
    return (
        Project.query
        .join(ProjectMember)
        .filter(ProjectMember.user_id == user_id)
        .filter(Project.deleted_at.is_(None))
        .all()
    )


def get_projects_by_id(user_id: int, project_id: int) -> Project:
    """
    Get a specific project if user has access.
    
    Args:
        user_id: ID of the user
        project_id: ID of the project
        
    Returns:
        Project: The requested project
        
    Raises:
        ProjectError: If project not found or user doesn't have access
    """
    project = Project.query.filter_by(id=project_id, deleted_at=None).first()
    if not project:
        logger.warning(f"Project {project_id} not found")
        raise ProjectError("Project not found.", 404)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if not member:
        logger.warning(f"User {user_id} attempted to access project {project_id} without permission")
        raise ProjectError("Project not found.", 404)

    return project


def update_project(user_id: int, project_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Project:
    """
    Update a project's name and/or description.
    
    Args:
        user_id: ID of the user making the update
        project_id: ID of the project
        name: New project name (optional)
        description: New project description (optional)
        
    Returns:
        Project: The updated project
        
    Raises:
        ProjectError: If user lacks permission or project not found
    """
    project = get_projects_by_id(user_id, project_id)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if member.role not in ("owner", "admin"):
        logger.warning(f"User {user_id} attempted to update project {project_id} without permission")
        raise ProjectError("You do not have permission to update this project.", 403)

    if name is not None:
        project.name = name.strip()
    if description is not None:
        project.description = description

    try:
        db.session.commit()
        logger.info(f"Project {project_id} updated by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update project {project_id}: {str(e)}", exc_info=True)
        raise ProjectError("Failed to update project.", 500)

    return project


def delete_project(user_id: int, project_id: int) -> bool:
    """
    Soft delete a project (marks deleted_at).
    
    Args:
        user_id: ID of the user deleting
        project_id: ID of the project to delete
        
    Returns:
        bool: True if successful
        
    Raises:
        ProjectError: If user lacks permission or project not found
    """
    project = get_projects_by_id(user_id, project_id)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if member.role not in ("owner", "admin"):
        logger.warning(f"User {user_id} attempted to delete project {project_id} without permission")
        raise ProjectError("You do not have permission to delete this project.", 403)

    project.deleted_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        logger.info(f"Project {project_id} deleted by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete project {project_id}: {str(e)}", exc_info=True)
        raise ProjectError("Failed to delete project.", 500)

    return True


def restore_project(user_id: int, project_id: int) -> Project:
    """
    Restore a soft-deleted project.
    
    Args:
        user_id: ID of the user restoring
        project_id: ID of the project to restore
        
    Returns:
        Project: The restored project
        
    Raises:
        ProjectError: If user lacks permission, project not found, or nothing to restore
    """
    project = Project.query.filter_by(id=project_id).first()
    if not project:
        logger.warning(f"Project {project_id} not found for restore")
        raise ProjectError("Project not found.", 404)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first()
    if not member or member.role != "owner":
        logger.warning(f"User {user_id} attempted to restore project {project_id} without permission")
        raise ProjectError("You do not have permission to restore this project.", 403)

    if project.deleted_at is None:
        logger.warning(f"Attempted to restore non-deleted project {project_id}")
        raise ProjectError("There is no project to restore.", 400)

    project.deleted_at = None
    
    try:
        db.session.commit()
        logger.info(f"Project {project_id} restored by user {user_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to restore project {project_id}: {str(e)}", exc_info=True)
        raise ProjectError("Failed to restore project.", 500)

    return project


def get_project_stats(user_id, project_id):
    project = get_projects_by_id(user_id, project_id)

    member_count = ProjectMember.query.filter_by(project_id=project_id).count()
    board_count = Board.query.filter_by(project_id=project_id).count()

    return {
        "project_id": project.id,
        "project_name": project.name,
        "member_count": member_count,
        "board_count": board_count
    }


def get_project_members(user_id, project_id):
    get_projects_by_id(user_id, project_id)
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    return [member.to_dict() for member in members]


def add_member(project_id, requester_id, targeted_id, role="member"):
    get_projects_by_id(requester_id, project_id)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=requester_id).first()
    if member.role not in ("owner", "admin"):
        raise ProjectError("You do not have permission to add members to this project.", 403)

    if member.role == "admin" and role == "owner":
        raise ProjectError("Admins cannot add owners to the project.", 403)

    valid_roles = ["owner", "admin", "member", "viewer"]
    if role not in valid_roles:
        raise ProjectError(f"Invalid role. Valid roles are: {', '.join(valid_roles)}", 400)

    target_user = User.query.filter_by(id=targeted_id).first()
    if not target_user:
        raise ProjectError("Targeted user not found.", 404)

    existing_member = ProjectMember.query.filter_by(project_id=project_id, user_id=targeted_id).first()
    if existing_member:
        raise ProjectError("User is already a member of this project.", 409)

    new_member = ProjectMember(project_id=project_id, user_id=targeted_id, role=role, invited_by=requester_id)
    db.session.add(new_member)
    db.session.commit()
    return new_member.to_dict()


def update_member_role(project_id, requester_id, targeted_id, new_role):
    get_projects_by_id(requester_id, project_id)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=requester_id).first()
    if member.role not in ("owner", "admin"):
        raise ProjectError("You do not have permission to update member roles in this project.", 403)

    if member.role == "admin" and new_role == "owner":
        raise ProjectError("Admins cannot promote members to owners.", 403)

    valid_roles = ["owner", "admin", "member", "viewer"]
    if new_role not in valid_roles:
        raise ProjectError(f"Invalid role. Valid roles are: {', '.join(valid_roles)}", 400)

    target_member = ProjectMember.query.filter_by(project_id=project_id, user_id=targeted_id).first()
    if not target_member:
        raise ProjectError("User is not a member of this project.", 404)

    # Admins cannot change other admins or owners
    if member.role == "admin" and target_member.role in ("admin", "owner"):
        raise ProjectError("Admins cannot modify the role of another admin or owner.", 403)

    if target_member.role == "owner" and new_role != "owner":
        if member.role != "owner":
            raise ProjectError("Only owners can change the role of an owner.", 403)
        owner_count = ProjectMember.query.filter_by(project_id=project_id, role="owner").count()
        if owner_count <= 1:
            raise ProjectError("Cannot change the role of the only project owner.", 403)

    target_member.role = new_role
    db.session.commit()
    return target_member.to_dict()


def remove_member(project_id, requester_id, targeted_id):
    get_projects_by_id(requester_id, project_id)

    member = ProjectMember.query.filter_by(project_id=project_id, user_id=requester_id).first()
    is_self_removal = (requester_id == targeted_id)

    if not is_self_removal and member.role not in ("owner", "admin"):
        raise ProjectError("You do not have permission to remove members from this project.", 403)

    target_member = ProjectMember.query.filter_by(project_id=project_id, user_id=targeted_id).first()
    if not target_member:
        raise ProjectError("User is not a member of this project.", 404)

    # Admins cannot remove other admins or owners
    if not is_self_removal and member.role == "admin" and target_member.role in ("admin", "owner"):
        raise ProjectError("Admins cannot remove other admins or owners.", 403)

    if target_member.role == "owner":
        owner_count = ProjectMember.query.filter_by(project_id=project_id, role="owner").count()
        if owner_count <= 1:
            raise ProjectError("Cannot remove the only project owner.", 403)
        if not is_self_removal and member.role != "owner":
            raise ProjectError("Only project owners can remove another owner.", 403)

    db.session.delete(target_member)
    db.session.commit()
    return True
