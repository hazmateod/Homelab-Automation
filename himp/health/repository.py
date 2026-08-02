"""
Health Report Repository.
"""

from pathlib import Path

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

            report = self.parser.parse(artifact)

            if report is not None:
                reports.append(report)

        return reports

    def plugin(self, name):

        artifact = (
            self.REPORT_DIR /
            f"{name}.json"
        )

        return self.parser.parse(artifact)
