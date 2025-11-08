from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class MetricDisplayConfig:
    """Configuration for how a metric should be rendered on the client."""

    type: str = "json"  # e.g. json, timeseries, table, gauge
    series: Optional[Mapping[str, str]] = None  # chart label -> dotted path in data
    unit: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class MetricDefinition:
    """Declarative definition of a metric provider."""

    id: str
    name: str
    description: str
    category: str = "system"
    display: MetricDisplayConfig = field(default_factory=MetricDisplayConfig)


class MetricProvider(ABC):
    """Abstract base class for metric providers."""

    definition: MetricDefinition

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Return the data for this metric."""


@dataclass
class MetricResult:
    definition: MetricDefinition
    data: Dict[str, Any]

