from app.extensions import db
from app.models.notification import Notification


def create_notification(user_id, notification_type, message, related_task_id=None):
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        related_task_id=related_task_id
    )

    db.session.add(notification)
    db.session.commit()

    return notification


def get_user_notifications(user_id, unread_only=False):
    query = Notification.query.filter_by(user_id=user_id)

    if unread_only:
        query = query.filter_by(is_read=False)

    return query.order_by(Notification.created_at.desc()).all()


def get_notification_by_id(notification_id):
    return db.session.get(Notification, notification_id)


def mark_notification_as_read(notification):
    notification.is_read = True
    db.session.commit()

    return notification


def mark_all_notifications_as_read(user_id):
    Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).update(
        {"is_read": True},
        synchronize_session=False
    )

    db.session.commit()


def get_unread_notification_count(user_id):
    return Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).count()
