"""
Workflow retry and replay service.

Provides safe operator actions over existing persisted workflow and
automation execution records.

This service does not implement another execution engine:

* failed-step retry delegates to AutomationService.run()
* workflow replay delegates to WorkflowExecutionService.execute()
* historical workflow and automation execution records are never mutated
* resume is intentionally unsupported because HIMP does not persist a
  deterministic resumable workflow checkpoint
"""


class WorkflowRetryReplayError(ValueError):
    """Rejected retry/replay request."""


class WorkflowRetryReplayService:

    def __init__(
        self,
        workflow_service,
        workflow_execution_service,
    ):
        self.workflow_service = workflow_service
        self.workflow_execution_service = (
            workflow_execution_service
        )

    @property
    def workflow_execution_repository(self):
        return (
            self.workflow_execution_service
            .workflow_execution_repository
        )

    @property
    def automation_service(self):
        return (
            self.workflow_execution_service
            .automation_service
        )

    @property
    def automation_execution_repository(self):
        return (
            self.automation_service
            .execution_repository
        )

    def retry_failed_step(
        self,
        workflow_id,
        workflow_execution_id,
        execution_id,
        confirmed=False,
    ):
        """
        Retry one persisted failed workflow task as a NEW standalone
        automation execution.

        The new execution is not appended to the completed historical
        workflow execution. Retry provenance is stored separately.
        """

        workflow_run = self._completed_workflow_run(
            workflow_id,
            workflow_execution_id,
        )

        source_execution = (
            self.automation_execution_repository.find(
                execution_id
            )
        )

        if source_execution is None:
            raise WorkflowRetryReplayError(
                "Automation execution does not exist: "
                f"{execution_id}"
            )

        if (
            source_execution.get(
                "workflow_execution_id"
            )
            != workflow_execution_id
        ):
            raise WorkflowRetryReplayError(
                "Automation execution does not belong to "
                "the selected workflow execution."
            )

        if source_execution.get("success") is not False:
            raise WorkflowRetryReplayError(
                "Only failed automation executions can be retried."
            )

        task_id = source_execution.get(
            "task_id"
        )

        workflow_task = (
            self.workflow_service.repository.get_task(
                workflow_id,
                task_id,
            )
        )

        if workflow_task is None:
            raise WorkflowRetryReplayError(
                "Failed task is no longer part of the "
                "current workflow definition: "
                f"{task_id}"
            )

        execution = self.automation_service.run(
            task_id,
            confirmed=confirmed,
            workflow_execution_id=None,
            retry_of_execution_id=execution_id,
            retry_source_workflow_execution_id=(
                workflow_execution_id
            ),
        )

        return {
            "action": "retry_failed_step",
            "workflow_id": workflow_id,
            "source_workflow_execution_id": (
                workflow_execution_id
            ),
            "source_execution_id": execution_id,
            "task_id": task_id,
            "workflow_run": workflow_run,
            "execution": execution,
        }

    def replay_workflow(
        self,
        workflow_id,
        workflow_execution_id,
        limit=None,
        confirmed=False,
    ):
        """
        Execute the CURRENT workflow definition as a new workflow run.

        The new workflow execution stores provenance to the selected
        historical execution. This is deliberately not described as
        exact historical replay because HIMP does not persist workflow
        definition snapshots.
        """

        self._completed_workflow_run(
            workflow_id,
            workflow_execution_id,
        )

        result = (
            self.workflow_execution_service.execute(
                workflow_id,
                limit=limit,
                confirmed=confirmed,
                replay_of_workflow_execution_id=(
                    workflow_execution_id
                ),
            )
        )

        return {
            "action": "replay_workflow",
            "source_workflow_execution_id": (
                workflow_execution_id
            ),
            "definition": "current",
            **result,
        }

    def capabilities(
        self,
        workflow_id,
        workflow_execution_id,
    ):
        workflow_run = self._workflow_run(
            workflow_id,
            workflow_execution_id,
        )

        completed = (
            workflow_run.get("completed_at")
            is not None
        )

        return {
            "retry_failed_step": completed,
            "replay_workflow": completed,
            "resume_workflow": False,
            "resume_reason": (
                "HIMP does not persist a deterministic "
                "workflow resume checkpoint."
            ),
            "replay_definition": "current",
        }

    def _workflow_run(
        self,
        workflow_id,
        workflow_execution_id,
    ):
        self.workflow_service.get_workflow(
            workflow_id
        )

        workflow_run = (
            self.workflow_execution_repository.find(
                workflow_execution_id
            )
        )

        if workflow_run is None:
            raise WorkflowRetryReplayError(
                "Workflow execution does not exist: "
                f"{workflow_execution_id}"
            )

        if workflow_run["workflow_id"] != workflow_id:
            raise WorkflowRetryReplayError(
                "Workflow execution does not belong to "
                "the selected workflow."
            )

        return workflow_run

    def _completed_workflow_run(
        self,
        workflow_id,
        workflow_execution_id,
    ):
        workflow_run = self._workflow_run(
            workflow_id,
            workflow_execution_id,
        )

        if workflow_run.get(
            "completed_at"
        ) is None:
            raise WorkflowRetryReplayError(
                "Workflow execution is still running."
            )

        return workflow_run
