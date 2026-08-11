"""
Automation Service.

Provides HIMP automation task definitions and execution.
"""

import time

from datetime import datetime, timezone

from himp.database.automation_dependencies import (
    AutomationDependencyRepository,
)
from himp.database.automation_executions import (
    AutomationExecutionRepository,
)
from himp.database.automation_locks import (
    AutomationLockRepository,
)


class AutomationAlreadyRunningError(
    RuntimeError
):
    """Raised when an automation is already executing."""


class AutomationDisabledError(
    RuntimeError
):
    """Raised when an automation is disabled."""


class AutomationConfirmationRequiredError(
    RuntimeError
):
    """Raised when a destructive automation lacks confirmation."""


class AutomationDependencyNotSatisfiedError(
    RuntimeError
):
    """Raised when an automation dependency is not satisfied."""


class AutomationDependencyNotFoundError(
    RuntimeError
):
    """Raised when an automation dependency does not exist."""


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
        self.dependency_repository = (
            AutomationDependencyRepository()
        )
        self.lock_repository = (
            AutomationLockRepository()
        )

        self.tasks = [
            {
                "id": "health_check",
                "name": "Health Check",
                "description": "Run health validation across plugins.",
                "enabled": True,
                "schedule": "manual",
                "timeout_seconds": 300,
                "risk_level": "read_only",
            },
            {
                "id": "host_health_check",
                "name": "Host Health Check",
                "description": "Run SSH health checks across active inventory hosts.",
                "enabled": True,
                "schedule": "manual",
                "timeout_seconds": 900,
                "risk_level": "read_only",
            },
            {
                "id": "generate_reports",
                "name": "Generate Reports",
                "description": "Generate HIMP infrastructure reports.",
                "enabled": True,
                "schedule": "weekly 03:00 Sunday",
                "timeout_seconds": 1800,
                "risk_level": "read_only",
            },
            {
                "id": "inventory_refresh",
                "name": "Inventory Refresh",
                "description": "Refresh inventory data.",
                "enabled": True,
                "schedule": "daily 03:00",
                "timeout_seconds": 300,
                "risk_level": "read_only",
            },
            {
                "id": "scheduled_updates",
                "name": "Scheduled Updates",
                "description": "Run maintenance updates across the homelab.",
                "enabled": True,
                "schedule": "daily 03:15",
                "timeout_seconds": 3600,
                "risk_level": "maintenance",
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


    def find_task(
        self,
        task_id,
    ):
        for task in self.tasks:
            if task["id"] == task_id:
                return task

        raise ValueError(
            f"Automation task does not exist: {task_id}"
        )

    def set_enabled(
        self,
        task_id,
        enabled,
    ):
        task = self.find_task(
            task_id
        )

        task["enabled"] = bool(
            enabled
        )

        return task

    def enable(
        self,
        task_id,
    ):
        return self.set_enabled(
            task_id,
            True,
        )

    def disable(
        self,
        task_id,
    ):
        return self.set_enabled(
            task_id,
            False,
        )

    def validate_dependencies(
        self,
        task_id,
    ):
        dependencies = self.dependency_repository.list(
            task_id
        )

        for dependency in dependencies:
            dependency_task_id = dependency[
                "depends_on_task_id"
            ]

            self.find_task(
                dependency_task_id
            )

            execution = (
                self.execution_repository.latest(
                    dependency_task_id
                )
            )

            if execution is None:
                raise AutomationDependencyNotSatisfiedError(
                    "Automation dependency has never "
                    "completed successfully: "
                    f"{task_id} -> {dependency_task_id}"
                )

            if not execution["success"]:
                raise AutomationDependencyNotSatisfiedError(
                    "Automation dependency failed: "
                    f"{task_id} -> {dependency_task_id}"
                )

        return dependencies


    def add_dependency(
        self,
        task_id,
        depends_on_task_id,
    ):
        self.find_task(
            task_id
        )

        self.find_task(
            depends_on_task_id
        )

        return self.dependency_repository.add(
            task_id,
            depends_on_task_id,
        )


    def remove_dependency(
        self,
        task_id,
        depends_on_task_id,
    ):
        self.find_task(
            task_id
        )

        self.find_task(
            depends_on_task_id
        )

        dependency = (
            self.dependency_repository.find(
                task_id,
                depends_on_task_id,
            )
        )

        if dependency is None:
            raise AutomationDependencyNotFoundError(
                "Automation dependency does not exist: "
                f"{task_id} -> {depends_on_task_id}"
            )

        self.dependency_repository.remove(
            task_id,
            depends_on_task_id,
        )

        return dependency


    def dependency_status(
        self,
        task_id,
    ):
        self.find_task(
            task_id
        )

        dependencies = (
            self.dependency_repository.list(
                task_id
            )
        )

        status = []

        for dependency in dependencies:
            dependency_task_id = (
                dependency["depends_on_task_id"]
            )

            self.find_task(
                dependency_task_id
            )

            execution = (
                self.execution_repository.latest(
                    dependency_task_id
                )
            )

            if execution is None:
                status.append(
                    {
                        "task_id": dependency_task_id,
                        "satisfied": False,
                        "status": "never_run",
                        "latest_execution": None,
                    }
                )
                continue

            success = bool(
                execution["success"]
            )

            status.append(
                {
                    "task_id": dependency_task_id,
                    "satisfied": success,
                    "status": (
                        "satisfied"
                        if success
                        else "failed"
                    ),
                    "latest_execution": execution,
                }
            )

        return {
            "task_id": task_id,
            "dependencies": status,
            "satisfied": all(
                dependency["satisfied"]
                for dependency in status
            ),
        }


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
        confirmed=False,
    ):

        task = self.find_task(
            task_id
        )

        if not task["enabled"]:
            raise AutomationDisabledError(
                f"Automation task is disabled: {task_id}"
            )

        if (
            task["risk_level"] == "destructive"
            and not confirmed
        ):
            raise AutomationConfirmationRequiredError(
                "Destructive automation requires explicit confirmation: "
                f"{task_id}"
            )

        self.validate_dependencies(
            task_id
        )

        if not self.lock_repository.acquire(
            task_id
        ):
            raise AutomationAlreadyRunningError(
                f"Automation task is already running: {task_id}"
            )

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

        finally:
            self.lock_repository.release(
                task_id
            )
