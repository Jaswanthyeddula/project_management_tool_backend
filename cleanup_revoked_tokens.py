# cleanup_revoked_tokens.py
#
# Standalone maintenance script — run manually and occasionally.
# Deletes rows from revoked_tokens whose expires_at has already passed.
# These tokens would have stopped working on their own anyway (JWT expiry),
# so the row no longer serves any purpose and is safe to remove.
#
# Usage:
#   python cleanup_revoked_tokens.py

from datetime import datetime, timezone

from dotenv import load_dotenv

# Load environment variables from .env file before creating app
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import RevokedToken


def cleanup_expired_revoked_tokens():
    app = create_app()
    with app.app_context():
        now = datetime.now(timezone.utc)

        deleted_count = RevokedToken.query.filter(
            RevokedToken.expires_at < now
        ).delete(synchronize_session=False)

        db.session.commit()

        print(f"Deleted {deleted_count} expired revoked_tokens row(s).")


if __name__ == "__main__":
    cleanup_expired_revoked_tokens()