import pytest

from himp.services.workflow_execution import WorkflowExecutionService


_UNSET = object()


class FakeWorkflowService:
    def __init__(
        self,
        workflow=_UNSET,
        validation=None,
        tasks=None,
        dependencies=None,
    ):
        self.workflow = (
            workflow
            if workflow is not _UNSET
            else {
                "id": 1,
                "name": "Infrastructure Refresh",
                "description": "Test workflow",
                "enabled": 1,
            }
        )

        self.validation = (
            validation
            if validation is not None
            else {
                "workflow_id": 1,
                "valid": True,
                "errors": [],
                "task_count": 3,
                "dependency_count": 2,
            }
        )

        self.tasks = (
            tasks
            if tasks is not None
            else [
                {
                    "id": 1,
                    "workflow_id": 1,
                    "task_id": "inventory_refresh",
                    "position": 1,
                },
                {
                    "id": 2,
                    "workflow_id": 1,
                    "task_id": "generate_reports",
                    "position": 2,
                },
                {
                    "id": 3,
                    "workflow_id": 1,
                    "task_id": "health_check",
                    "position": 3,
                },
            ]
        )

        self.dependencies = (
            dependencies
            if dependencies is not None
            else [
                {
                    "id": 1,
                    "workflow_id": 1,
                    "task_id": "generate_reports",
                    "depends_on_task_id": "inventory_refresh",
                },
                {
                    "id": 2,
                    "workflow_id": 1,
                    "task_id": "health_check",
                    "depends_on_task_id": "generate_reports",
                },
            ]
        )

        self.repository = self

        self.get_workflow_calls = []
        self.validate_workflow_calls = []
        self.list_tasks_calls = []
        self.list_dependencies_calls = []

    def get_workflow(self, workflow_id):
        self.get_workflow_calls.append(workflow_id)

        if self.workflow is None:
            from himp.services.workflows import WorkflowNotFoundError

            raise WorkflowNotFoundError(
                f"Workflow does not exist: {workflow_id}"
            )

        return self.workflow

    def validate_workflow(self, workflow_id):
        self.validate_workflow_calls.append(workflow_id)
        return self.validation

    def list_tasks(self, workflow_id):
        self.list_tasks_calls.append(workflow_id)
        return self.tasks

    def list_dependencies(self, workflow_id):
        self.list_dependencies_calls.append(workflow_id)
        return self.dependencies


class FakeAutomationService:
    def __init__(self):
        self.calls = []

    def run(
        self,
        task_id,
        limit=None,
        confirmed=False,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                "limit": limit,
                "confirmed": confirmed,
            }
        )

        return {
            "task_id": task_id,
            "success": True,
        }


def make_service(
    workflow_service=None,
    automation_service=None,
):
    workflow_service = (
        workflow_service
        or FakeWorkflowService()
    )

    automation_service = (
        automation_service
        or FakeAutomationService()
    )

    service = WorkflowExecutionService(
        workflow_service=workflow_service,
        automation_service=automation_service,
    )

    return (
        service,
        workflow_service,
        automation_service,
    )


def test_execute_runs_tasks_in_dependency_order():
    service, workflow_service, automation = (
        make_service()
    )

    result = service.execute(1)

    assert result["success"] is True
    assert result["task_count"] == 3

    assert result["executed_tasks"] == [
        "inventory_refresh",
        "generate_reports",
        "health_check",
    ]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == [
        "inventory_refresh",
        "generate_reports",
        "health_check",
    ]

    assert workflow_service.get_workflow_calls == [1]
    assert workflow_service.validate_workflow_calls == [1]
    assert workflow_service.list_tasks_calls == [1]
    assert workflow_service.list_dependencies_calls == [1]


def test_execute_returns_individual_execution_results():
    service, _, automation = make_service()

    result = service.execute(1)

    assert result["executions"] == [
        {
            "task_id": "inventory_refresh",
            "success": True,
        },
        {
            "task_id": "generate_reports",
            "success": True,
        },
        {
            "task_id": "health_check",
            "success": True,
        },
    ]

    assert len(automation.calls) == 3


def test_execute_passes_limit_and_confirmation_to_every_task():
    service, _, automation = make_service()

    result = service.execute(
        1,
        limit=25,
        confirmed=True,
    )

    assert result["success"] is True

    assert automation.calls == [
        {
            "task_id": "inventory_refresh",
            "limit": 25,
            "confirmed": True,
        },
        {
            "task_id": "generate_reports",
            "limit": 25,
            "confirmed": True,
        },
        {
            "task_id": "health_check",
            "limit": 25,
            "confirmed": True,
        },
    ]


def test_execute_rejects_invalid_workflow():
    workflow_service = FakeWorkflowService(
        validation={
            "workflow_id": 1,
            "valid": False,
            "errors": [
                "Unknown automation task: missing_task",
            ],
            "task_count": 1,
            "dependency_count": 0,
        }
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
    )

    with pytest.raises(
        ValueError,
        match="Workflow validation failed: "
        "Unknown automation task: missing_task",
    ):
        service.execute(1)

    assert automation.calls == []


def test_execute_propagates_missing_workflow():
    from himp.services.workflows import (
        WorkflowNotFoundError,
    )

    workflow_service = FakeWorkflowService(
        workflow=None,
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
    )

    with pytest.raises(
        WorkflowNotFoundError,
        match="Workflow does not exist: 1",
    ):
        service.execute(1)

    assert automation.calls == []


def test_execution_order_handles_independent_tasks():
    workflow_service = FakeWorkflowService(
        tasks=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_a",
                "position": 1,
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_b",
                "position": 2,
            },
            {
                "id": 3,
                "workflow_id": 1,
                "task_id": "task_c",
                "position": 3,
            },
        ],
        dependencies=[],
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
    )

    result = service.execute(1)

    assert result["executed_tasks"] == [
        "task_a",
        "task_b",
        "task_c",
    ]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == [
        "task_a",
        "task_b",
        "task_c",
    ]


def test_execution_order_resolves_dependencies_before_dependents():
    workflow_service = FakeWorkflowService(
        tasks=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_a",
                "position": 1,
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_b",
                "position": 2,
            },
            {
                "id": 3,
                "workflow_id": 1,
                "task_id": "task_c",
                "position": 3,
            },
        ],
        dependencies=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_c",
                "depends_on_task_id": "task_b",
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
        ],
    )

    service, _, _ = make_service(
        workflow_service=workflow_service,
    )

    assert service._execution_order(1) == [
        "task_a",
        "task_b",
        "task_c",
    ]


def test_execution_order_rejects_cycle():
    workflow_service = FakeWorkflowService(
        tasks=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_a",
                "position": 1,
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_b",
                "position": 2,
            },
        ],
        dependencies=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_a",
                "depends_on_task_id": "task_b",
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
        ],
    )

    service, _, _ = make_service(
        workflow_service=workflow_service,
    )

    with pytest.raises(
        ValueError,
        match="Workflow dependency cycle detected",
    ):
        service._execution_order(1)


def test_empty_workflow_returns_success_without_execution():
    workflow_service = FakeWorkflowService(
        tasks=[],
        dependencies=[],
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
    )

    result = service.execute(1)

    assert result["success"] is True
    assert result["task_count"] == 0
    assert result["executed_tasks"] == []
    assert result["executions"] == []
    assert automation.calls == []
