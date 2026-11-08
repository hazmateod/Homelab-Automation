"""Phase 17.1 durable automation progress tests."""

import pytest

from himp.database.automation_progress import (
    AutomationProgressRepository,
)
from himp.database.config import DatabaseConfig
from himp.database.factory import create_database


@pytest.fixture
def repository(tmp_path):
    database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "progress.db",
        )
    )
    return AutomationProgressRepository(database=database)


def test_start_creates_pending_hosts(repository):
    run_id = repository.start(
        "maintenance",
        hosts=["host1", "host2"],
    )

    result = repository.get(run_id)

    assert result["task_id"] == "maintenance"
    assert result["attempt"] == 1
    assert result["status"] == "running"
    assert result["host_results"]["host1"]["status"] == "pending"
    assert result["host_results"]["host2"]["status"] == "pending"


def test_update_persists_host_progress(repository):
    run_id = repository.start(
        "maintenance",
        hosts=["host1"],
    )

    result = repository.update(
        run_id,
        host_results={
            "host1": {
                "host": "host1",
                "status": "succeeded",
            }
        },
        execution_token=repository.get(run_id)["execution_token"],
    )

    assert result["status"] == "running"
    assert result["host_results"]["host1"]["status"] == "succeeded"
    assert result["updated_at"] is not None


def test_finalize_prevents_further_updates(repository):
    run_id = repository.start("maintenance")

    result = repository.update(
        run_id,
        status="succeeded",
        completed_execution_id=123,
        execution_token=repository.get(run_id)["execution_token"],
    )

    assert result["status"] == "succeeded"
    assert result["finished_at"] is not None
    assert result["completed_execution_id"] == 123

    with pytest.raises(
        ValueError,
        match="already finalized",
    ):
        repository.update(
            run_id,
            status="failed",
            execution_token=repository.get(run_id)["execution_token"],
        )


def test_progress_survives_database_reopen(
    repository,
    tmp_path,
):
    run_id = repository.start(
        "maintenance",
        hosts=["host1"],
    )

    repository.update(
        run_id,
        host_results={
            "host1": {
                "host": "host1",
                "status": "failed",
            }
        },
        execution_token=repository.get(run_id)["execution_token"],
    )

    reopened_database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "progress.db",
        )
    )

    reopened = AutomationProgressRepository(
        database=reopened_database
    )

    result = reopened.get(run_id)

    assert result is not None
    assert result["host_results"]["host1"]["status"] == "failed"


def test_concurrent_update_rejects_stale_revision(
    repository,
    monkeypatch,
):
    run_id = repository.start(
        "maintenance",
        hosts=["host1"],
    )

    original_get = repository.get
    stale_record = original_get(run_id)

    # Simulate another writer completing an update.
    repository.update(
        run_id,
        host_results={
            "host1": {
                "host": "host1",
                "status": "succeeded",
            }
        },
        execution_token=repository.get(run_id)["execution_token"],
    )

    assert original_get(run_id)["revision"] == 1

    # Force the next writer to use the previously read revision.
    monkeypatch.setattr(
        repository,
        "get",
        lambda requested_id: (
            stale_record
            if requested_id == run_id
            else original_get(requested_id)
        ),
    )

    with pytest.raises(
        ValueError,
        match="Concurrent execution progress update rejected",
    ):
        repository.update(
            run_id,
            host_results={
                "host1": {
                    "host": "host1",
                    "status": "failed",
                }
            },
            execution_token=repository.get(run_id)["execution_token"],
        )

    # Read directly to avoid the patched getter.
    persisted = original_get(run_id)

    assert persisted["revision"] == 1
    assert (
        persisted["host_results"]["host1"]["status"]
        == "succeeded"
    )


def test_latest_running_returns_current_execution(repository):
    first = repository.start("maintenance")
    second = repository.start("maintenance")

    assert repository.latest_running("maintenance") is not None

    repository.interrupt(first, execution_token=repository.get(first)["execution_token"])

    current = repository.latest_running("maintenance")
    assert current["run_id"] == second


def test_interrupt_finalizes_unfinished_execution(repository):
    run_id = repository.start(
        "maintenance",
        hosts=["host1"],
    )

    result = repository.interrupt(run_id, execution_token=repository.get(run_id)["execution_token"])

    assert result["status"] == "interrupted"
    assert result["finished_at"] is not None
    assert result["revision"] == 1
    assert repository.latest_running("maintenance") is None

    with pytest.raises(ValueError):
        repository.interrupt(run_id, execution_token=repository.get(run_id)["execution_token"])


def test_interrupted_old_run_does_not_replace_new_run(
    repository,
):
    old_run = repository.start(
        "scheduled_updates",
        attempt=1,
    )

    repository.interrupt(old_run, execution_token=repository.get(old_run)["execution_token"])

    new_run = repository.start(
        "scheduled_updates",
        attempt=1,
    )

    current = repository.latest_running(
        "scheduled_updates"
    )

    assert current is not None
    assert current["run_id"] == new_run

    old_record = repository.get(old_run)

    assert old_record["status"] == "interrupted"
    assert old_record["finished_at"] is not None
    assert current["status"] == "running"
