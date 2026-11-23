"""
Health Report Repository.
"""

from pathlib import Path

from himp.database.host_identity import HostIdentityRepository
from himp.health.attempts import HealthAttempts, current_evidence
from himp.health.parser import HealthArtifactParser


class HealthRepository:

    REPORT_DIR = Path("reports/health")

    def __init__(self):

        self.parser = HealthArtifactParser()

    def plugins(self):

        if not self.REPORT_DIR.exists():
            return []

        reports = []

        for artifact in sorted(
            self.REPORT_DIR.glob("*.json")
        ):

            report = self._parse(artifact)

            if report is not None:
                reports.append(report)

        return reports

    def plugin(self, name):

        artifact = (
            self.REPORT_DIR /
            f"{name}.json"
        )

        return self._parse(artifact)

    def _parse(self, artifact):
        try:
            return self.parser.parse(artifact)
        except (OSError, ValueError, TypeError, AttributeError, RecursionError):
            return None

    def observations(self):
        reports = {report.summary.plugin: report for report in self.plugins()}
        attempts = HealthAttempts(self.REPORT_DIR).all()
        for name in sorted(reports.keys() | attempts.keys()):
            report, attempt = reports.get(name), attempts.get(name)
            yield name, report, attempt, current_evidence(attempt, report)

    def current_plugins(self):
        for _, report, _, freshness in self.observations():
            if report is not None and freshness != "stale":
                yield report

    def current_hosts(self, current=None):
        """Shadow view of verified plugin results without replacing legacy artifacts."""
        if current is None:
            current = HostIdentityRepository().current_hostnames()
        for execution in self.current_plugins():
            for host in execution.hosts:
                hostname = HostIdentityRepository.projected_hostname(current, host.host_identity)
                if hostname is not None:
                    yield execution.summary.plugin, host.model_copy(update={"hostname": hostname})
