from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.types import TypeDecorator

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime only accepts timezone-aware datetimes")
        return value.astimezone(timezone.utc)

    def process_result_value(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class MetricSample(Base):
    """Persisted metric sample for historical lookups."""

    __tablename__ = "metric_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    payload: Mapped[dict] = mapped_column(JSON)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "timestamp": self.timestamp.isoformat(),  # Stored in UTC
            "data": self.payload,
        }
