"""
Workflow History Service.
"""

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

            execution = dict(
                workflow_run
            )

            execution["workflow"] = workflow

            execution["executions"] = (
                self.automation_execution_repository.workflow_history(
                    workflow_run[
                        "workflow_execution_id"
                    ]
                )
            )

            history.append(execution)

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

        execution = dict(
            workflow_run
        )

        execution["workflow"] = workflow

        execution["executions"] = (
            self.automation_execution_repository.workflow_history(
                workflow_execution_id
            )
        )

        return execution
