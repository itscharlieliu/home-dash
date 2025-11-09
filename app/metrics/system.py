import platform
import time
from typing import Any, Dict, List

import psutil

from .base import MetricDefinition, MetricDisplayConfig, MetricProvider


def _percent(value: float) -> float:
    return round(value, 2)


class CPUMetric(MetricProvider):
    definition = MetricDefinition(
        id="cpu",
        name="CPU Load",
        description="Current CPU utilisation across cores.",
        category="system",
        display=MetricDisplayConfig(
            type="timeseries",
            series={"Total %": "percent_total"},
            unit="percent",
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
            "percent_total": _percent(total),
            "percent_per_core": [_percent(value) for value in per_core],
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
                "percent": _percent(virt.percent),
                "free": virt.free,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "percent": _percent(swap.percent),
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
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": _percent(usage.percent),
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


DEFAULT_PROVIDERS = [
    CPUMetric(),
    MemoryMetric(),
    NetworkMetric(),
    DiskMetric(),
]
