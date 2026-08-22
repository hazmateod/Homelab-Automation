"""
Workflow History Service.

Provides workflow execution history and operator-readable timeline
composition using the existing workflow and automation execution
repositories.

This service does not create or persist a second workflow-history model.
WorkflowExecutionRepository remains authoritative for workflow-level
execution state and AutomationExecutionRepository remains authoritative
for individual executed workflow tasks.
"""

from datetime import datetime, timezone

from himp.database.automation_executions import (
    AutomationExecutionRepository,
)
from himp.database.workflow_executions import (
    WorkflowExecutionRepository,
)
from himp.services.workflows import (
    WorkflowService,
)


class WorkflowHistoryService:

    def __init__(
        self,
        workflow_service=None,
        workflow_execution_repository=None,
        automation_execution_repository=None,
    ):

        self.workflow_service = (
            workflow_service
            or WorkflowService()
        )

        self.workflow_execution_repository = (
            workflow_execution_repository
            or WorkflowExecutionRepository()
        )

        self.automation_execution_repository = (
            automation_execution_repository
            or AutomationExecutionRepository()
        )

    def history(
        self,
        workflow_id,
        limit=50,
    ):

        workflow = (
            self.workflow_service.get_workflow(
                workflow_id
            )
        )

        workflow_runs = (
            self.workflow_execution_repository.workflow_history(
                workflow_id,
                limit=limit,
            )
        )

        history = []

        for workflow_run in workflow_runs:
            history.append(
                self._compose_execution(
                    workflow,
                    workflow_run,
                )
            )

        return history

    def get(
        self,
        workflow_id,
        workflow_execution_id,
    ):

        workflow = (
            self.workflow_service.get_workflow(
                workflow_id
            )
        )

        workflow_run = (
            self.workflow_execution_repository.find(
                workflow_execution_id
            )
        )

        if workflow_run is None:
            return None

        if workflow_run["workflow_id"] != workflow_id:
            return None

        return self._compose_execution(
            workflow,
            workflow_run,
        )

    def _compose_execution(
        self,
        workflow,
        workflow_run,
    ):
        """
        Compose one workflow run from existing persisted records.

        No additional execution state is created here.
        """

        execution = dict(
            workflow_run
        )

        executions = list(
            self.automation_execution_repository.workflow_history(
                workflow_run[
                    "workflow_execution_id"
                ]
            )
        )

        ordered_executions = sorted(
            executions,
            key=self._execution_sort_key,
        )

        execution["workflow"] = workflow

        # Preserve the established API contract.
        execution["executions"] = ordered_executions

        execution["status"] = self._workflow_status(
            workflow_run
        )

        execution["duration_seconds"] = (
            self._duration_seconds(
                workflow_run.get("started_at"),
                workflow_run.get("completed_at"),
            )
        )

        execution["timeline"] = self._timeline(
            workflow_run,
            ordered_executions,
        )

        return execution

    def _timeline(
        self,
        workflow_run,
        executions,
    ):
        """
        Build a truthful timeline exclusively from persisted state.

        Skipped tasks are intentionally not synthesized because the
        current workflow execution engine does not persist skipped-task
        records after the immediate execution response.
        """

        timeline = []

        started_at = workflow_run.get(
            "started_at"
        )

        if started_at is not None:
            timeline.append(
                {
                    "type": "workflow_started",
                    "status": "RUNNING",
                    "timestamp": started_at,
                }
            )

        prior_successful_task = None

        for execution in executions:

            success = bool(
                execution.get("success")
            )

            event = {
                "type": "task_execution",
                "execution_id": execution.get(
                    "id"
                ),
                "task_id": execution.get(
                    "task_id"
                ),
                "status": (
                    "SUCCESS"
                    if success
                    else "FAILED"
                ),
                "timestamp": execution.get(
                    "executed_at"
                ),
                "duration_seconds": execution.get(
                    "elapsed"
                ),
                "result": execution.get(
                    "result"
                ),
            }

            if success:
                prior_successful_task = {
                    "execution_id": execution.get(
                        "id"
                    ),
                    "task_id": execution.get(
                        "task_id"
                    ),
                    "timestamp": execution.get(
                        "executed_at"
                    ),
                    "duration_seconds": execution.get(
                        "elapsed"
                    ),
                }

            else:
                event["failure_analysis"] = (
                    self._failure_analysis(
                        execution,
                        prior_successful_task,
                    )
                )

            timeline.append(event)

        completed_at = workflow_run.get(
            "completed_at"
        )

        if completed_at is not None:
            timeline.append(
                {
                    "type": "workflow_completed",
                    "status": self._workflow_status(
                        workflow_run
                    ),
                    "timestamp": completed_at,
                }
            )

        elif workflow_run.get(
            "current_task_id"
        ):
            timeline.append(
                {
                    "type": "current_task",
                    "task_id": workflow_run[
                        "current_task_id"
                    ],
                    "status": "RUNNING",
                    "timestamp": None,
                }
            )

        return timeline

    @classmethod
    def _failure_analysis(
        cls,
        execution,
        prior_successful_task=None,
    ):
        """
        Compose operator-readable failure evidence exclusively from
        persisted AutomationExecutionRepository data.

        No target, error, or component information is synthesized when
        it was not persisted by the underlying automation.
        """

        result = execution.get(
            "result"
        )

        if not isinstance(result, dict):
            result = {}

        nested_result = result.get(
            "result"
        )

        if isinstance(nested_result, dict):
            payload = nested_result
        else:
            payload = result

        component_rows = payload.get(
            "executions"
        )

        if not isinstance(
            component_rows,
            list,
        ):
            component_rows = []

        failed_components = []
        successful_components_before_failure = []
        failure_seen = False

        for component in component_rows:

            if not isinstance(
                component,
                dict,
            ):
                continue

            component_name = (
                component.get("plugin")
                or component.get("task_id")
                or component.get("task")
                or component.get("name")
            )

            component_success = component.get(
                "success"
            )

            if component_success is False:
                failure_seen = True

                failed_components.append(
                    {
                        "component": component_name,
                        "return_code": component.get(
                            "return_code"
                        ),
                        "error": component.get(
                            "error"
                        ),
                        "stderr": component.get(
                            "stderr"
                        ),
                        "elapsed": component.get(
                            "elapsed"
                        ),
                        "warnings": component.get(
                            "warnings"
                        ),
                        "artifacts": component.get(
                            "artifacts"
                        ),
                    }
                )

            elif (
                component_success is True
                and not failure_seen
                and component_name is not None
            ):
                successful_components_before_failure.append(
                    {
                        "component": component_name,
                        "return_code": component.get(
                            "return_code"
                        ),
                        "elapsed": component.get(
                            "elapsed"
                        ),
                    }
                )

        target = cls._first_present(
            payload.get("target"),
            result.get("target"),
            payload.get("host"),
            result.get("host"),
            payload.get("limit"),
            result.get("limit"),
        )

        return_code = cls._first_present(
            payload.get("return_code"),
            result.get("return_code"),
        )

        stderr = cls._first_present(
            payload.get("stderr"),
            result.get("stderr"),
        )

        error = cls._first_present(
            payload.get("error"),
            result.get("error"),
            stderr,
        )

        if error is None:
            for component in failed_components:
                error = cls._first_present(
                    component.get("error"),
                    component.get("stderr"),
                )

                if error is not None:
                    break

        return {
            "failed_task": execution.get(
                "task_id"
            ),
            "execution_id": execution.get(
                "id"
            ),
            "target": target,
            "return_code": return_code,
            "stderr": stderr,
            "error": error,
            "failed_components": failed_components,
            "prior_successful_task": prior_successful_task,
            "prior_successful_components": (
                successful_components_before_failure
            ),
        }

    @staticmethod
    def _first_present(
        *values,
    ):
        for value in values:
            if value is None:
                continue

            if isinstance(
                value,
                str,
            ):
                if value.strip():
                    return value

                continue

            return value

        return None

    @staticmethod
    def _workflow_status(
        workflow_run,
    ):

        completed_at = workflow_run.get(
            "completed_at"
        )

        success = workflow_run.get(
            "success"
        )

        if completed_at is None:
            return "RUNNING"

        if success is True:
            return "SUCCESS"

        if success is False:
            return "FAILED"

        return "UNKNOWN"

    @classmethod
    def _duration_seconds(
        cls,
        started_at,
        completed_at,
    ):

        if (
            started_at is None
            or completed_at is None
        ):
            return None

        started = cls._parse_timestamp(
            started_at
        )

        completed = cls._parse_timestamp(
            completed_at
        )

        if (
            started is None
            or completed is None
        ):
            return None

        duration = (
            completed - started
        ).total_seconds()

        return max(
            0.0,
            duration,
        )

    @staticmethod
    def _parse_timestamp(
        value,
    ):

        if isinstance(
            value,
            datetime,
        ):
            timestamp = value

        elif isinstance(
            value,
            str,
        ):
            try:
                timestamp = datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError:
                return None

        else:
            return None

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        return timestamp.astimezone(
            timezone.utc
        )

    @classmethod
    def _execution_sort_key(
        cls,
        execution,
    ):
        timestamp = cls._parse_timestamp(
            execution.get(
                "executed_at"
            )
        )

        if timestamp is None:
            timestamp = datetime.min.replace(
                tzinfo=timezone.utc
            )

        execution_id = (
            execution.get("id")
            if execution.get("id") is not None
            else 0
        )

        return (
            timestamp,
            execution_id,
        )
