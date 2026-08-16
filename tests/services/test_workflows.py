import sqlite3

import pytest

from himp.database.workflows import WorkflowRepository
from himp.services.workflows import (
    WorkflowDependencyCycleError,
    WorkflowDependencyNotFoundError,
    WorkflowNotFoundError,
    WorkflowService,
    WorkflowTaskNotFoundError,
    WorkflowValidationError,
)


class TemporaryDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row

    def execute(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor

    def query(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        return cursor.fetchall()

    def execute_insert(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, parameters)
        self.connection.commit()
        return cursor.lastrowid


class FakeAutomationService:
    TASKS = {
        "inventory_refresh": {
            "id": "inventory_refresh",
            "name": "Inventory Refresh",
        },
        "generate_reports": {
            "id": "generate_reports",
            "name": "Generate Reports",
        },
        "health_check": {
            "id": "health_check",
            "name": "Health Check",
        },
        "scheduled_updates": {
            "id": "scheduled_updates",
            "name": "Scheduled Updates",
        },
    }

    def find_task(self, task_id):
        task = self.TASKS.get(task_id)

        if task is None:
            raise ValueError(
                f"Unknown automation task: {task_id}"
            )

        return task


def make_service():
    repository = object.__new__(WorkflowRepository)
    repository.database = TemporaryDatabase()
    repository._ensure_tables()

    return WorkflowService(
        repository=repository,
        automation_service=FakeAutomationService(),
    )


def create_workflow(service, name="Infrastructure Refresh"):
    return service.create_workflow(
        name=name,
        description="Test workflow",
        enabled=True,
    )


def add_standard_tasks(service, workflow_id):
    service.add_task(
        workflow_id,
        "inventory_refresh",
        1,
    )

    service.add_task(
        workflow_id,
        "generate_reports",
        2,
    )

    service.add_task(
        workflow_id,
        "health_check",
        3,
    )


def test_create_workflow_returns_saved_workflow():
    service = make_service()

    workflow = create_workflow(service)

    assert workflow["name"] == "Infrastructure Refresh"
    assert workflow["description"] == "Test workflow"
    assert workflow["enabled"] == 1


def test_create_workflow_rejects_empty_name():
    service = make_service()

    with pytest.raises(
        WorkflowValidationError,
        match="Workflow name is required",
    ):
        service.create_workflow("")


def test_create_workflow_rejects_duplicate_name():
    service = make_service()

    create_workflow(service)

    with pytest.raises(
        WorkflowValidationError,
        match="Workflow already exists",
    ):
        create_workflow(service)


def test_get_workflow_returns_saved_workflow():
    service = make_service()

    workflow = create_workflow(service)

    result = service.get_workflow(
        workflow["id"]
    )

    assert result["id"] == workflow["id"]


def test_get_missing_workflow_raises():
    service = make_service()

    with pytest.raises(
        WorkflowNotFoundError,
        match="Workflow does not exist",
    ):
        service.get_workflow(999)


def test_list_workflows_returns_workflows():
    service = make_service()

    create_workflow(
        service,
        "First Workflow",
    )

    create_workflow(
        service,
        "Second Workflow",
    )

    workflows = service.list_workflows()

    assert [
        workflow["name"]
        for workflow in workflows
    ] == [
        "First Workflow",
        "Second Workflow",
    ]


def test_update_workflow_updates_definition():
    service = make_service()

    workflow = create_workflow(service)

    updated = service.update_workflow(
        workflow["id"],
        "Updated Workflow",
        "Updated description",
        False,
    )

    assert updated["name"] == "Updated Workflow"
    assert updated["description"] == "Updated description"
    assert updated["enabled"] == 0


def test_update_workflow_rejects_duplicate_name():
    service = make_service()

    first = create_workflow(
        service,
        "First Workflow",
    )

    create_workflow(
        service,
        "Second Workflow",
    )

    with pytest.raises(
        WorkflowValidationError,
        match="Workflow already exists",
    ):
        service.update_workflow(
            first["id"],
            "Second Workflow",
        )


def test_update_missing_workflow_raises():
    service = make_service()

    with pytest.raises(
        WorkflowNotFoundError,
    ):
        service.update_workflow(
            999,
            "Missing",
        )


def test_delete_workflow_removes_definition():
    service = make_service()

    workflow = create_workflow(service)

    service.delete_workflow(
        workflow["id"]
    )

    with pytest.raises(
        WorkflowNotFoundError,
    ):
        service.get_workflow(
            workflow["id"]
        )


def test_delete_missing_workflow_raises():
    service = make_service()

    with pytest.raises(
        WorkflowNotFoundError,
    ):
        service.delete_workflow(999)


def test_add_task_requires_known_automation_task():
    service = make_service()

    workflow = create_workflow(service)

    with pytest.raises(
        ValueError,
        match="Unknown automation task",
    ):
        service.add_task(
            workflow["id"],
            "does_not_exist",
            1,
        )


def test_add_task_rejects_duplicate_membership():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    with pytest.raises(
        WorkflowValidationError,
        match="Task already exists",
    ):
        service.add_task(
            workflow["id"],
            "inventory_refresh",
            2,
        )


def test_add_task_requires_existing_workflow():
    service = make_service()

    with pytest.raises(
        WorkflowNotFoundError,
    ):
        service.add_task(
            999,
            "inventory_refresh",
            1,
        )


def test_add_task_and_remove_task():
    service = make_service()

    workflow = create_workflow(service)

    task = service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    assert task["task_id"] == "inventory_refresh"

    service.remove_task(
        workflow["id"],
        "inventory_refresh",
    )

    assert service.repository.list_tasks(
        workflow["id"]
    ) == []


def test_remove_missing_task_raises():
    service = make_service()

    workflow = create_workflow(service)

    with pytest.raises(
        WorkflowTaskNotFoundError,
        match="Workflow task does not exist",
    ):
        service.remove_task(
            workflow["id"],
            "inventory_refresh",
        )


def test_add_dependency_requires_tasks_in_workflow():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    with pytest.raises(
        WorkflowTaskNotFoundError,
        match="Workflow task does not exist",
    ):
        service.add_dependency(
            workflow["id"],
            "inventory_refresh",
            "generate_reports",
        )


def test_add_dependency_creates_workflow_local_relationship():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    dependency = service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    assert dependency["task_id"] == "generate_reports"
    assert (
        dependency["depends_on_task_id"]
        == "inventory_refresh"
    )


def test_add_dependency_rejects_self_dependency():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    with pytest.raises(
        WorkflowDependencyCycleError,
        match="would create a cycle",
    ):
        service.add_dependency(
            workflow["id"],
            "inventory_refresh",
            "inventory_refresh",
        )


def test_add_dependency_rejects_duplicate_dependency():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    with pytest.raises(
        WorkflowValidationError,
        match="dependency already exists",
    ):
        service.add_dependency(
            workflow["id"],
            "generate_reports",
            "inventory_refresh",
        )


def test_dependency_cycle_is_rejected():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    service.add_dependency(
        workflow["id"],
        "health_check",
        "generate_reports",
    )

    with pytest.raises(
        WorkflowDependencyCycleError,
        match="would create a cycle",
    ):
        service.add_dependency(
            workflow["id"],
            "inventory_refresh",
            "health_check",
        )


def test_long_dependency_chain_without_cycle_is_allowed():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    service.add_dependency(
        workflow["id"],
        "health_check",
        "generate_reports",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["task_count"] == 3
    assert result["dependency_count"] == 2


def test_remove_dependency_returns_removed_dependency():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    dependency = service.remove_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    assert (
        dependency["depends_on_task_id"]
        == "inventory_refresh"
    )

    assert service.repository.list_dependencies(
        workflow["id"]
    ) == []


def test_remove_missing_dependency_raises():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    with pytest.raises(
        WorkflowDependencyNotFoundError,
        match="dependency does not exist",
    ):
        service.remove_dependency(
            workflow["id"],
            "generate_reports",
            "inventory_refresh",
        )


def test_validate_workflow_accepts_valid_definition():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result == {
        "workflow_id": workflow["id"],
        "valid": True,
        "errors": [],
        "task_count": 3,
        "dependency_count": 1,
    }


def test_validate_workflow_reports_unknown_automation_task():
    service = make_service()

    workflow = create_workflow(service)

    service.repository.add_task(
        workflow["id"],
        "unknown_task",
        1,
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is False
    assert any(
        "Unknown automation task"
        in error
        for error in result["errors"]
    )


def test_validate_workflow_reports_dependency_missing_source():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    service.repository.add_dependency(
        workflow["id"],
        "unknown_source",
        "inventory_refresh",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is False
    assert any(
        "source task is not in workflow"
        in error
        for error in result["errors"]
    )


def test_validate_workflow_reports_dependency_missing_target():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    service.repository.add_dependency(
        workflow["id"],
        "inventory_refresh",
        "unknown_target",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is False
    assert any(
        "target task is not in workflow"
        in error
        for error in result["errors"]
    )


def test_validate_workflow_reports_self_dependency():
    service = make_service()

    workflow = create_workflow(service)

    service.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    service.repository.add_dependency(
        workflow["id"],
        "inventory_refresh",
        "inventory_refresh",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is False
    assert any(
        "self-dependency"
        in error
        for error in result["errors"]
    )


def test_validate_workflow_reports_cycle():
    service = make_service()

    workflow = create_workflow(service)

    add_standard_tasks(
        service,
        workflow["id"],
    )

    service.repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    service.repository.add_dependency(
        workflow["id"],
        "health_check",
        "generate_reports",
    )

    service.repository.add_dependency(
        workflow["id"],
        "inventory_refresh",
        "health_check",
    )

    result = service.validate_workflow(
        workflow["id"]
    )

    assert result["valid"] is False
    assert any(
        "would create a cycle"
        in error
        for error in result["errors"]
    )
