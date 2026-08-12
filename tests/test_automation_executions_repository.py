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
