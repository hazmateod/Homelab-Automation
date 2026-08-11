"""
Automation Service.

Provides HIMP automation task definitions and execution.
"""

import time

from datetime import datetime, timezone

from himp.database.automation_executions import (
    AutomationExecutionRepository,
)


class AutomationService:

    def __init__(self):

        self.health = None
        self.host_health = None
        self.reports = None
        self.inventory = None
        self.updates = None
        self.execution_repository = (
            AutomationExecutionRepository()
        )

        self.tasks = [
            {
                "id": "health_check",
                "name": "Health Check",
                "description": "Run health validation across plugins.",
                "enabled": True,
                "schedule": "manual",
            },
            {
                "id": "host_health_check",
                "name": "Host Health Check",
                "description": "Run SSH health checks across active inventory hosts.",
                "enabled": True,
                "schedule": "manual",
            },
            {
                "id": "generate_reports",
                "name": "Generate Reports",
                "description": "Generate HIMP infrastructure reports.",
                "enabled": True,
                "schedule": "weekly 03:00 Sunday",
            },
            {
                "id": "inventory_refresh",
                "name": "Inventory Refresh",
                "description": "Refresh inventory data.",
                "enabled": True,
                "schedule": "daily 03:00",
            },
            {
                "id": "scheduled_updates",
                "name": "Scheduled Updates",
                "description": "Run maintenance updates across the homelab.",
                "enabled": True,
                "schedule": "daily 03:15",
            },
        ]


    def configure(
        self,
        health,
        reports,
        inventory,
        updates,
        host_health=None,
    ):

        self.health = health
        self.host_health = host_health
        self.reports = reports
        self.inventory = inventory
        self.updates = updates


    def summary(self):

        return {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "tasks": len(self.tasks),

            "enabled": sum(
                1
                for task in self.tasks
                if task["enabled"]
            ),

            "disabled": sum(
                1
                for task in self.tasks
                if not task["enabled"]
            ),

            "automation": self.tasks,
        }


    def run(
        self,
        task_id,
        limit=None,
    ):

        started = time.perf_counter()

        executed_at = datetime.now(
            timezone.utc
        ).isoformat()

        try:

            if task_id == "host_health_check":

                if self.host_health is None:
                    raise RuntimeError(
                        "Host health service not configured"
                    )

                result = self.host_health.check_all_hosts()

            elif task_id == "health_check":

                if self.health is None:
                    raise RuntimeError(
                        "Health service not configured"
                    )

                result = self.health.summary()

            elif task_id == "generate_reports":

                if self.reports is None:
                    raise RuntimeError(
                        "Report service not configured"
                    )

                result = self.reports.generate(
                    limit=limit,
                )

            elif task_id == "inventory_refresh":

                if self.inventory is None:
                    raise RuntimeError(
                        "Inventory service not configured"
                    )

                result = self.inventory.sync()

            elif task_id == "scheduled_updates":

                if self.updates is None:
                    raise RuntimeError(
                        "Update service not configured"
                    )

                result = self.updates.update(
                    "maintenance",
                    limit=limit,
                )

            else:

                raise ValueError(
                    f"Unknown automation task: {task_id}"
                )

            elapsed = round(
                time.perf_counter() - started,
                3,
            )

            success = True

            if isinstance(result, dict):
                if "success" in result:
                    success = bool(
                        result["success"]
                    )

            execution = {
                "task": task_id,
                "executed_at": executed_at,
                "result": result,
            }

            self.execution_repository.save(
                task_id=task_id,
                success=success,
                elapsed=elapsed,
                result=execution,
                executed_at=executed_at,
            )

            return execution

        except Exception as error:

            elapsed = round(
                time.perf_counter() - started,
                3,
            )

            failure = {
                "task": task_id,
                "executed_at": executed_at,
                "result": {
                    "success": False,
                    "error": str(error),
                },
            }

            self.execution_repository.save(
                task_id=task_id,
                success=False,
                elapsed=elapsed,
                result=failure,
                executed_at=executed_at,
            )

            raise
