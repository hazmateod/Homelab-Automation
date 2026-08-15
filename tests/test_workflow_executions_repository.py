import sqlite3

from himp.database.workflow_executions import (
    WorkflowExecutionRepository,
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


def make_repository():
    repository = object.__new__(
        WorkflowExecutionRepository
    )
    repository.database = TemporaryDatabase()
    repository._ensure_table()
    return repository


def test_create_returns_workflow_execution():
    repository = make_repository()

    execution = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
        started_at="2026-08-14T20:00:00+00:00",
    )

    assert execution is not None
    assert execution["id"] > 0
    assert execution["workflow_id"] == 1
    assert execution["workflow_execution_id"] == (
        "workflow-run-001"
    )
    assert execution["started_at"] == (
        "2026-08-14T20:00:00+00:00"
    )
    assert execution["completed_at"] is None
    assert execution["success"] is None


def test_find_returns_saved_workflow_execution():
    repository = make_repository()

    created = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
        started_at="2026-08-14T20:00:00+00:00",
    )

    execution = repository.find(
        "workflow-run-001"
    )

    assert execution == created


def test_find_missing_workflow_execution_returns_none():
    repository = make_repository()

    assert repository.find(
        "missing-run"
    ) is None


def test_history_returns_newest_first():
    repository = make_repository()

    first = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
        started_at="2026-08-14T20:00:00+00:00",
    )

    second = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-002",
        started_at="2026-08-14T21:00:00+00:00",
    )

    history = repository.history()

    assert [
        item["id"]
        for item in history
    ] == [
        second["id"],
        first["id"],
    ]


def test_history_can_filter_by_workflow_id():
    repository = make_repository()

    first = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
    )

    repository.create(
        workflow_id=2,
        workflow_execution_id="workflow-run-002",
    )

    history = repository.history(
        workflow_id=1
    )

    assert len(history) == 1
    assert history[0]["id"] == first["id"]
    assert history[0]["workflow_id"] == 1


def test_history_respects_limit():
    repository = make_repository()

    for index in range(3):
        repository.create(
            workflow_id=1,
            workflow_execution_id=(
                f"workflow-run-{index + 1:03d}"
            ),
        )

    history = repository.history(
        limit=2
    )

    assert len(history) == 2


def test_workflow_history_returns_only_requested_workflow():
    repository = make_repository()

    first = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
    )

    second = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-002",
    )

    repository.create(
        workflow_id=2,
        workflow_execution_id="workflow-run-003",
    )

    history = repository.workflow_history(
        1
    )

    assert [
        item["id"]
        for item in history
    ] == [
        second["id"],
        first["id"],
    ]


def test_complete_marks_successful_workflow_execution():
    repository = make_repository()

    created = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
    )

    completed = repository.complete(
        workflow_execution_id="workflow-run-001",
        success=True,
        completed_at="2026-08-14T20:05:00+00:00",
    )

    assert completed["id"] == created["id"]
    assert completed["success"] is True
    assert completed["completed_at"] == (
        "2026-08-14T20:05:00+00:00"
    )


def test_complete_marks_failed_workflow_execution():
    repository = make_repository()

    repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
    )

    completed = repository.complete(
        workflow_execution_id="workflow-run-001",
        success=False,
        completed_at="2026-08-14T20:05:00+00:00",
    )

    assert completed["success"] is False
    assert completed["completed_at"] == (
        "2026-08-14T20:05:00+00:00"
    )


def test_complete_missing_workflow_execution_returns_none():
    repository = make_repository()

    completed = repository.complete(
        workflow_execution_id="missing-run",
        success=True,
    )

    assert completed is None


def test_duplicate_workflow_execution_id_is_rejected():
    repository = make_repository()

    repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-001",
    )

    try:
        repository.create(
            workflow_id=1,
            workflow_execution_id="workflow-run-001",
        )
    except sqlite3.IntegrityError:
        return

    raise AssertionError(
        "Duplicate workflow execution ID was accepted"
    )


def test_existing_workflow_execution_table_is_usable():
    database = TemporaryDatabase()

    database.execute(
        """
        CREATE TABLE workflow_executions
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id INTEGER NOT NULL,
            workflow_execution_id TEXT NOT NULL UNIQUE,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            success INTEGER
        )
        """
    )

    repository = object.__new__(
        WorkflowExecutionRepository
    )
    repository.database = database

    repository._ensure_table()

    execution = repository.create(
        workflow_id=1,
        workflow_execution_id="workflow-run-existing",
    )

    assert execution["workflow_id"] == 1
    assert execution["workflow_execution_id"] == (
        "workflow-run-existing"
    )
