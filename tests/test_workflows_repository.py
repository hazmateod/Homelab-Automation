import sqlite3

import pytest

from himp.database.workflows import WorkflowRepository


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


def make_repository():
    repository = object.__new__(WorkflowRepository)
    repository.database = TemporaryDatabase()
    repository._ensure_tables()
    return repository


def test_create_returns_workflow():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
        description="Refresh infrastructure inventory and reports.",
        enabled=True,
    )

    assert workflow is not None
    assert workflow["id"] > 0
    assert workflow["name"] == "Infrastructure Refresh"
    assert (
        workflow["description"]
        == "Refresh infrastructure inventory and reports."
    )
    assert workflow["enabled"] == 1
    assert workflow["created_at"] is not None
    assert workflow["updated_at"] is not None


def test_get_returns_saved_workflow():
    repository = make_repository()

    created = repository.create(
        name="Infrastructure Refresh",
    )

    workflow = repository.get(created["id"])

    assert workflow == created


def test_get_missing_workflow_returns_none():
    repository = make_repository()

    assert repository.get(9999) is None


def test_get_by_name_returns_saved_workflow():
    repository = make_repository()

    created = repository.create(
        name="Infrastructure Refresh",
    )

    workflow = repository.get_by_name(
        "Infrastructure Refresh"
    )

    assert workflow["id"] == created["id"]


def test_list_returns_workflows_in_id_order():
    repository = make_repository()

    first = repository.create(
        name="First Workflow",
    )

    second = repository.create(
        name="Second Workflow",
    )

    workflows = repository.list()

    assert [item["id"] for item in workflows] == [
        first["id"],
        second["id"],
    ]


def test_update_changes_workflow():
    repository = make_repository()

    created = repository.create(
        name="Infrastructure Refresh",
        description="Original",
        enabled=True,
    )

    updated = repository.update(
        workflow_id=created["id"],
        name="Nightly Infrastructure Refresh",
        description="Updated",
        enabled=False,
    )

    assert updated["id"] == created["id"]
    assert updated["name"] == "Nightly Infrastructure Refresh"
    assert updated["description"] == "Updated"
    assert updated["enabled"] == 0


def test_delete_removes_workflow():
    repository = make_repository()

    created = repository.create(
        name="Infrastructure Refresh",
    )

    repository.delete(created["id"])

    assert repository.get(created["id"]) is None


def test_duplicate_workflow_name_is_rejected():
    repository = make_repository()

    repository.create(
        name="Infrastructure Refresh",
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.create(
            name="Infrastructure Refresh",
        )


def test_add_task_returns_task():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    task = repository.add_task(
        workflow_id=workflow["id"],
        task_id="inventory_refresh",
        position=1,
    )

    assert task is not None
    assert task["workflow_id"] == workflow["id"]
    assert task["task_id"] == "inventory_refresh"
    assert task["position"] == 1


def test_get_task_returns_saved_task():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    task = repository.get_task(
        workflow["id"],
        "inventory_refresh",
    )

    assert task is not None
    assert task["task_id"] == "inventory_refresh"


def test_get_missing_task_returns_none():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    assert repository.get_task(
        workflow["id"],
        "inventory_refresh",
    ) is None


def test_list_tasks_returns_position_order():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "health_check",
        3,
    )

    tasks = repository.list_tasks(
        workflow["id"]
    )

    assert [
        task["task_id"]
        for task in tasks
    ] == [
        "inventory_refresh",
        "generate_reports",
        "health_check",
    ]


def test_duplicate_task_in_workflow_is_rejected():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.add_task(
            workflow["id"],
            "inventory_refresh",
            2,
        )


def test_same_task_can_exist_in_different_workflows():
    repository = make_repository()

    first = repository.create(
        name="First Workflow",
    )

    second = repository.create(
        name="Second Workflow",
    )

    first_task = repository.add_task(
        first["id"],
        "inventory_refresh",
        1,
    )

    second_task = repository.add_task(
        second["id"],
        "inventory_refresh",
        1,
    )

    assert first_task["task_id"] == "inventory_refresh"
    assert second_task["task_id"] == "inventory_refresh"
    assert first_task["workflow_id"] != second_task["workflow_id"]


def test_remove_task_removes_task():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.remove_task(
        workflow["id"],
        "inventory_refresh",
    )

    assert repository.get_task(
        workflow["id"],
        "inventory_refresh",
    ) is None


def test_add_dependency_returns_dependency():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    dependency = repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    assert dependency is not None
    assert dependency["workflow_id"] == workflow["id"]
    assert dependency["task_id"] == "generate_reports"
    assert (
        dependency["depends_on_task_id"]
        == "inventory_refresh"
    )


def test_list_dependencies_returns_workflow_dependencies():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    repository.add_task(
        workflow["id"],
        "health_check",
        3,
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "health_check",
        "inventory_refresh",
    )

    dependencies = repository.list_dependencies(
        workflow["id"]
    )

    assert [
        (
            dependency["task_id"],
            dependency["depends_on_task_id"],
        )
        for dependency in dependencies
    ] == [
        (
            "generate_reports",
            "inventory_refresh",
        ),
        (
            "health_check",
            "inventory_refresh",
        ),
    ]


def test_list_task_dependencies_returns_only_requested_task():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "health_check",
        "inventory_refresh",
    )

    dependencies = repository.list_task_dependencies(
        workflow["id"],
        "generate_reports",
    )

    assert len(dependencies) == 1
    assert dependencies[0]["task_id"] == "generate_reports"


def test_duplicate_dependency_is_rejected():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    with pytest.raises(sqlite3.IntegrityError):
        repository.add_dependency(
            workflow["id"],
            "generate_reports",
            "inventory_refresh",
        )


def test_remove_dependency_removes_only_requested_dependency():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.add_dependency(
        workflow["id"],
        "health_check",
        "inventory_refresh",
    )

    repository.remove_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    dependencies = repository.list_dependencies(
        workflow["id"]
    )

    assert len(dependencies) == 1
    assert dependencies[0]["task_id"] == "health_check"


def test_remove_task_cleans_dependencies_for_removed_task():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.remove_task(
        workflow["id"],
        "inventory_refresh",
    )

    assert repository.list_dependencies(
        workflow["id"]
    ) == []


def test_remove_task_cleans_dependencies_where_task_is_dependent():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.remove_task(
        workflow["id"],
        "generate_reports",
    )

    assert repository.list_dependencies(
        workflow["id"]
    ) == []


def test_delete_workflow_cascades_tasks_and_dependencies():
    repository = make_repository()

    workflow = repository.create(
        name="Infrastructure Refresh",
    )

    repository.add_task(
        workflow["id"],
        "inventory_refresh",
        1,
    )

    repository.add_task(
        workflow["id"],
        "generate_reports",
        2,
    )

    repository.add_dependency(
        workflow["id"],
        "generate_reports",
        "inventory_refresh",
    )

    repository.delete(
        workflow["id"]
    )

    assert repository.get(
        workflow["id"]
    ) is None

    assert repository.list_tasks(
        workflow["id"]
    ) == []

    assert repository.list_dependencies(
        workflow["id"]
    ) == []
