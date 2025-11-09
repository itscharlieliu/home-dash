# Home Dash

Lightweight FastAPI dashboard that exposes system metrics via a web UI and JSON API. Built to run easily inside Docker and designed for extension with custom metric providers.

## Features

- Real-time system metrics for CPU, memory, disk, and network using `psutil`
- Modular `MetricProvider` abstraction for adding new metrics (system or external APIs)
- Responsive dashboard UI with automatic refresh and per-metric display types (charts, tables, raw JSON)
- Historical storage of metrics in SQLite for time-series charts and API access
- JSON API for integrating the metrics with other tooling

## Getting Started

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/dashboard`.

## Extending Metrics

Create a new metric provider by subclassing `MetricProvider` and registering it in `app/main.py` or another startup module:

```python
from app.metrics.base import MetricDefinition, MetricDisplayConfig, MetricProvider


class WeatherMetric(MetricProvider):
    definition = MetricDefinition(
        id="weather",
        name="Local Weather",
        description="Current weather from the external API.",
        category="external",
        display=MetricDisplayConfig(
            type="timeseries",
            series={"Temperature °C": "temperature_c"},
            unit="°C",
        ),
    )

    def collect(self) -> dict:
        # fetch from external API
        return {"temperature_c": 21.2, "condition": "Sunny"}
```

Then register the provider:

```python
from app.metrics.registry import MetricRegistry
from .metrics.weather import WeatherMetric

registry = MetricRegistry()
registry.register(WeatherMetric())
```

The new metric automatically appears in the dashboard and the `/api/metrics` endpoint.

## Project Structure

- `app/main.py` – FastAPI application bootstrap
- `app/metrics/` – metric abstraction and providers
- `app/models.py` – SQLAlchemy models for persisted samples
- `templates/` – Jinja templates for the dashboard UI
- `static/` – frontend assets (CSS/JS)
- `Dockerfile` – container runtime definition

## Roadmap Ideas

- Historical data storage and charts
- Authentication / access control
- Websocket push updates
- Pluggable configuration via YAML or database
