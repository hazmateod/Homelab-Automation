"""
Health Service.
"""

from himp.health.models import (
    HealthCheckResult,
    HealthStatus,
    HealthSummary,
)
from himp.health.repository import HealthRepository
from himp.plugins.loader import PluginLoader
from himp.sdk.health import PluginHealthRunner
from himp.services.health_history import HealthHistoryService


class HealthService:

    def __init__(self):

        self.runner = PluginHealthRunner()
        self.loader = PluginLoader()
        self.repository = HealthRepository()

        self.history = HealthHistoryService()

    def plugin(self, name):

        execution = self.runner.health(name)

        if execution.success and getattr(execution, "health_attempt_id", None):
            report = self.repository.plugin(name)
            if (
                report is not None
                and report.metadata.data.get("attempt_id") == execution.health_attempt_id
            ):
                self.history.record(report)

        return execution

    def all(
        self,
        timeout=None,
    ):

        return self.runner.health_all(
            timeout=timeout,
        )

    def execution(self, name):

        return self.repository.plugin(name)

    def summary(self):

        summary = HealthSummary()

        for name, report, attempt, freshness in self.repository.observations():
            current = report is not None and freshness != "stale"
            status = report.summary.status if current else HealthStatus.UNKNOWN
            details = dict(report.metadata.data) if current else {}
            details.update(latest_attempt=attempt, evidence_freshness=freshness)
            if not current and report is not None:
                details["last_observation_status"] = report.metadata.data.get(
                    "last_observation_status", report.summary.status.value
                )
                if "fleet_membership" in report.metadata.data:
                    details["fleet_membership"] = report.metadata.data["fleet_membership"]

            summary.plugins.append(
                HealthCheckResult(
                    plugin=name,
                    check="health",
                    status=status,
                    message="Latest attempt has no current evidence" if not current else status.value,
                    duration_ms=report.summary.elapsed_ms if current else 0.0,
                    details=details,
                )
            )

        return summary
