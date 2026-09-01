from sqlalchemy import ForeignKey
from app.extensions import db

class TaskLabels(db.Model):
    __tablename__ = "task_labels"

    task_id = db.Column(db.Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    label_id = db.Column(db.Integer, ForeignKey("labels.id", ondelete="CASCADE"), nullable=False, primary_key=True)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "label_id": self.label_id,
        }
    


