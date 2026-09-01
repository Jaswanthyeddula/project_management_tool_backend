from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class Board(db.Model):
    __tablename__ = "boards"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    position = db.Column(db.Float, default=1000)
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = db.Column(UTCDateTime(), nullable=True)

    project = db.relationship("Project", back_populates="boards")
    tasks = db.relationship("Task", back_populates="board", cascade="all, delete-orphan")
    # columns = db.relationship("BoardColumn", back_populates="board", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "position": self.position,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }