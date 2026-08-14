"""
Workflow execution orchestration service.
"""

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
    ):
        self.workflow_service = (
            workflow_service
            or WorkflowService()
        )

        self.automation_service = (
            automation_service
            or AutomationService()
        )

    def execute(
        self,
        workflow_id,
        limit=None,
        confirmed=False,
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

        task_ids = self._execution_order(
            workflow_id
        )

        executions = []

        for task_id in task_ids:
            execution = self.automation_service.run(
                task_id,
                limit=limit,
                confirmed=confirmed,
            )

            executions.append(
                execution
            )

        return {
            "workflow": workflow,
            "success": True,
            "task_count": len(task_ids),
            "executed_tasks": task_ids,
            "executions": executions,
        }

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
