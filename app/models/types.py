from datetime import date, datetime, time, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Store UTC datetimes without an offset and return them as UTC-aware values."""

    impl = DateTime
    cache_ok = True

    @staticmethod
    def _coerce_to_datetime(value):
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, time.min)
        return value

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        value = self._coerce_to_datetime(value)

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)

        return value.replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        value = self._coerce_to_datetime(value)

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
