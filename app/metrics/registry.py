from collections import OrderedDict
from typing import Iterable, List

from .base import MetricProvider, MetricResult


class MetricRegistry:
    """Registry that manages metric providers and collection."""

    def __init__(self) -> None:
        self._providers: "OrderedDict[str, MetricProvider]" = OrderedDict()

    def register(self, provider: MetricProvider) -> None:
        definition = provider.definition
        if definition.id in self._providers:
            raise ValueError(f"Metric '{definition.id}' is already registered.")
        self._providers[definition.id] = provider

    def all(self) -> Iterable[MetricProvider]:
        return self._providers.values()

    def get(self, metric_id: str) -> MetricProvider:
        if metric_id not in self._providers:
            raise KeyError(f"Metric '{metric_id}' is not registered.")
        return self._providers[metric_id]

    def collect_all(self) -> List[MetricResult]:
        return [MetricResult(provider.definition, provider.collect()) for provider in self.all()]

    def collect_one(self, metric_id: str) -> MetricResult:
        provider = self.get(metric_id)
        return MetricResult(provider.definition, provider.collect())

