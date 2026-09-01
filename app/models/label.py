from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class Label(db.Model):
    __tablename__ = "labels"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column( db.Integer, db.ForeignKey("projects.id"), nullable=False )
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), nullable = False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(UTCDateTime(), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("project_id", "name", name="uq_label_project_name"),
        db.Index("ix_label_project_id", "project_id"),
    )
    

    project = db.relationship("Project", back_populates="labels")
    tasks = db.relationship("Task", secondary="task_labels", back_populates="labels")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "color": self.color,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }
    

