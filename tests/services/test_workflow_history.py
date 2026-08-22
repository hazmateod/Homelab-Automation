import pytest

from himp.services.workflow_history import (
    WorkflowHistoryService,
)


DEFAULT_WORKFLOW = {
    "id": 1,
    "name": "Infrastructure Refresh",
    "description": "Test workflow",
    "enabled": 1,
}


class FakeWorkflowService:
    def __init__(self, workflow=DEFAULT_WORKFLOW):
        self.workflow = workflow

    def get_workflow(self, workflow_id):
        if self.workflow is None:
            from himp.services.workflows import (
                WorkflowNotFoundError,
            )

            raise WorkflowNotFoundError(
                f"Workflow does not exist: {workflow_id}"
            )

        return self.workflow


class FakeWorkflowExecutionRepository:
    def __init__(self, history=None):
        self.history_records = (
            history if history is not None else []
        )
        self.history_calls = []
        self.find_calls = []

    def workflow_history(
        self,
        workflow_id,
        limit=50,
    ):
        self.history_calls.append(
            {
                "workflow_id": workflow_id,
                "limit": limit,
            }
        )

        return self.history_records

    def find(self, workflow_execution_id):
        self.find_calls.append(
            workflow_execution_id
        )

        for execution in self.history_records:
            if (
                execution["workflow_execution_id"]
                == workflow_execution_id
            ):
                return execution

        return None


class FakeAutomationExecutionRepository:
    def __init__(self, histories=None):
        self.histories = (
            histories if histories is not None else {}
        )
        self.workflow_history_calls = []

    def workflow_history(
        self,
        workflow_execution_id,
    ):
        self.workflow_history_calls.append(
            workflow_execution_id
        )

        return self.histories.get(
            workflow_execution_id,
            [],
        )


def make_service(
    workflow_service=None,
    workflow_execution_repository=None,
    automation_execution_repository=None,
):
    workflow_service = (
        workflow_service
        or FakeWorkflowService()
    )

    workflow_execution_repository = (
        workflow_execution_repository
        or FakeWorkflowExecutionRepository()
    )

    automation_execution_repository = (
        automation_execution_repository
        or FakeAutomationExecutionRepository()
    )

    service = WorkflowHistoryService(
        workflow_service=workflow_service,
        workflow_execution_repository=(
            workflow_execution_repository
        ),
        automation_execution_repository=(
            automation_execution_repository
        ),
    )

    return (
        service,
        workflow_service,
        workflow_execution_repository,
        automation_execution_repository,
    )


def test_history_returns_workflow_runs_with_task_history():
    workflow_runs = [
        {
            "id": 2,
            "workflow_id": 1,
            "workflow_execution_id": "run-002",
            "started_at": "2026-08-15T00:05:00+00:00",
            "completed_at": "2026-08-15T00:06:00+00:00",
            "success": True,
        },
        {
            "id": 1,
            "workflow_id": 1,
            "workflow_execution_id": "run-001",
            "started_at": "2026-08-15T00:01:00+00:00",
            "completed_at": "2026-08-15T00:02:00+00:00",
            "success": False,
        },
    ]

    task_histories = {
        "run-002": [
            {
                "id": 20,
                "task_id": "inventory_refresh",
                "workflow_execution_id": "run-002",
                "success": True,
            },
        ],
        "run-001": [
            {
                "id": 10,
                "task_id": "inventory_refresh",
                "workflow_execution_id": "run-001",
                "success": False,
            },
        ],
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=workflow_runs,
        )
    )

    automation_repository = (
        FakeAutomationExecutionRepository(
            histories=task_histories,
        )
    )

    (
        service,
        _,
        _,
        _,
    ) = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
        automation_execution_repository=(
            automation_repository
        ),
    )

    history = service.history(1, limit=25)

    assert len(history) == 2

    assert history[0]["workflow"] == {
        "id": 1,
        "name": "Infrastructure Refresh",
        "description": "Test workflow",
        "enabled": 1,
    }

    assert history[0]["workflow_execution_id"] == (
        "run-002"
    )

    assert history[0]["executions"] == (
        task_histories["run-002"]
    )

    assert history[1]["workflow_execution_id"] == (
        "run-001"
    )

    assert history[1]["executions"] == (
        task_histories["run-001"]
    )

    assert execution_repository.history_calls == [
        {
            "workflow_id": 1,
            "limit": 25,
        }
    ]

    assert (
        automation_repository.workflow_history_calls
        == [
            "run-002",
            "run-001",
        ]
    )


def test_history_returns_empty_list_when_workflow_has_no_runs():
    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[],
        )
    )

    (
        service,
        _,
        _,
        automation_repository,
    ) = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
    )

    history = service.history(1)

    assert history == []
    assert (
        automation_repository.workflow_history_calls
        == []
    )


def test_history_propagates_missing_workflow():
    workflow_service = FakeWorkflowService(
        workflow=None,
    )

    service, _, _, _ = make_service(
        workflow_service=workflow_service,
    )

    with pytest.raises(
        Exception,
        match="Workflow does not exist: 1",
    ):
        service.history(1)


def test_get_returns_one_workflow_run_with_task_history():
    workflow_run = {
        "id": 7,
        "workflow_id": 1,
        "workflow_execution_id": "run-007",
        "started_at": "2026-08-15T01:00:00+00:00",
        "completed_at": "2026-08-15T01:01:00+00:00",
        "success": True,
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[workflow_run],
        )
    )

    automation_repository = (
        FakeAutomationExecutionRepository(
            histories={
                "run-007": [
                    {
                        "id": 70,
                        "task_id": "health_check",
                        "workflow_execution_id": "run-007",
                        "success": True,
                    },
                ],
            },
        )
    )

    (
        service,
        _,
        _,
        _,
    ) = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
        automation_execution_repository=(
            automation_repository
        ),
    )

    result = service.get(
        1,
        "run-007",
    )

    assert result["workflow"] == {
        "id": 1,
        "name": "Infrastructure Refresh",
        "description": "Test workflow",
        "enabled": 1,
    }

    assert result["workflow_execution_id"] == (
        "run-007"
    )

    assert result["executions"] == [
        {
            "id": 70,
            "task_id": "health_check",
            "workflow_execution_id": "run-007",
            "success": True,
        },
    ]

    assert (
        execution_repository.find_calls
        == ["run-007"]
    )


def test_get_returns_none_for_unknown_workflow_run():
    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[],
        )
    )

    service, _, _, _ = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
    )

    assert service.get(
        1,
        "missing-run",
    ) is None


def test_get_rejects_run_belonging_to_another_workflow():
    workflow_run = {
        "id": 7,
        "workflow_id": 2,
        "workflow_execution_id": "run-007",
        "started_at": "2026-08-15T01:00:00+00:00",
        "completed_at": "2026-08-15T01:01:00+00:00",
        "success": True,
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[workflow_run],
        )
    )

    service, _, _, _ = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
    )

    assert service.get(
        1,
        "run-007",
    ) is None


def test_get_builds_ordered_execution_timeline():
    workflow_run = {
        "id": 10,
        "workflow_id": 1,
        "workflow_execution_id": "run-timeline",
        "started_at": "2026-08-21T20:00:00+00:00",
        "completed_at": "2026-08-21T20:01:00+00:00",
        "success": True,
        "current_task_id": None,
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[workflow_run],
        )
    )

    automation_repository = (
        FakeAutomationExecutionRepository(
            histories={
                "run-timeline": [
                    {
                        "id": 22,
                        "task_id": "generate_reports",
                        "workflow_execution_id": "run-timeline",
                        "success": True,
                        "elapsed": 20.0,
                        "executed_at": "2026-08-21T20:00:30+00:00",
                        "result": {"status": "ok"},
                    },
                    {
                        "id": 21,
                        "task_id": "health_check",
                        "workflow_execution_id": "run-timeline",
                        "success": True,
                        "elapsed": 5.0,
                        "executed_at": "2026-08-21T20:00:05+00:00",
                        "result": {"status": "ok"},
                    },
                ],
            },
        )
    )

    service, _, _, _ = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
        automation_execution_repository=(
            automation_repository
        ),
    )

    result = service.get(
        1,
        "run-timeline",
    )

    assert result["status"] == "SUCCESS"
    assert result["duration_seconds"] == 60.0

    assert [
        item["task_id"]
        for item in result["executions"]
    ] == [
        "health_check",
        "generate_reports",
    ]

    assert [
        event["type"]
        for event in result["timeline"]
    ] == [
        "workflow_started",
        "task_execution",
        "task_execution",
        "workflow_completed",
    ]

    assert result["timeline"][1]["task_id"] == (
        "health_check"
    )

    assert result["timeline"][1]["status"] == (
        "SUCCESS"
    )

    assert result["timeline"][2]["task_id"] == (
        "generate_reports"
    )


def test_get_reports_failed_workflow_and_failed_task():
    workflow_run = {
        "id": 11,
        "workflow_id": 1,
        "workflow_execution_id": "run-failed",
        "started_at": "2026-08-21T21:00:00+00:00",
        "completed_at": "2026-08-21T21:00:15+00:00",
        "success": False,
        "current_task_id": None,
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[workflow_run],
        )
    )

    automation_repository = (
        FakeAutomationExecutionRepository(
            histories={
                "run-failed": [
                    {
                        "id": 30,
                        "task_id": "inventory_refresh",
                        "workflow_execution_id": "run-failed",
                        "success": False,
                        "elapsed": 12.5,
                        "executed_at": "2026-08-21T21:00:02+00:00",
                        "result": {
                            "error": "inventory failed",
                        },
                    },
                ],
            },
        )
    )

    service, _, _, _ = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
        automation_execution_repository=(
            automation_repository
        ),
    )

    result = service.get(
        1,
        "run-failed",
    )

    assert result["status"] == "FAILED"
    assert result["duration_seconds"] == 15.0

    task_event = result["timeline"][1]

    assert task_event["type"] == (
        "task_execution"
    )

    assert task_event["status"] == "FAILED"

    assert task_event["result"] == {
        "error": "inventory failed",
    }

    assert result["timeline"][-1] == {
        "type": "workflow_completed",
        "status": "FAILED",
        "timestamp": "2026-08-21T21:00:15+00:00",
    }


def test_get_reports_running_workflow_current_task():
    workflow_run = {
        "id": 12,
        "workflow_id": 1,
        "workflow_execution_id": "run-running",
        "started_at": "2026-08-21T22:00:00+00:00",
        "completed_at": None,
        "success": None,
        "current_task_id": "generate_reports",
    }

    execution_repository = (
        FakeWorkflowExecutionRepository(
            history=[workflow_run],
        )
    )

    service, _, _, _ = make_service(
        workflow_execution_repository=(
            execution_repository
        ),
    )

    result = service.get(
        1,
        "run-running",
    )

    assert result["status"] == "RUNNING"
    assert result["duration_seconds"] is None

    assert result["timeline"] == [
        {
            "type": "workflow_started",
            "status": "RUNNING",
            "timestamp": "2026-08-21T22:00:00+00:00",
        },
        {
            "type": "current_task",
            "task_id": "generate_reports",
            "status": "RUNNING",
            "timestamp": None,
        },
    ]


def test_duration_handles_naive_and_timezone_timestamps():
    assert WorkflowHistoryService._duration_seconds(
        "2026-08-21 20:00:00",
        "2026-08-21T20:00:30+00:00",
    ) == 30.0


def test_duration_returns_none_for_invalid_timestamp():
    assert WorkflowHistoryService._duration_seconds(
        "invalid",
        "2026-08-21T20:00:30+00:00",
    ) is None
