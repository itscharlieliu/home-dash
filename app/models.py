from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class MetricSample(Base):
    """Persisted metric sample for historical lookups."""

    __tablename__ = "metric_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_id: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(JSON)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "metric_id": self.metric_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.payload,
        }

