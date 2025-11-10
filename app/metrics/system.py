import platform
import time
from typing import Any, Dict, List, Optional

import psutil

from .base import MetricDefinition, MetricDisplayConfig, MetricProvider


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
    if value is None:
        return "0 B"
    negative = value < 0
    size = float(abs(value))
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            break
        size /= 1024.0
    formatted = f"{size:.2f}".rstrip("0").rstrip(".")
    result = f"{formatted} {unit}"
    return f"-{result}" if negative else result


class CPUMetric(MetricProvider):
    definition = MetricDefinition(
        id="cpu",
        name="CPU Load",
        description="Current CPU utilisation across cores.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={"Total %": "percent_total"},
            unit="%",
        ),
    )

    def collect(self) -> Dict[str, Any]:
        per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        total = (
            sum(per_core) / len(per_core)
            if per_core
            else psutil.cpu_percent(interval=None)
        )
        return {
            "timestamp": time.time(),
            "logical_cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
            "percent_total": total,
            "percent_per_core": [value for value in per_core],
            "load_average": (
                list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else None
            ),
        }


class MemoryMetric(MetricProvider):
    definition = MetricDefinition(
        id="memory",
        name="Memory Usage",
        description="Virtual memory and swap usage.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={"Virtual %": "virtual.percent"},
            unit="percent",
        ),
    )

    def collect(self) -> Dict[str, Any]:
        virt = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "timestamp": time.time(),
            "virtual": {
                "total": virt.total,
                "available": virt.available,
                "used": virt.used,
                "percent": virt.percent,
                "free": virt.free,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "percent": swap.percent,
                "free": swap.free,
            },
        }


class DiskMetric(MetricProvider):
    definition = MetricDefinition(
        id="disk",
        name="Disk Usage",
        description="Disk usage stats per mounted partition.",
        category="system",
        display=MetricDisplayConfig(
            type="table",
            options={
                "columns": ["device", "mountpoint", "percent", "used", "free", "total"]
            },
            column_span=3,
        ),
    )

    def collect(self) -> Dict[str, Any]:
        partitions = psutil.disk_partitions()
        partition_stats: List[Dict[str, Any]] = []
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
            except PermissionError:
                continue
            partition_stats.append(
                {
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": _format_bytes(usage.total),
                    "used": _format_bytes(usage.used),
                    "free": _format_bytes(usage.free),
                    "percent": usage.percent,
                }
            )

        disk_io = psutil.disk_io_counters(perdisk=False)
        return {
            "timestamp": time.time(),
            "partitions": partition_stats,
            "io": {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
            },
        }


class NetworkMetric(MetricProvider):
    definition = MetricDefinition(
        id="network",
        name="Network I/O",
        description="Network throughput statistics since boot.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={
                "Bytes Sent": "totals.bytes_sent",
                "Bytes Received": "totals.bytes_recv",
            },
            unit="bytes",
        ),
    )

    def collect(self) -> Dict[str, Any]:
        pernic = psutil.net_io_counters(pernic=True)
        totals = psutil.net_io_counters(pernic=False)
        interfaces = []
        for name, stats in pernic.items():
            interfaces.append(
                {
                    "interface": name,
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                    "errin": stats.errin,
                    "errout": stats.errout,
                    "dropin": stats.dropin,
                    "dropout": stats.dropout,
                }
            )

        return {
            "timestamp": time.time(),
            "hostname": platform.node(),
            "interfaces": interfaces,
            "totals": {
                "bytes_sent": totals.bytes_sent,
                "bytes_recv": totals.bytes_recv,
                "packets_sent": totals.packets_sent,
                "packets_recv": totals.packets_recv,
            },
        }


def _aggregate_temperature(
    readings: Dict[str, Any],
    keywords: List[str],
) -> Optional[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    for name, entries in readings.items():
        name_lc = name.lower()
        name_matches = any(keyword in name_lc for keyword in keywords)
        for entry in entries:
            label_lc = (entry.label or "").lower()
            label_matches = any(keyword in label_lc for keyword in keywords)
            if not (name_matches or label_matches):
                continue
            if entry.current is None:
                continue
            matches.append(
                {
                    "label": entry.label or name,
                    "current": entry.current,
                    "high": entry.high,
                    "critical": entry.critical,
                }
            )
    if not matches:
        return None

    current_values = [
        sample["current"] for sample in matches if sample["current"] is not None
    ]
    high_values = [sample["high"] for sample in matches if sample["high"] is not None]
    critical_values = [
        sample["critical"] for sample in matches if sample["critical"] is not None
    ]

    return {
        "current": (
            sum(current_values) / len(current_values) if current_values else None
        ),
        "high": max(high_values) if high_values else None,
        "critical": max(critical_values) if critical_values else None,
        "sensors": matches,
    }


class TemperatureMetric(MetricProvider):
    definition = MetricDefinition(
        id="temperature",
        name="CPU & GPU Temperature",
        description="Average temperature readings for CPU and GPU sensors.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={
                "CPU °C": "cpu.current",
                "GPU °C": "gpu.current",
            },
            unit="celsius",
        ),
    )

    CPU_KEYWORDS = ["cpu", "core", "package", "soc"]
    GPU_KEYWORDS = ["gpu", "graphics", "nvidia", "amdgpu", "radeon"]

    def collect(self) -> Dict[str, Any]:
        try:
            temps = psutil.sensors_temperatures()
        except (AttributeError, NotImplementedError):
            print("no temps")
            temps = {}

        print("temps", temps)

        cpu_summary = (
            _aggregate_temperature(temps, self.CPU_KEYWORDS) if temps else None
        )
        gpu_summary = (
            _aggregate_temperature(temps, self.GPU_KEYWORDS) if temps else None
        )

        return {
            "timestamp": time.time(),
            "cpu": cpu_summary,
            "gpu": gpu_summary,
            "sensors_available": bool(temps),
        }


class DiskIOMetric(MetricProvider):
    definition = MetricDefinition(
        id="disk_io",
        name="Disk Read/Write",
        description="Disk I/O throughput measured in bytes per second.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={
                "Read B/s": "rates.read_bytes_per_sec",
                "Write B/s": "rates.write_bytes_per_sec",
            },
            unit="bytes_per_second",
        ),
    )

    def __init__(self) -> None:
        self._last_counters: Optional[Any] = None
        self._last_timestamp: Optional[float] = None

    def collect(self) -> Dict[str, Any]:
        timestamp = time.time()
        counters = psutil.disk_io_counters(perdisk=False)
        if counters is None:
            return {
                "timestamp": timestamp,
                "rates": {
                    "read_bytes_per_sec": None,
                    "write_bytes_per_sec": None,
                },
                "totals": None,
            }

        read_rate: Optional[float] = None
        write_rate: Optional[float] = None

        if self._last_counters is not None and self._last_timestamp is not None:
            elapsed = timestamp - self._last_timestamp
            if elapsed > 0:
                read_delta = counters.read_bytes - self._last_counters.read_bytes
                write_delta = counters.write_bytes - self._last_counters.write_bytes
                read_rate = read_delta / elapsed
                write_rate = write_delta / elapsed

        self._last_counters = counters
        self._last_timestamp = timestamp

        return {
            "timestamp": timestamp,
            "rates": {
                "read_bytes_per_sec": read_rate,
                "write_bytes_per_sec": write_rate,
            },
            "totals": {
                "read_bytes": counters.read_bytes,
                "write_bytes": counters.write_bytes,
                "read_count": counters.read_count,
                "write_count": counters.write_count,
                "read_time": getattr(counters, "read_time", None),
                "write_time": getattr(counters, "write_time", None),
            },
        }


DEFAULT_PROVIDERS = [
    CPUMetric(),
    MemoryMetric(),
    NetworkMetric(),
    DiskMetric(),
    TemperatureMetric(),
    DiskIOMetric(),
]
