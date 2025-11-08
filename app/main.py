from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import SessionLocal, engine, get_session, init_db
from .metrics.registry import MetricRegistry
from .metrics.system import DEFAULT_PROVIDERS
from .models import MetricSample
from .services.collector import MetricCollector

templates = Jinja2Templates(directory="templates")
registry = MetricRegistry()
for provider in DEFAULT_PROVIDERS:
    registry.register(provider)

collector = MetricCollector(
    registry=registry,
    session_factory=SessionLocal,
    interval_seconds=settings.sample_interval_seconds,
)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="12" fill="#111827"/>
<rect x="14" y="14" width="36" height="36" rx="8" fill="#1f2937"/>
<path d="M24 24h16v4H24zm0 8h16v4H24zm0 8h10v4H24z" fill="#38bdf8"/>
</svg>
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await collector.collect_once()
    collector.start()
    try:
        yield
    finally:
        await collector.stop()
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


def get_registry() -> MetricRegistry:
    return registry


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse("/dashboard")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.get("/dashboard")
async def dashboard(request: Request, registry: MetricRegistry = Depends(get_registry)):
    metric_definitions = [asdict(provider.definition) for provider in registry.all()]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "metrics": metric_definitions,
            "refresh_interval": settings.refresh_interval_seconds,
            "app_name": settings.app_name,
            "history_limit": settings.history_points_limit,
        },
    )


async def _latest_sample(session: AsyncSession, metric_id: str) -> Optional[Dict[str, Any]]:
    stmt = (
        select(MetricSample)
        .where(MetricSample.metric_id == metric_id)
        .order_by(MetricSample.timestamp.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    sample: Optional[MetricSample] = result.scalar_one_or_none()
    return sample.to_dict() if sample else None


async def _history_samples(
    session: AsyncSession, metric_id: str, limit: int
) -> List[Dict[str, Any]]:
    stmt = (
        select(MetricSample)
        .where(MetricSample.metric_id == metric_id)
        .order_by(MetricSample.timestamp.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    samples = list(result.scalars())
    return [sample.to_dict() for sample in reversed(samples)]


@app.get("/api/metrics")
async def read_metrics(
    include_history: bool = Query(True, alias="history"),
    session: AsyncSession = Depends(get_session),
    registry: MetricRegistry = Depends(get_registry),
):
    metrics_payload = []
    for provider in registry.all():
        definition = asdict(provider.definition)
        metric_id = definition["id"]
        latest = await _latest_sample(session, metric_id)
        payload: Dict[str, Any] = {
            "definition": definition,
            "latest": latest,
        }
        if include_history and definition.get("display", {}).get("type") == "timeseries":
            payload["history"] = await _history_samples(
                session, metric_id, settings.history_points_limit
            )
        metrics_payload.append(payload)
    return metrics_payload


@app.get("/api/metrics/{metric_id}")
async def read_metric(
    metric_id: str,
    include_history: bool = Query(False, alias="history"),
    session: AsyncSession = Depends(get_session),
    registry: MetricRegistry = Depends(get_registry),
):
    try:
        definition = asdict(registry.get(metric_id).definition)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    latest = await _latest_sample(session, metric_id)
    response: Dict[str, Any] = {"definition": definition, "latest": latest}
    if include_history:
        response["history"] = await _history_samples(
            session, metric_id, settings.history_points_limit
        )
    return response


@app.get("/api/metrics/{metric_id}/history")
async def read_metric_history(
    metric_id: str,
    limit: int = Query(settings.history_points_limit, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    registry: MetricRegistry = Depends(get_registry),
):
    try:
        registry.get(metric_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    limit = min(limit, settings.history_points_limit)
    return await _history_samples(session, metric_id, limit)


app.mount("/static", StaticFiles(directory="static"), name="static")
