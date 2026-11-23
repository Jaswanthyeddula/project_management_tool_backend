from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class ProjectMember(db.Model):
    __tablename__ = "project_members"
    __table_args__ = (db.UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = db.Column(db.Enum("owner", "admin", "member", "viewer", name="member_role"), default="member")
    joined_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    invited_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))

    project = db.relationship("Project", back_populates="members")
    user = db.relationship("User", foreign_keys=[user_id])
    inviter = db.relationship("User", foreign_keys=[invited_by])

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "invited_by": self.invited_by
        }
