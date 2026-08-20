"""
Automation Service.

Provides HIMP automation task definitions and execution.
"""

import logging
import time

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone

from pydantic import BaseModel

from himp.database.automation_dependencies import (
    AutomationDependencyRepository,
)
from himp.database.automation_executions import (
    AutomationExecutionRepository,
)
from himp.database.automation_locks import (
    AutomationLockRepository,
)


logger = logging.getLogger("himp.automation")


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


class AutomationDependencyCycleError(
    RuntimeError
):
    """Raised when an automation dependency would create a cycle."""


class AutomationService:

    @staticmethod
    def _classify_error(error):
        if isinstance(error, TimeoutError):
            return {
                "category": "timeout",
                "retryable": True,
            }

        if isinstance(error, OSError):
            return {
                "category": "unreachable",
                "retryable": True,
            }

        if isinstance(
            error,
            AutomationAlreadyRunningError,
        ):
            return {
                "category": "concurrency",
                "retryable": False,
            }

        if isinstance(
            error,
            AutomationDisabledError,
        ):
            return {
                "category": "disabled",
                "retryable": False,
            }

        if isinstance(
            error,
            AutomationConfirmationRequiredError,
        ):
            return {
                "category": "confirmation",
                "retryable": False,
            }

        if isinstance(
            error,
            (
                AutomationDependencyNotSatisfiedError,
                AutomationDependencyNotFoundError,
                AutomationDependencyCycleError,
            ),
        ):
            return {
                "category": "dependency",
                "retryable": False,
            }

        if isinstance(error, RuntimeError):
            return {
                "category": "execution",
                "retryable": True,
            }

        return {
            "category": "internal",
            "retryable": False,
        }


    def __init__(self):

        self.health = None
        self.host_health = None
        self.storage = None
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
                "schedule": "daily 04:00",
                "timeout_seconds": 300,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "read_only",
            },
            {
                "id": "host_health_check",
                "name": "Host Health Check",
                "description": "Run SSH health checks across active inventory hosts.",
                "enabled": True,
                "schedule": "manual",
                "timeout_seconds": 900,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "read_only",
            },
            {
                "id": "storage_capacity_check",
                "name": "Storage Capacity Check",
                "description": (
                    "Collect per-filesystem storage utilization "
                    "across active inventory hosts."
                ),
                "enabled": True,
                "schedule": "daily 04:15",
                "timeout_seconds": 900,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "read_only",
            },
            {
                "id": "generate_reports",
                "name": "Generate Reports",
                "description": "Generate HIMP infrastructure reports.",
                "enabled": True,
                "schedule": "weekly 03:00 Sunday",
                "timeout_seconds": 1800,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "read_only",
            },
            {
                "id": "inventory_refresh",
                "name": "Inventory Refresh",
                "description": "Refresh inventory data.",
                "enabled": True,
                "schedule": "daily 03:00",
                "timeout_seconds": 300,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "read_only",
            },
            {
                "id": "scheduled_updates",
                "name": "Scheduled Updates",
                "description": "Run maintenance updates across the homelab.",
                "enabled": True,
                "schedule": "daily 03:15",
                "timeout_seconds": 3600,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "maintenance",
            },
            {
                "id": "update_host",
                "name": "Update Host",
                "description": "Run maintenance updates for a specific inventory host.",
                "enabled": True,
                "schedule": "manual",
                "timeout_seconds": 3600,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "maintenance",
            },
            {
                "id": "update_group",
                "name": "Update Group",
                "description": "Run maintenance updates for an inventory group.",
                "enabled": True,
                "schedule": "manual",
                "timeout_seconds": 3600,
                "retry_attempts": 1,
                "retry_delay_seconds": 0,
                "risk_level": "maintenance",
            },
        ]


    @staticmethod
    def _normalize_result(
        value,
    ):
        if isinstance(value, BaseModel):
            return value.model_dump(
                mode="json"
            )

        if is_dataclass(value):
            return asdict(value)

        if isinstance(value, list):
            return [
                AutomationService._normalize_result(
                    item
                )
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: AutomationService._normalize_result(
                    item
                )
                for key, item in value.items()
            }

        return value


    def validate_execution_policy(
        self,
        task_id,
        confirmed=False,
    ):
        """
        Validate all pre-execution safety policy.

        No task execution should occur before this
        policy validation succeeds.
        """

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

        dependencies = self.validate_dependencies(
            task_id
        )

        retry_policy = self.validate_retry_policy(
            task_id
        )

        return {
            "task_id": task_id,
            "enabled": task["enabled"],
            "risk_level": task["risk_level"],
            "confirmed": confirmed,
            "dependencies": dependencies,
            **retry_policy,
        }


    def validate_retry_policy(
        self,
        task_id,
    ):
        task = self.find_task(
            task_id
        )

        attempts = task.get(
            "retry_attempts",
            1,
        )

        delay = task.get(
            "retry_delay_seconds",
            0,
        )

        timeout = task.get(
            "timeout_seconds"
        )

        if (
            not isinstance(attempts, int)
            or isinstance(attempts, bool)
            or attempts < 1
        ):
            raise ValueError(
                "Automation retry_attempts must be "
                "an integer greater than or equal to 1: "
                f"{task_id}"
            )

        if (
            not isinstance(delay, int | float)
            or isinstance(delay, bool)
            or delay < 0
        ):
            raise ValueError(
                "Automation retry_delay_seconds must be "
                "a non-negative number: "
                f"{task_id}"
            )

        if (
            timeout is not None
            and (
                not isinstance(timeout, int | float)
                or isinstance(timeout, bool)
                or timeout <= 0
            )
        ):
            raise ValueError(
                "Automation timeout_seconds must be "
                "a positive number: "
                f"{task_id}"
            )

        return {
            "task_id": task_id,
            "retry_attempts": attempts,
            "retry_delay_seconds": delay,
            "timeout_seconds": timeout,
        }


    def configure(
        self,
        health,
        reports,
        inventory,
        updates,
        host_health=None,
        storage=None,
    ):

        self.health = health
        self.host_health = host_health
        self.storage = storage
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

        if task_id == depends_on_task_id:
            raise AutomationDependencyCycleError(
                "Automation dependency would create a cycle: "
                f"{task_id} -> {depends_on_task_id}"
            )

        pending = [
            depends_on_task_id
        ]

        visited = set()

        while pending:
            current_task_id = pending.pop()

            if current_task_id in visited:
                continue

            visited.add(current_task_id)

            if current_task_id == task_id:
                raise AutomationDependencyCycleError(
                    "Automation dependency would create a cycle: "
                    f"{task_id} -> {depends_on_task_id}"
                )

            dependencies = (
                self.dependency_repository.list(
                    current_task_id
                )
            )

            pending.extend(
                dependency["depends_on_task_id"]
                for dependency in dependencies
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


    def dependency_graph(self):
        graph = []

        for task in self.tasks:
            task_id = task["id"]

            dependencies = [
                dependency["depends_on_task_id"]
                for dependency in (
                    self.dependency_repository.list(
                        task_id
                    )
                )
            ]

            dependents = [
                dependency["task_id"]
                for dependency in (
                    self.dependency_repository.dependents(
                        task_id
                    )
                )
            ]

            graph.append(
                {
                    "task_id": task_id,
                    "dependencies": dependencies,
                    "dependents": dependents,
                }
            )

        return {
            "tasks": graph,
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


    def _execute_task(
        self,
        task_id,
        limit=None,
        timeout=None,
    ):
        if task_id == "host_health_check":

            if self.host_health is None:
                raise RuntimeError(
                    "Host health service not configured"
                )

            return self.host_health.check_all_hosts(
                timeout=timeout,
            )

        if task_id == "storage_capacity_check":

            if self.storage is None:
                raise RuntimeError(
                    "Storage capacity service not configured"
                )

            return self.storage.collect_all(
                timeout=timeout,
            )

        if task_id == "health_check":

            if self.health is None:
                raise RuntimeError(
                    "Health service not configured"
                )

            executions = self.health.all(
                timeout=timeout,
            )

            return {
                "success": (
                    bool(executions)
                    and all(
                        execution.success
                        for execution in executions
                    )
                ),
                "executions": executions,
            }

        if task_id == "generate_reports":

            if self.reports is None:
                raise RuntimeError(
                    "Report service not configured"
                )

            return self.reports.generate(
                limit=limit,
                timeout=timeout,
            )

        if task_id == "inventory_refresh":

            if self.inventory is None:
                raise RuntimeError(
                    "Inventory service not configured"
                )

            return self.inventory.sync()

        if task_id == "scheduled_updates":

            if self.updates is None:
                raise RuntimeError(
                    "Update service not configured"
                )

            return self.updates.update(
                "maintenance",
                limit=limit,
                timeout=timeout,
            )

        if task_id == "update_host":

            if self.updates is None:
                raise RuntimeError(
                    "Update service not configured"
                )

            if not limit:
                raise ValueError(
                    "Host update requires a hostname"
                )

            return self.updates.update(
                "update_host",
                limit=limit,
                timeout=timeout,
            )

        if task_id == "update_group":

            if self.updates is None:
                raise RuntimeError(
                    "Update service not configured"
                )

            if not limit:
                raise ValueError(
                    "Group update requires a group name"
                )

            return self.updates.update(
                "update_group",
                limit=limit,
                timeout=timeout,
            )

        raise ValueError(
            f"Unknown automation task: {task_id}"
        )


    def active_execution_status(
        self,
        task_id,
    ):
        self.find_task(task_id)

        lock = self.lock_repository.get(
            task_id
        )

        if lock is None:
            return {
                "task_id": task_id,
                "running": False,
                "started_at": None,
                "expires_at": None,
                "elapsed_seconds": None,
            }

        def normalize_timestamp(value):
            if value is None:
                return None

            if isinstance(value, datetime):
                parsed = value
            else:
                parsed = datetime.fromisoformat(
                    str(value)
                )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        started_at = normalize_timestamp(
            lock["locked_at"]
        )

        expires_at = normalize_timestamp(
            lock["expires_at"]
        )

        now = datetime.now(
            timezone.utc
        )

        if expires_at <= now:
            return {
                "task_id": task_id,
                "running": False,
                "started_at": None,
                "expires_at": None,
                "elapsed_seconds": None,
            }

        elapsed_seconds = max(
            (
                now
                - started_at
            ).total_seconds(),
            0,
        )

        return {
            "task_id": task_id,
            "running": True,
            "started_at": started_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "elapsed_seconds": round(
                elapsed_seconds,
                3,
            ),
        }


    def run(
        self,
        task_id,
        limit=None,
        confirmed=False,
        workflow_execution_id=None,
    ):

        policy = self.validate_execution_policy(
            task_id,
            confirmed=confirmed,
        )

        timeout = policy["timeout_seconds"]

        if timeout is None:
            lease_seconds = (
                self.lock_repository.DEFAULT_LEASE_SECONDS
            )
        else:
            lease_seconds = (
                (timeout * policy["retry_attempts"])
                + (
                    policy["retry_delay_seconds"]
                    * max(
                        policy["retry_attempts"] - 1,
                        0,
                    )
                )
                + 60
            )

        if not self.lock_repository.acquire(
            task_id,
            lease_seconds=lease_seconds,
        ):
            raise AutomationAlreadyRunningError(
                f"Automation task is already running: {task_id}"
            )

        logger.info(
            "Automation execution started: %s",
            task_id,
        )

        started = time.perf_counter()

        executed_at = datetime.now(
            timezone.utc
        ).isoformat()

        attempts = policy["retry_attempts"]
        delay = policy["retry_delay_seconds"]

        try:

            last_error = None

            for attempt in range(
                1,
                attempts + 1,
            ):

                attempt_started = (
                    time.perf_counter()
                )

                attempt_executed_at = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                try:

                    result = self._execute_task(
                        task_id,
                        limit=limit,
                        timeout=policy["timeout_seconds"],
                    )

                    result = self._normalize_result(
                        result
                    )

                    success = True

                    if isinstance(result, dict):
                        if "success" in result:
                            success = bool(
                                result["success"]
                            )

                    attempt_elapsed = round(
                        time.perf_counter()
                        - attempt_started,
                        3,
                    )

                    execution = {
                        "task": task_id,
                        "executed_at": executed_at,
                        "attempt": attempt,
                        "attempts": attempts,
                        "result": result,
                    }

                    execution_id = self.execution_repository.save(
                        task_id=task_id,
                        success=success,
                        elapsed=attempt_elapsed,
                        result=execution,
                        executed_at=attempt_executed_at,
                        workflow_execution_id=workflow_execution_id,
                    )

                    execution["id"] = execution_id

                    if success:
                        return execution

                    last_error = None
                    retry_error_category = "result"

                except Exception as error:

                    attempt_elapsed = round(
                        time.perf_counter()
                        - attempt_started,
                        3,
                    )

                    failure_result = {
                        "success": False,
                        "error": str(error),
                    }

                    classification = self._classify_error(
                        error
                    )

                    retry_error_category = classification[
                        "category"
                    ]

                    failure_result.update(
                        {
                            "error_category": classification[
                                "category"
                            ],
                            "retryable": classification[
                                "retryable"
                            ],
                        }
                    )

                    logger.error(
                        "Automation execution failed: %s",
                        task_id,
                        extra={
                            "attempt": attempt,
                            "attempts": attempts,
                            "error_category": classification["category"],
                            "retryable": classification["retryable"],
                        },
                    )

                    if isinstance(
                        error,
                        TimeoutError,
                    ):
                        failure_result["error_type"] = (
                            "timeout"
                        )

                    failure = {
                        "task": task_id,
                        "executed_at": executed_at,
                        "attempt": attempt,
                        "attempts": attempts,
                        "result": failure_result,
                    }

                    execution_id = self.execution_repository.save(
                        task_id=task_id,
                        success=False,
                        elapsed=attempt_elapsed,
                        result=failure,
                        executed_at=attempt_executed_at,
                        workflow_execution_id=workflow_execution_id,
                    )

                    failure["id"] = execution_id

                    last_error = error

                    if not classification["retryable"]:
                        break

                if attempt < attempts:
                    logger.info(
                        "Automation execution retrying: %s",
                        task_id,
                        extra={
                            "attempt": attempt,
                            "next_attempt": attempt + 1,
                            "error_category": retry_error_category,
                        },
                    )

                    if delay > 0:
                        time.sleep(
                            delay
                        )

            if last_error is not None:
                raise last_error

            return execution

        finally:
            self.lock_repository.release(
                task_id
            )
