from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    last_login = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    owned_projects = db.relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")
    comments = db.relationship("TaskComment", back_populates="user")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    ai_task_requests = db.relationship("AITaskRequest", back_populates="requester")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'bio': self.bio,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }