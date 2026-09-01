from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(UTCDateTime(), nullable=True)

    owner = db.relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    boards = db.relationship("Board", back_populates="project", cascade="all, delete-orphan")
    members = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    labels = db.relationship("Label", back_populates="project", cascade="all, delete-orphan")
    ai_task_requests = db.relationship("AITaskRequest",back_populates="project",cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
