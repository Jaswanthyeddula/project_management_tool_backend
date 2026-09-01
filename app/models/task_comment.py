from app import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime

class TaskComment(db.Model):
    __tablename__ = 'task_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    task = db.relationship('Task', back_populates='comments')
    user = db.relationship('User', back_populates='comments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'content': self.content,
            'created_at': self.created_at.isoformat()
        }
