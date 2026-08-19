from datetime import timezone

from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator):
    """
    Stores datetimes as naive UTC under the hood and always returns
    timezone-aware UTC datetimes on read.

    Why this exists: SQLAlchemy's DateTime(timezone=True) is honored by
    Postgres (which has a real `timestamptz` type) but SQLite has no native
    timezone-aware column type -- it silently stores and returns naive
    datetimes regardless of the flag. Without this, the same code produces
    tz-aware datetimes on Postgres and naive ones on SQLite, which breaks
    equality comparisons (exactly the kind of bug that would slip past a
    quick manual test but bite the availability-vs-booked-slot matching in
    this app). Normalizing here makes behavior identical on both backends.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires timezone-aware datetimes")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)
