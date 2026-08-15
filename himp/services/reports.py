"""
Report Service.

Provides report inventory and dashboard report information.
"""

from pathlib import Path

from himp.config import config
from himp.database.automation_executions import AutomationExecutionRepository
from himp.lib.ansible import run_playbook
from himp.models.dashboard import Dashboard


class ReportService:

    def __init__(self):

        self.root = Path("reports")
        self.automation_executions = (
            AutomationExecutionRepository()
        )


    def generate(
        self,
        limit=None,
        timeout=None,
    ):

        success, elapsed = run_playbook(
            config.report_playbook,
            limit,
            timeout=timeout,
        )

        return {
            "success": success,
            "elapsed": elapsed,
        }


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


    def operational_summary(self):
        dashboard = self.dashboard()
        execution_history = (
            self.automation_executions.history(
                limit=50
            )
        )

        executions = {
            "total": len(execution_history),
            "successful": sum(
                1
                for execution in execution_history
                if execution["success"]
            ),
            "failed": sum(
                1
                for execution in execution_history
                if not execution["success"]
            ),
            "recent": [
                {
                    "id": execution["id"],
                    "task_id": execution["task_id"],
                    "success": execution["success"],
                    "elapsed": execution["elapsed"],
                    "executed_at": execution["executed_at"],
                }
                for execution in execution_history
            ],
        }

        return {
            "generated": (
                dashboard["generated"]
                if dashboard
                else None
            ),
            "dashboard": (
                {
                    key: dashboard[key]
                    for key in (
                        "hosts",
                        "healthy",
                        "warnings",
                        "critical",
                        "unknown",
                        "average_score",
                    )
                }
                if dashboard
                else None
            ),
            "reports": {
                "current": self.count_files(
                    self.root / "current"
                ),
                "history": self.count_files(
                    self.root / "history"
                ),
                "health": self.count_files(
                    self.root / "health"
                ),
                "discovery": self.count_files(
                    self.root / "discovery"
                ),
                "json": self.count_files(
                    self.root / "json"
                ),
            },
            "executions": executions,
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
