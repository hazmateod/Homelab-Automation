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


class HealthService:

    def __init__(self):

        self.runner = PluginHealthRunner()
        self.loader = PluginLoader()
        self.repository = HealthRepository()

    def plugin(self, name):

        return self.runner.health(name)

    def all(self):

        return self.runner.health_all()

    def execution(self, name):

        execution = self.runner.health(name)

        if not execution.success:
            return None

        return self.repository.plugin(name)

    def summary(self):

        summary = HealthSummary()

        reports = {
            report.summary.plugin: report
            for report in self.repository.plugins()
        }

        for plugin in self.loader.plugins():

            if not plugin.supports_health():
                continue

            report = reports.get(plugin.id)

            if report is None:

                summary.plugins.append(
                    HealthCheckResult(
                        plugin=plugin.id,
                        check="health",
                        status=HealthStatus.UNKNOWN,
                        message="No health report available.",
                    )
                )

                continue

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
