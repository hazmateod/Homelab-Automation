"""
Report Service.

Provides report inventory and dashboard report information.
"""

from pathlib import Path

from himp.models.dashboard import Dashboard


class ReportService:

    def __init__(self):

        self.root = Path("reports")


    def summary(self):

        return {
            "dashboard": self.dashboard(),
            "health": self.count_files(
                self.root / "health"
            ),
            "discovery": self.count_files(
                self.root / "discovery"
            ),
            "current": self.count_files(
                self.root / "current"
            ),
            "history": self.count_files(
                self.root / "history"
            ),
            "json": self.count_files(
                self.root / "json"
            ),
        }


    def count_files(
        self,
        path,
    ):

        if not path.exists():

            return 0

        return len(
            [
                item
                for item in path.rglob("*")
                if item.is_file()
            ]
        )


    def dashboard(self):

        filename = (
            self.root
            / "dashboard"
            / "dashboard.json"
        )

        if not filename.exists():

            return None

        dashboard = Dashboard.load(
            str(filename)
        )

        return {
            "generated": dashboard.generated,
            "hosts": len(dashboard.hosts),
            "healthy": dashboard.healthy_count(),
            "warnings": dashboard.warning_count(),
            "critical": dashboard.critical_count(),
            "unknown": dashboard.unknown_count(),
            "average_score": dashboard.average_score(),
        }


    def files(self):

        reports = []

        if not self.root.exists():

            return reports


        for item in sorted(
            self.root.rglob("*")
        ):

            if item.is_file():

                reports.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": item.suffix.replace(
                            ".",
                            "",
                        ),
                    }
                )


        return reports
