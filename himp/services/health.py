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

        report = self.repository.plugin(name)

        if report is not None:

            self.history.record(
                report
            )

        return execution

    def all(self):

        return self.runner.health_all()

    def execution(self, name):

        return self.repository.plugin(name)

    def summary(self):

        summary = HealthSummary()

        reports = {
            report.summary.plugin: report
            for report in self.repository.plugins()
        }

        for plugin_id, report in reports.items():

            summary.plugins.append(
                HealthCheckResult(
                    plugin=report.summary.plugin,
                    check="health",
                    status=report.summary.status,
                    message=report.summary.status.value,
                    duration_ms=report.summary.elapsed_ms,
                    details=report.metadata.data,
                )
            )

        return summary
