import sqlite3

from himp.database.automation_executions import (
    AutomationExecutionRepository,
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

    def table_columns(self, table_name):
        cursor = self.connection.cursor()
        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )
        return [
            row["name"]
            for row in cursor.fetchall()
        ]

    def execute_insert(self, sql, parameters=()):
        cursor = self.connection.cursor()
        cursor.execute(
            sql,
            parameters,
        )
        self.connection.commit()
        return cursor.lastrowid


def make_repository():
    repository = object.__new__(
        AutomationExecutionRepository
    )
    repository.database = TemporaryDatabase()
    repository._ensure_table()
    return repository


def test_save_returns_execution_id():
    repository = make_repository()

    execution_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.25,
        result={
            "success": True,
            "message": "healthy",
        },
        executed_at="2026-08-11T20:00:00+00:00",
    )

    assert isinstance(execution_id, int)
    assert execution_id > 0


def test_find_returns_saved_execution():
    repository = make_repository()

    execution_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.25,
        result={
            "success": True,
            "message": "healthy",
        },
        executed_at="2026-08-11T20:00:00+00:00",
    )

    execution = repository.find(execution_id)

    assert execution is not None
    assert execution["id"] == execution_id
    assert execution["task_id"] == "health_check"
    assert execution["success"] is True
    assert execution["elapsed"] == 1.25
    assert execution["result"] == {
        "success": True,
        "message": "healthy",
    }
    assert (
        execution["executed_at"]
        == "2026-08-11T20:00:00+00:00"
    )


def test_find_missing_execution_returns_none():
    repository = make_repository()

    assert repository.find(9999) is None


def test_latest_returns_newest_execution_for_task():
    repository = make_repository()

    first_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"message": "first"},
    )

    second_id = repository.save(
        task_id="health_check",
        success=False,
        elapsed=2.0,
        result={"message": "second"},
    )

    latest = repository.latest("health_check")

    assert latest["id"] == second_id
    assert latest["id"] != first_id
    assert latest["success"] is False
    assert latest["result"] == {
        "message": "second",
    }


def test_latest_is_scoped_to_task():
    repository = make_repository()

    health_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"task": "health"},
    )

    report_id = repository.save(
        task_id="generate_reports",
        success=True,
        elapsed=2.0,
        result={"task": "reports"},
    )

    health_latest = repository.latest("health_check")
    report_latest = repository.latest("generate_reports")

    assert health_latest["id"] == health_id
    assert report_latest["id"] == report_id


def test_history_returns_newest_first():
    repository = make_repository()

    first_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"sequence": 1},
    )

    second_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=2.0,
        result={"sequence": 2},
    )

    third_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=3.0,
        result={"sequence": 3},
    )

    history = repository.history()

    assert [
        item["id"]
        for item in history
    ] == [
        third_id,
        second_id,
        first_id,
    ]


def test_history_task_filter():
    repository = make_repository()

    repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"task": "health"},
    )

    report_id = repository.save(
        task_id="generate_reports",
        success=True,
        elapsed=2.0,
        result={"task": "reports"},
    )

    history = repository.history(
        task_id="generate_reports"
    )

    assert len(history) == 1
    assert history[0]["id"] == report_id
    assert history[0]["task_id"] == "generate_reports"


def test_history_success_filter():
    repository = make_repository()

    success_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"success": True},
    )

    failure_id = repository.save(
        task_id="health_check",
        success=False,
        elapsed=2.0,
        result={"success": False},
    )

    successful = repository.history(
        success=True
    )

    failed = repository.history(
        success=False
    )

    assert [
        item["id"]
        for item in successful
    ] == [success_id]

    assert [
        item["id"]
        for item in failed
    ] == [failure_id]


def test_history_supports_task_and_success_filters():
    repository = make_repository()

    repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"status": "ok"},
    )

    matching_id = repository.save(
        task_id="health_check",
        success=False,
        elapsed=2.0,
        result={"status": "failed"},
    )

    repository.save(
        task_id="generate_reports",
        success=False,
        elapsed=3.0,
        result={"status": "failed"},
    )

    history = repository.history(
        task_id="health_check",
        success=False,
    )

    assert len(history) == 1
    assert history[0]["id"] == matching_id


def test_task_history_only_returns_requested_task():
    repository = make_repository()

    repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={"task": "health"},
    )

    report_id = repository.save(
        task_id="generate_reports",
        success=True,
        elapsed=2.0,
        result={"task": "reports"},
    )

    history = repository.task_history(
        "generate_reports"
    )

    assert len(history) == 1
    assert history[0]["id"] == report_id
    assert history[0]["task_id"] == "generate_reports"


def test_result_is_deserialized_from_json():
    repository = make_repository()

    execution_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={
            "nested": {
                "items": [1, 2, 3],
            },
        },
    )

    execution = repository.find(
        execution_id
    )

    assert execution["result"] == {
        "nested": {
            "items": [1, 2, 3],
        },
    }


def test_success_is_deserialized_as_boolean():
    repository = make_repository()

    success_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={},
    )

    failure_id = repository.save(
        task_id="health_check",
        success=False,
        elapsed=1.0,
        result={},
    )

    success = repository.find(
        success_id
    )

    failure = repository.find(
        failure_id
    )

    assert success["success"] is True
    assert failure["success"] is False


def test_save_persists_workflow_execution_id():
    repository = make_repository()

    execution_id = repository.save(
        task_id="inventory_refresh",
        workflow_execution_id="workflow-run-001",
        success=True,
        elapsed=1.25,
        result={
            "task": "inventory_refresh",
            "success": True,
        },
    )

    execution = repository.find(execution_id)

    assert execution["workflow_execution_id"] == (
        "workflow-run-001"
    )


def test_save_allows_execution_without_workflow_execution_id():
    repository = make_repository()

    execution_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=0.5,
        result={
            "task": "health_check",
            "success": True,
        },
    )

    execution = repository.find(execution_id)

    assert execution["workflow_execution_id"] is None


def test_history_can_filter_by_workflow_execution_id():
    repository = make_repository()

    repository.save(
        task_id="inventory_refresh",
        workflow_execution_id="workflow-run-001",
        success=True,
        elapsed=1.0,
        result={"success": True},
    )

    repository.save(
        task_id="generate_reports",
        workflow_execution_id="workflow-run-001",
        success=True,
        elapsed=2.0,
        result={"success": True},
    )

    repository.save(
        task_id="health_check",
        workflow_execution_id="workflow-run-002",
        success=True,
        elapsed=3.0,
        result={"success": True},
    )

    history = repository.history(
        workflow_execution_id="workflow-run-001",
    )

    assert len(history) == 2
    assert {
        execution["task_id"]
        for execution in history
    } == {
        "inventory_refresh",
        "generate_reports",
    }

    assert all(
        execution["workflow_execution_id"]
        == "workflow-run-001"
        for execution in history
    )


def test_workflow_history_returns_only_matching_execution():
    repository = make_repository()

    repository.save(
        task_id="inventory_refresh",
        workflow_execution_id="workflow-run-001",
        success=True,
        elapsed=1.0,
        result={"success": True},
    )

    repository.save(
        task_id="generate_reports",
        workflow_execution_id="workflow-run-001",
        success=False,
        elapsed=2.0,
        result={
            "success": False,
            "error": "report failure",
        },
    )

    repository.save(
        task_id="health_check",
        workflow_execution_id="workflow-run-002",
        success=True,
        elapsed=3.0,
        result={"success": True},
    )

    history = repository.workflow_history(
        "workflow-run-001",
    )

    assert len(history) == 2
    assert [
        execution["task_id"]
        for execution in history
    ] == [
        "generate_reports",
        "inventory_refresh",
    ]


def test_task_history_preserves_workflow_execution_id():
    repository = make_repository()

    repository.save(
        task_id="inventory_refresh",
        workflow_execution_id="workflow-run-001",
        success=True,
        elapsed=1.0,
        result={"success": True},
    )

    history = repository.task_history(
        "inventory_refresh",
    )

    assert len(history) == 1
    assert history[0]["workflow_execution_id"] == (
        "workflow-run-001"
    )


def test_existing_execution_table_is_upgraded_with_workflow_execution_id():
    database = TemporaryDatabase()

    database.execute(
        """
        CREATE TABLE automation_executions
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            success INTEGER NOT NULL,
            elapsed REAL NOT NULL,
            result TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    repository = object.__new__(
        AutomationExecutionRepository
    )
    repository.database = database

    repository._ensure_table()

    columns = {
        row[1]
        for row in database.query(
            "PRAGMA table_info(automation_executions)"
        )
    }

    assert "workflow_execution_id" in columns

    execution_id = repository.save(
        task_id="inventory_refresh",
        workflow_execution_id="workflow-run-migration",
        success=True,
        elapsed=1.0,
        result={
            "success": True,
        },
    )

    execution = repository.find(execution_id)

    assert execution["workflow_execution_id"] == (
        "workflow-run-migration"
    )



def test_save_persists_retry_provenance():
    repository = make_repository()

    execution_id = repository.save(
        task_id="health_check",
        success=True,
        elapsed=1.0,
        result={
            "success": True,
        },
        retry_of_execution_id=723,
        retry_source_workflow_execution_id=(
            "workflow-source-001"
        ),
    )

    execution = repository.find(
        execution_id
    )

    assert execution[
        "workflow_execution_id"
    ] is None

    assert execution[
        "retry_of_execution_id"
    ] == 723

    assert execution[
        "retry_source_workflow_execution_id"
    ] == "workflow-source-001"


def test_existing_execution_table_is_upgraded_with_retry_provenance():
    database = TemporaryDatabase()

    database.execute(
        """
        CREATE TABLE automation_executions
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            success INTEGER NOT NULL,
            elapsed REAL NOT NULL,
            result TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    repository = object.__new__(
        AutomationExecutionRepository
    )

    repository.database = database

    repository._ensure_table()

    columns = {
        row[1]
        for row in database.query(
            "PRAGMA table_info(automation_executions)"
        )
    }

    assert "workflow_execution_id" in columns
    assert "retry_of_execution_id" in columns
    assert (
        "retry_source_workflow_execution_id"
        in columns
    )
