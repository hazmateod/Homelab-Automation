from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class HealthSource(StrEnum):
    PLUGIN = "PLUGIN"
    HOST_CONNECTIVITY = "HOST_CONNECTIVITY"


class HealthCheckResult(BaseModel):
    plugin: str
    check: str
    status: HealthStatus
    source: HealthSource = HealthSource.PLUGIN
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float = 0.0
    details: dict[str, object] = Field(default_factory=dict)


class HostHealthResult(BaseModel):
    hostname: str
    results: list[HealthCheckResult]

    @property
    def passed(self) -> int:
        return sum(
            r.status is HealthStatus.PASS
            for r in self.results
        )

    @property
    def warnings(self) -> int:
        return sum(
            r.status is HealthStatus.WARNING
            for r in self.results
        )

    @property
    def failed(self) -> int:
        return sum(
            r.status is HealthStatus.FAIL
            for r in self.results
        )

    @property
    def unknown(self) -> int:
        return sum(
            r.status is HealthStatus.UNKNOWN
            for r in self.results
        )

    @property
    def score(self) -> int:

        total = len(self.results)

        if total == 0:
            return 0

        points = (
            self.passed * 100 +
            self.warnings * 50 +
            self.unknown * 25
        )

        return round(points / total)


class PluginMetadata(BaseModel):
    data: dict[str, object] = Field(default_factory=dict)


class PluginHealthSummary(BaseModel):
    plugin: str
    status: HealthStatus
    score: int
    possible: int
    elapsed_ms: float = 0.0
    issues: list[str] = Field(default_factory=list)


class PluginHealthExecution(BaseModel):
    summary: PluginHealthSummary
    metadata: PluginMetadata = Field(default_factory=PluginMetadata)
    hosts: list[HostHealthResult] = Field(default_factory=list)


class HealthSummary(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plugins: list[HealthCheckResult] = Field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(
            p.status is HealthStatus.PASS
            for p in self.plugins
        )

    @property
    def warnings(self) -> int:
        return sum(
            p.status is HealthStatus.WARNING
            for p in self.plugins
        )

    @property
    def failed(self) -> int:
        return sum(
            p.status is HealthStatus.FAIL
            for p in self.plugins
        )

    @property
    def unknown(self) -> int:
        return sum(
            p.status is HealthStatus.UNKNOWN
            for p in self.plugins
        )

    @property
    def score(self) -> int:

        total = len(self.plugins)

        if total == 0:
            return 0

        points = (
            self.passed * 100 +
            self.warnings * 50 +
            self.unknown * 25
        )

        return round(points / total)
