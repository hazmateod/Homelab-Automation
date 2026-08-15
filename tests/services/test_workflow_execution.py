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


class FakeWorkflowExecutionRepository:
    def __init__(self):
        self.created = []
        self.completed = []
        self.current_tasks = []

    def create(
        self,
        workflow_id,
        workflow_execution_id,
        started_at=None,
    ):
        execution = {
            "id": len(self.created) + 1,
            "workflow_id": workflow_id,
            "workflow_execution_id": workflow_execution_id,
            "started_at": started_at,
            "completed_at": None,
            "success": None,
        }

        self.created.append(execution)

        return execution

    def complete(
        self,
        workflow_execution_id,
        success,
        completed_at=None,
    ):
        execution = next(
            execution
            for execution in self.created
            if execution["workflow_execution_id"]
            == workflow_execution_id
        )

        execution = {
            **execution,
            "completed_at": completed_at,
            "success": success,
        }

        self.completed.append(execution)

        return execution

    def set_current_task(
        self,
        workflow_execution_id,
        current_task_id,
    ):
        execution = next(
            execution
            for execution in self.created
            if execution["workflow_execution_id"]
            == workflow_execution_id
        )

        execution["current_task_id"] = current_task_id

        self.current_tasks.append(
            {
                "workflow_execution_id": workflow_execution_id,
                "current_task_id": current_task_id,
            }
        )

        return execution


class FakeAutomationService:
    def __init__(
        self,
        outcomes=None,
        exceptions=None,
    ):
        self.calls = []
        self.outcomes = outcomes or {}
        self.exceptions = exceptions or {}

    def run(
        self,
        task_id,
        limit=None,
        confirmed=False,
        workflow_execution_id=None,
    ):
        self.calls.append(
            {
                "task_id": task_id,
                "limit": limit,
                "confirmed": confirmed,
                "workflow_execution_id": (
                    workflow_execution_id
                ),
            }
        )

        if task_id in self.exceptions:
            raise self.exceptions[task_id]

        return self.outcomes.get(
            task_id,
            {
                "task_id": task_id,
                "success": True,
            },
        )


def make_service(
    workflow_service=None,
    automation_service=None,
    workflow_execution_repository=None,
):
    workflow_service = (
        workflow_service
        or FakeWorkflowService()
    )

    automation_service = (
        automation_service
        or FakeAutomationService()
    )

    workflow_execution_repository = (
        workflow_execution_repository
        or FakeWorkflowExecutionRepository()
    )

    service = WorkflowExecutionService(
        workflow_service=workflow_service,
        automation_service=automation_service,
        workflow_execution_repository=(
            workflow_execution_repository
        ),
    )

    return (
        service,
        workflow_service,
        automation_service,
    )


def test_execute_creates_workflow_execution_record():
    repository = FakeWorkflowExecutionRepository()

    service, _, _ = make_service(
        workflow_execution_repository=repository,
    )

    result = service.execute(1)

    assert len(repository.created) == 1

    execution = repository.created[0]

    assert execution["workflow_id"] == 1
    assert execution["workflow_execution_id"] == (
        result["workflow_execution_id"]
    )


def test_execute_completes_successful_workflow_execution():
    repository = FakeWorkflowExecutionRepository()

    service, _, _ = make_service(
        workflow_execution_repository=repository,
    )

    result = service.execute(1)

    assert result["success"] is True
    assert len(repository.completed) == 1

    execution = repository.completed[0]

    assert execution["workflow_id"] == 1
    assert execution["workflow_execution_id"] == (
        result["workflow_execution_id"]
    )
    assert execution["success"] is True


def test_execute_completes_failed_workflow_execution():
    repository = FakeWorkflowExecutionRepository()

    automation = FakeAutomationService(
        outcomes={
            "generate_reports": {
                "task_id": "generate_reports",
                "success": False,
            },
        },
    )

    service, _, _ = make_service(
        automation_service=automation,
        workflow_execution_repository=repository,
    )

    result = service.execute(1)

    assert result["success"] is False
    assert len(repository.completed) == 1

    execution = repository.completed[0]

    assert execution["workflow_execution_id"] == (
        result["workflow_execution_id"]
    )
    assert execution["success"] is False


def test_execute_uses_one_correlation_id_for_record_and_tasks():
    repository = FakeWorkflowExecutionRepository()
    automation = FakeAutomationService()

    service, _, _ = make_service(
        automation_service=automation,
        workflow_execution_repository=repository,
    )

    result = service.execute(1)

    workflow_execution_id = (
        result["workflow_execution_id"]
    )

    assert repository.created[0][
        "workflow_execution_id"
    ] == workflow_execution_id

    assert repository.completed[0][
        "workflow_execution_id"
    ] == workflow_execution_id

    assert {
        call["workflow_execution_id"]
        for call in automation.calls
    } == {
        workflow_execution_id
    }


def test_execute_runs_tasks_in_dependency_order():
    repository = FakeWorkflowExecutionRepository()

    service, workflow_service, automation = make_service(
        workflow_execution_repository=repository,
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

    assert [
        call["current_task_id"]
        for call in repository.current_tasks
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

    assert [
        {
            key: value
            for key, value in call.items()
            if key != "workflow_execution_id"
        }
        for call in automation.calls
    ] == [
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

    workflow_execution_ids = {
        call["workflow_execution_id"]
        for call in automation.calls
    }

    assert len(workflow_execution_ids) == 1

    assert (
        next(iter(workflow_execution_ids))
        == result["workflow_execution_id"]
    )


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


def test_execute_marks_workflow_failed_when_execution_order_fails():
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

    repository = FakeWorkflowExecutionRepository()

    service, _, automation = make_service(
        workflow_service=workflow_service,
        workflow_execution_repository=repository,
    )

    with pytest.raises(
        ValueError,
        match="Workflow dependency cycle detected",
    ):
        service.execute(1)

    assert automation.calls == []
    assert len(repository.created) == 1
    assert len(repository.completed) == 1

    created = repository.created[0]
    completed = repository.completed[0]

    assert completed["workflow_execution_id"] == (
        created["workflow_execution_id"]
    )
    assert completed["success"] is False
    assert completed["completed_at"] is not None


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


def test_failed_task_skips_direct_and_transitive_dependents():
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
            {
                "id": 4,
                "workflow_id": 1,
                "task_id": "task_d",
                "position": 4,
            },
        ],
        dependencies=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_c",
                "depends_on_task_id": "task_b",
            },
        ],
    )

    automation = FakeAutomationService(
        outcomes={
            "task_a": {
                "task_id": "task_a",
                "success": False,
                "result": {
                    "success": False,
                    "error": "Task failed",
                },
            },
        }
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
        automation_service=automation,
    )

    result = service.execute(1)

    assert result["success"] is False
    assert result["failed_tasks"] == ["task_a"]
    assert result["skipped_tasks"] == [
        "task_b",
        "task_c",
    ]

    assert result["executed_tasks"] == [
        "task_a",
        "task_d",
    ]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == [
        "task_a",
        "task_d",
    ]


def test_failed_task_does_not_block_independent_branch():
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
            {
                "id": 4,
                "workflow_id": 1,
                "task_id": "task_d",
                "position": 4,
            },
        ],
        dependencies=[
            {
                "id": 1,
                "workflow_id": 1,
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
            {
                "id": 2,
                "workflow_id": 1,
                "task_id": "task_d",
                "depends_on_task_id": "task_c",
            },
        ],
    )

    automation = FakeAutomationService(
        outcomes={
            "task_a": {
                "task_id": "task_a",
                "success": False,
            },
        }
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
        automation_service=automation,
    )

    result = service.execute(1)

    assert result["success"] is False
    assert result["failed_tasks"] == ["task_a"]
    assert result["skipped_tasks"] == ["task_b"]

    assert result["executed_tasks"] == [
        "task_a",
        "task_c",
        "task_d",
    ]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == [
        "task_a",
        "task_c",
        "task_d",
    ]


def test_task_exception_fails_task_and_skips_dependents():
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
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
        ],
    )

    automation = FakeAutomationService(
        exceptions={
            "task_a": RuntimeError(
                "execution failed"
            ),
        }
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
        automation_service=automation,
    )

    result = service.execute(1)

    assert result["success"] is False
    assert result["failed_tasks"] == ["task_a"]
    assert result["skipped_tasks"] == ["task_b"]
    assert result["executed_tasks"] == ["task_a"]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == ["task_a"]

    assert result["executions"][0]["success"] is False
    assert result["executions"][0]["error"] == (
        "execution failed"
    )


def test_successful_task_allows_dependents_to_execute():
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
                "task_id": "task_b",
                "depends_on_task_id": "task_a",
            },
        ],
    )

    service, _, automation = make_service(
        workflow_service=workflow_service,
    )

    result = service.execute(1)

    assert result["success"] is True
    assert result["failed_tasks"] == []
    assert result["skipped_tasks"] == []
    assert result["executed_tasks"] == [
        "task_a",
        "task_b",
    ]

    assert [
        call["task_id"]
        for call in automation.calls
    ] == [
        "task_a",
        "task_b",
    ]


def test_workflow_execution_uses_one_correlation_id_for_all_tasks():
    service, _, automation = make_service()

    result = service.execute(1)

    assert result["success"] is True
    assert result["workflow_execution_id"]

    workflow_execution_ids = [
        call["workflow_execution_id"]
        for call in automation.calls
    ]

    assert len(workflow_execution_ids) == 3
    assert len(set(workflow_execution_ids)) == 1

    assert workflow_execution_ids[0] == (
        result["workflow_execution_id"]
    )
