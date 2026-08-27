"""
HIMP Application Health Service.

Provides health and operational lifecycle information about HIMP
itself rather than individual infrastructure plugins.
"""

from pathlib import Path

from himp.database.factory import create_database
from himp.services.automation import AutomationService
from himp.services.host_health_dashboard import (
    HostHealthDashboardService,
)
from himp.services.maintenance_windows import (
    MaintenanceWindowService,
)
from himp.services.scheduler import SchedulerService
from himp.services.settings import SettingsService


class ApplicationHealthService:

    RELEASE_MARKER = Path("/opt/himp/.himp-release")

    def __init__(
        self,
        automation=None,
        settings=None,
        scheduler=None,
        maintenance_windows=None,
        host_health=None,
        release_marker=None,
    ):
        self.database = create_database()

        self.scheduler = (
            scheduler
            if scheduler is not None
            else SchedulerService()
        )

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

        self.maintenance_windows = (
            maintenance_windows
            if maintenance_windows is not None
            else MaintenanceWindowService()
        )

        self.host_health = (
            host_health
            if host_health is not None
            else HostHealthDashboardService()
        )

        self.release_marker = (
            Path(release_marker)
            if release_marker is not None
            else self.RELEASE_MARKER
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
            "release": self._release(),
            "scheduler_operations": (
                self._scheduler_operations()
            ),
            "maintenance": self._maintenance(),
            "infrastructure": self._infrastructure(),
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

    def _release(self):

        try:
            revision = self.release_marker.read_text(
                encoding="utf-8"
            ).strip()

        except (OSError, UnicodeError):
            revision = ""

        return {
            "revision": revision or None,
            "available": bool(revision),
        }

    def _scheduler_operations(self):

        try:
            schedules = self.scheduler.all()

            operations = []

            for schedule in schedules:
                status = self.scheduler.execution_status(
                    schedule["task_id"]
                )

                operations.append(
                    {
                        "task_id": schedule["task_id"],
                        "name": schedule["name"],
                        "enabled": bool(
                            schedule["enabled"]
                        ),
                        "frequency": schedule["frequency"],
                        "next_run": status["next_run"],
                        "last_execution_success": (
                            status[
                                "last_execution_success"
                            ]
                        ),
                        "last_execution_at": (
                            status["last_execution_at"]
                        ),
                        "last_execution_elapsed": (
                            status[
                                "last_execution_elapsed"
                            ]
                        ),
                        "last_execution_error": (
                            status[
                                "last_execution_error"
                            ]
                        ),
                    }
                )

            return {
                "available": True,
                "total": len(operations),
                "enabled": sum(
                    operation["enabled"]
                    for operation in operations
                ),
                "disabled": sum(
                    not operation["enabled"]
                    for operation in operations
                ),
                "failed": sum(
                    operation[
                        "last_execution_success"
                    ] is False
                    for operation in operations
                ),
                "schedules": operations,
            }

        except Exception as exc:
            return {
                "available": False,
                "error": str(exc),
                "total": 0,
                "enabled": 0,
                "disabled": 0,
                "failed": 0,
                "schedules": [],
            }

    def _maintenance(self):

        try:
            active = self.maintenance_windows.active_all()
            upcoming = self.maintenance_windows.upcoming(
                limit=10
            )

            return {
                "available": True,
                "active_count": len(active),
                "upcoming_count": len(upcoming),
                "active": active,
                "upcoming": upcoming,
            }

        except Exception as exc:
            return {
                "available": False,
                "error": str(exc),
                "active_count": 0,
                "upcoming_count": 0,
                "active": [],
                "upcoming": [],
            }

    def _infrastructure(self):

        try:
            summary = self.host_health.summary()

            return {
                "available": True,
                "total": summary["total"],
                "passed": summary["passed"],
                "warnings": summary["warnings"],
                "failed": summary["failed"],
                "unknown": summary["unknown"],
                "score": summary["score"],
            }

        except Exception as exc:
            return {
                "available": False,
                "error": str(exc),
                "total": 0,
                "passed": 0,
                "warnings": 0,
                "failed": 0,
                "unknown": 0,
                "score": 0,
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
