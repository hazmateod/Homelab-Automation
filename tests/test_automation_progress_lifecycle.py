"""Phase 17.1 maintenance progress lifecycle tests."""

import pytest

from himp.database.automation_progress import (
    AutomationProgressRepository,
)
from himp.database.config import DatabaseConfig
from himp.database.factory import create_database
from himp.services.automation_progress_lifecycle import (
    AutomationProgressLifecycle,
)


@pytest.fixture
def repository(tmp_path):
    database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "lifecycle.db",
        )
    )
    return AutomationProgressRepository(database=database)


def make_lifecycle(repository, token="owner-token", attempt=1):
    return AutomationProgressLifecycle(
        repository,
        task_id="scheduled_updates",
        attempt=attempt,
        execution_token=token,
    )


def test_successful_attempt_links_execution_history(repository):
    lifecycle = make_lifecycle(repository)

    run_id = lifecycle.start(
        ["host01", "host02"],
        ["excluded01"],
    )

    started = repository.get(run_id)

    assert started["status"] == "running"
    assert started["attempt"] == 1
    assert set(started["host_results"]) == {
        "host01",
        "host02",
    }

    finished = lifecycle.finalize(
        success=True,
        execution_id=123,
    )

    assert finished["status"] == "succeeded"
    assert finished["completed_execution_id"] == 123
    assert finished["finished_at"] is not None


def test_failed_attempt_is_finalized(repository):
    lifecycle = make_lifecycle(repository, attempt=2)

    run_id = lifecycle.start(["host01"])

    finished = lifecycle.finalize(
        success=False,
        execution_id=456,
    )

    assert finished["status"] == "failed"
    assert finished["attempt"] == 2
    assert finished["completed_execution_id"] == 456
    assert repository.latest_running("scheduled_updates") is None
    assert repository.get(run_id)["status"] == "failed"


def test_interruption_finalizes_attempt(repository):
    lifecycle = make_lifecycle(repository)

    run_id = lifecycle.start(["host01"])

    interrupted = lifecycle.interrupt()

    assert interrupted["status"] == "interrupted"
    assert interrupted["finished_at"] is not None
    assert repository.get(run_id)["status"] == "interrupted"

    with pytest.raises(ValueError):
        lifecycle.finalize(success=True)


def test_wrong_owner_cannot_finalize(repository):
    lifecycle = make_lifecycle(repository)
    run_id = lifecycle.start(["host01"])

    unauthorized = make_lifecycle(
        repository,
        token="wrong-token",
    )
    unauthorized.run_id = run_id

    with pytest.raises(ValueError, match="ownership mismatch"):
        unauthorized.finalize(success=True)

    assert repository.get(run_id)["status"] == "running"


def test_duplicate_start_is_rejected(repository):
    lifecycle = make_lifecycle(repository)
    lifecycle.start(["host01"])

    with pytest.raises(
        ValueError,
        match="already started",
    ):
        lifecycle.start(["host02"])


def test_events_require_started_attempt(repository):
    lifecycle = make_lifecycle(repository)

    with pytest.raises(
        ValueError,
        match="has not started",
    ):
        lifecycle.handle_event({})


def test_retry_attempts_have_independent_records(repository):
    first = make_lifecycle(repository, attempt=1)
    first_id = first.start(["host01"])
    first.finalize(success=False, execution_id=100)

    second = make_lifecycle(repository, attempt=2)
    second_id = second.start(["host01"])
    second.finalize(success=True, execution_id=101)

    assert first_id != second_id
    assert repository.get(first_id)["status"] == "failed"
    assert repository.get(second_id)["status"] == "succeeded"
    assert repository.get(first_id)["completed_execution_id"] == 100
    assert repository.get(second_id)["completed_execution_id"] == 101
