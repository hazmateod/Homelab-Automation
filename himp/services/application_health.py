"""
HIMP Application Health Service.

Provides health information about HIMP itself rather than
individual infrastructure plugins.
"""

from pathlib import Path

from himp.database.factory import create_database
from himp.services.automation import AutomationService
from himp.services.scheduler import SchedulerService
from himp.services.settings import SettingsService


class ApplicationHealthService:

    def __init__(
        self,
        automation=None,
        settings=None,
    ):

        self.database = create_database()
        self.scheduler = SchedulerService()
        self.automation = (
            automation
            if automation is not None
            else AutomationService()
        )
        self.settings = (
            settings
            if settings is not None
            else SettingsService()
        )

    def summary(self):

        components = {
            "database": self._database(),
            "scheduler": self._scheduler(),
            "automation": self._automation(),
            "configuration": self._configuration(),
            "storage": self._storage(),
        }

        return {
            "status": self._overall_status(
                components
            ),
            "components": components,
        }

    def _database(self):

        try:

            self.database.query(
                "SELECT 1"
            )

            return {
                "status": "healthy",
                "message": "Database is available.",
            }

        except Exception as exc:

            return {
                "status": "critical",
                "message": str(exc),
            }

    def _scheduler(self):

        try:

            schedules = self.scheduler.all()

            return {
                "status": "healthy",
                "message": "Scheduler is available.",
                "schedules": len(schedules),
            }

        except Exception as exc:

            return {
                "status": "critical",
                "message": str(exc),
            }

    def _automation(self):

        try:

            summary = self.automation.summary()

            return {
                "status": "healthy",
                "message": "Automation service is available.",
                "tasks": summary["tasks"],
                "enabled": summary["enabled"],
                "disabled": summary["disabled"],
            }

        except Exception as exc:

            return {
                "status": "critical",
                "message": str(exc),
            }

    def _configuration(self):

        try:

            paths = self.settings.paths()

            missing = [
                name
                for name, details in paths.items()
                if not details["exists"]
            ]

            if missing:

                return {
                    "status": "warning",
                    "message": (
                        "Required configuration paths are missing."
                    ),
                    "missing": missing,
                    "paths": paths,
                }

            return {
                "status": "healthy",
                "message": "Required configuration paths exist.",
                "paths": paths,
            }

        except Exception as exc:

            return {
                "status": "critical",
                "message": str(exc),
            }

    def _storage(self):

        data = Path("data")
        reports = Path("reports")

        return {
            "status": (
                "healthy"
                if data.is_dir() and reports.is_dir()
                else "critical"
            ),
            "details": {
                "data": data.is_dir(),
                "reports": reports.is_dir(),
            },
        }

    @staticmethod
    def _overall_status(components):

        statuses = {
            component["status"]
            for component in components.values()
        }

        if "critical" in statuses:
            return "critical"

        if "warning" in statuses:
            return "warning"

        return "healthy"
