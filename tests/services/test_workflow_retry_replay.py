from himp.services.workflow_retry_replay import (
    WorkflowRetryReplayError,
    WorkflowRetryReplayService,
)


class FakeWorkflowRepository:

    def get_task(
        self,
        workflow_id,
        task_id,
    ):
        if (
            workflow_id == 1
            and task_id == "health_check"
        ):
            return {
                "workflow_id": 1,
                "task_id": "health_check",
            }

        return None


class FakeWorkflowService:

    def __init__(self):
        self.repository = (
            FakeWorkflowRepository()
        )

    def get_workflow(
        self,
        workflow_id,
    ):
        if workflow_id != 1:
            raise ValueError(
                "Workflow does not exist"
            )

        return {
            "id": 1,
            "name": "Test Workflow",
        }


class FakeWorkflowExecutionRepository:

    def __init__(self):
        self.rows = {
            "source-run": {
                "workflow_id": 1,
                "workflow_execution_id": (
                    "source-run"
                ),
                "completed_at": (
                    "2026-08-22T00:00:00+00:00"
                ),
                "success": False,
            },
            "running-run": {
                "workflow_id": 1,
                "workflow_execution_id": (
                    "running-run"
                ),
                "completed_at": None,
                "success": None,
            },
        }

    def find(
        self,
        execution_id,
    ):
        return self.rows.get(
            execution_id
        )


class FakeAutomationExecutionRepository:

    def __init__(self):
        self.rows = {
            723: {
                "id": 723,
                "task_id": "health_check",
                "workflow_execution_id": (
                    "source-run"
                ),
                "success": False,
            },
            724: {
                "id": 724,
                "task_id": "health_check",
                "workflow_execution_id": (
                    "source-run"
                ),
                "success": True,
            },
        }

    def find(
        self,
        execution_id,
    ):
        return self.rows.get(
            execution_id
        )


class FakeAutomationService:

    def __init__(self):
        self.execution_repository = (
            FakeAutomationExecutionRepository()
        )
        self.calls = []

    def run(
        self,
        task_id,
        **kwargs,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                **kwargs,
            }
        )

        return {
            "id": 900,
            "task": task_id,
            "result": {
                "success": True,
            },
        }


class FakeWorkflowExecutionService:

    def __init__(self):
        self.workflow_execution_repository = (
            FakeWorkflowExecutionRepository()
        )
        self.automation_service = (
            FakeAutomationService()
        )
        self.calls = []

    def execute(
        self,
        workflow_id,
        **kwargs,
    ):
        self.calls.append(
            {
                "workflow_id": workflow_id,
                **kwargs,
            }
        )

        return {
            "workflow": {
                "id": workflow_id,
            },
            "workflow_execution_id": (
                "new-run"
            ),
            "success": True,
            "task_count": 1,
            "executed_tasks": [
                "health_check",
            ],
            "failed_tasks": [],
            "skipped_tasks": [],
            "executions": [],
        }


def make_service():
    workflow_service = (
        FakeWorkflowService()
    )

    execution_service = (
        FakeWorkflowExecutionService()
    )

    return (
        WorkflowRetryReplayService(
            workflow_service=(
                workflow_service
            ),
            workflow_execution_service=(
                execution_service
            ),
        ),
        execution_service,
    )


def test_retry_failed_step_creates_standalone_execution_with_provenance():
    service, execution_service = (
        make_service()
    )

    result = service.retry_failed_step(
        1,
        "source-run",
        723,
    )

    assert result["action"] == (
        "retry_failed_step"
    )

    assert (
        execution_service
        .automation_service
        .calls
    ) == [
        {
            "task_id": "health_check",
            "confirmed": False,
            "workflow_execution_id": None,
            "retry_of_execution_id": 723,
            "retry_source_workflow_execution_id": (
                "source-run"
            ),
        }
    ]


def test_retry_rejects_successful_source_execution():
    service, _ = make_service()

    try:
        service.retry_failed_step(
            1,
            "source-run",
            724,
        )
    except WorkflowRetryReplayError as error:
        assert "Only failed" in str(
            error
        )
    else:
        raise AssertionError(
            "Expected retry rejection"
        )


def test_retry_rejects_execution_from_another_workflow_run():
    service, execution_service = (
        make_service()
    )

    execution_service\
        .automation_service\
        .execution_repository\
        .rows[725] = {
            "id": 725,
            "task_id": "health_check",
            "workflow_execution_id": (
                "different-run"
            ),
            "success": False,
        }

    try:
        service.retry_failed_step(
            1,
            "source-run",
            725,
        )
    except WorkflowRetryReplayError as error:
        assert "does not belong" in str(
            error
        )
    else:
        raise AssertionError(
            "Expected workflow correlation rejection"
        )


def test_retry_rejects_running_workflow_execution():
    service, _ = make_service()

    try:
        service.retry_failed_step(
            1,
            "running-run",
            723,
        )
    except WorkflowRetryReplayError as error:
        assert "still running" in str(
            error
        )
    else:
        raise AssertionError(
            "Expected running workflow rejection"
        )


def test_replay_creates_new_workflow_execution_with_provenance():
    service, execution_service = (
        make_service()
    )

    result = service.replay_workflow(
        1,
        "source-run",
        confirmed=True,
    )

    assert result[
        "workflow_execution_id"
    ] == "new-run"

    assert result[
        "source_workflow_execution_id"
    ] == "source-run"

    assert result["definition"] == (
        "current"
    )

    assert execution_service.calls == [
        {
            "workflow_id": 1,
            "limit": None,
            "confirmed": True,
            "replay_of_workflow_execution_id": (
                "source-run"
            ),
        }
    ]


def test_capabilities_explicitly_disable_resume():
    service, _ = make_service()

    result = service.capabilities(
        1,
        "source-run",
    )

    assert result[
        "retry_failed_step"
    ] is True

    assert result[
        "replay_workflow"
    ] is True

    assert result[
        "resume_workflow"
    ] is False

    assert result[
        "replay_definition"
    ] == "current"

    assert "does not persist" in (
        result["resume_reason"]
    )
