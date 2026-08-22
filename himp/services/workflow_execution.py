"""
Workflow execution orchestration service.
"""

from datetime import datetime, timezone
from uuid import uuid4

from himp.database.workflow_executions import (
    WorkflowExecutionRepository,
)
from himp.services.automation import AutomationService
from himp.services.workflows import (
    WorkflowNotFoundError,
    WorkflowService,
)


class WorkflowExecutionService:
    """
    Executes workflow tasks through the existing
    AutomationService execution engine.

    This service owns workflow orchestration only.
    AutomationService remains responsible for task
    execution policy, retries, timeouts, locking,
    and execution persistence.
    """

    def __init__(
        self,
        workflow_service=None,
        automation_service=None,
        workflow_execution_repository=None,
    ):
        self.workflow_service = (
            workflow_service
            or WorkflowService()
        )

        self.automation_service = (
            automation_service
            or AutomationService()
        )

        self.workflow_execution_repository = (
            workflow_execution_repository
            or WorkflowExecutionRepository()
        )

    def execute(
        self,
        workflow_id,
        limit=None,
        confirmed=False,
        replay_of_workflow_execution_id=None,
    ):
        workflow = self.workflow_service.get_workflow(
            workflow_id
        )

        validation = (
            self.workflow_service.validate_workflow(
                workflow_id
            )
        )

        if not validation["valid"]:
            raise ValueError(
                "Workflow validation failed: "
                + "; ".join(
                    validation["errors"]
                )
            )

        workflow_execution_id = str(
            uuid4()
        )

        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        self.workflow_execution_repository.create(
            workflow_id=workflow_id,
            workflow_execution_id=(
                workflow_execution_id
            ),
            started_at=started_at,
            replay_of_workflow_execution_id=(
                replay_of_workflow_execution_id
            ),
        )

        try:
            task_ids = self._execution_order(
                workflow_id
            )

            executions = []
            failed_tasks = []
            skipped_tasks = []

            dependency_map = self._dependency_map

            task_results = {}

            for task_id in task_ids:
                prerequisites = dependency_map.get(
                    task_id,
                    [],
                )

                failed_prerequisites = [
                    prerequisite
                    for prerequisite in prerequisites
                    if prerequisite in failed_tasks
                    or prerequisite in skipped_tasks
                ]

                if failed_prerequisites:
                    skipped_tasks.append(task_id)

                    task_results[task_id] = {
                        "task_id": task_id,
                        "success": False,
                        "skipped": True,
                        "reason": (
                            "Dependency failed or was skipped"
                        ),
                        "failed_dependencies": (
                            failed_prerequisites
                        ),
                    }

                    continue

                self.workflow_execution_repository.set_current_task(
                    workflow_execution_id,
                    task_id,
                )

                try:
                    execution = self.automation_service.run(
                        task_id,
                        limit=limit,
                        confirmed=confirmed,
                        workflow_execution_id=(
                            workflow_execution_id
                        ),
                    )

                except Exception as error:
                    execution = {
                        "task_id": task_id,
                        "success": False,
                        "error": str(error),
                    }

                executions.append(execution)
                task_results[task_id] = execution

                success = self._execution_success(
                    execution
                )

                if not success:
                    failed_tasks.append(task_id)

        except Exception:
            completed_at = datetime.now(
                timezone.utc
            ).isoformat()

            self.workflow_execution_repository.complete(
                workflow_execution_id=(
                    workflow_execution_id
                ),
                success=False,
                completed_at=completed_at,
            )

            raise

        workflow_success = not failed_tasks

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        self.workflow_execution_repository.complete(
            workflow_execution_id=(
                workflow_execution_id
            ),
            success=workflow_success,
            completed_at=completed_at,
        )

        return {
            "workflow": workflow,
            "workflow_execution_id": (
                workflow_execution_id
            ),
            "success": workflow_success,
            "task_count": len(task_ids),
            "executed_tasks": [
                task_id
                for task_id in task_ids
                if task_id not in skipped_tasks
            ],
            "failed_tasks": failed_tasks,
            "skipped_tasks": skipped_tasks,
            "executions": executions,
        }

    @staticmethod
    def _execution_success(
        execution,
    ):
        """
        Interpret the existing AutomationService execution envelope.

        AutomationService persists task success separately and returns
        an execution envelope whose normalized task result is stored
        under ``result``. Some callers/tests may also provide a direct
        top-level ``success`` field, so preserve support for both forms.
        """

        if not isinstance(execution, dict):
            return True

        if "success" in execution:
            return bool(
                execution["success"]
            )

        result = execution.get(
            "result"
        )

        if (
            isinstance(result, dict)
            and "success" in result
        ):
            return bool(
                result["success"]
            )

        return True

    def _execution_order(
        self,
        workflow_id,
    ):
        tasks = self.workflow_service.repository.list_tasks(
            workflow_id
        )

        dependencies = (
            self.workflow_service.repository.list_dependencies(
                workflow_id
            )
        )

        task_ids = [
            task["task_id"]
            for task in tasks
        ]

        graph = {
            task_id: []
            for task_id in task_ids
        }

        for dependency in dependencies:
            graph[
                dependency["task_id"]
            ].append(
                dependency[
                    "depends_on_task_id"
                ]
            )

        self._dependency_map = graph

        order = []
        visiting = set()
        visited = set()

        def visit(task_id):
            if task_id in visited:
                return

            if task_id in visiting:
                raise ValueError(
                    "Workflow dependency cycle detected"
                )

            visiting.add(task_id)

            for dependency in graph[
                task_id
            ]:
                visit(dependency)

            visiting.remove(task_id)
            visited.add(task_id)
            order.append(task_id)

        for task in tasks:
            visit(task["task_id"])

        return order
