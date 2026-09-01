# app/models/revoked_token.py

from app.extensions import db
from datetime import datetime, timezone
from app.models.types import UTCDateTime


class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    revoked_at = db.Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(UTCDateTime(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'jti': self.jti,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }