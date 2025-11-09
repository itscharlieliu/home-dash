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

#### Start the server

```bash
./start.sh
```

The script provisions the virtual environment and runs Uvicorn in the background. Logs are written to `logs/uvicorn.log`, and the active process ID is stored in `.uvicorn.pid`.

#### Stop the server

```bash
./stop.sh
```

This terminates the background Uvicorn process and removes the PID file. If the PID file is missing or stale, the script handles cleanup for you.

Once the server is running, visit `http://localhost:8000/dashboard`.

### Start automatically on Linux (systemd user service)

1. Confirm that the path in `support/systemd/home-dash.service` matches the location of your checkout. Update the `WorkingDirectory`, `ExecStart`, `ExecStop`, and `PIDFile` entries if your project lives somewhere other than `~/Documents/projects/home-dash`.
2. Copy the service file into your user systemd directory:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp support/systemd/home-dash.service ~/.config/systemd/user/
   ```
3. Reload and enable the service:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now home-dash.service
   ```
4. The dashboard now starts automatically when you log in. Stop it with `systemctl --user stop home-dash.service`, disable permanent autostart with `systemctl --user disable home-dash.service`, and view logs via `journalctl --user -u home-dash.service`.

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
