from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..metrics.registry import MetricRegistry
from ..models import MetricSample


class MetricCollector:
    """Background task that periodically captures metrics into the database."""

    def __init__(
        self,
        registry: MetricRegistry,
        session_factory: async_sessionmaker[AsyncSession],
        interval_seconds: int,
    ) -> None:
        self.registry = registry
        self.session_factory = session_factory
        self.interval_seconds = max(interval_seconds, 1)
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run(), name="metric-collector")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self._collect_once()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def collect_once(self) -> None:
        await self._collect_once()

    async def _collect_once(self) -> None:
        results = self.registry.collect_all()
        timestamp = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            async with session.begin():
                for result in results:
                    sample = MetricSample(
                        metric_id=result.definition.id,
                        timestamp=timestamp,
                        payload=result.data,
                    )
                    session.add(sample)
