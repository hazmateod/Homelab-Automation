"""Phase 17.1 execution progress ownership security tests."""

from datetime import datetime, timezone

import pytest

from himp.database.automation_progress import (
    AutomationProgressRepository,
)
from himp.database.config import DatabaseConfig
from himp.database.factory import create_database
from himp.services.automation_progress import (
    AutomationProgressTracker,
)


@pytest.fixture
def repository(tmp_path):
    database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "ownership.db",
        )
    )
    return AutomationProgressRepository(database=database)


def test_wrong_token_cannot_update_progress(repository):
    run_id = repository.start(
        "synthetic-maintenance",
        execution_token="owner-token",
        hosts=["host1"],
    )

    before = repository.get(run_id)

    with pytest.raises(ValueError, match="ownership mismatch"):
        repository.update(
            run_id,
            execution_token="wrong-token",
            host_results={
                "host1": {
                    "host": "host1",
                    "status": "succeeded",
                }
            },
        )

    assert repository.get(run_id) == before


def test_wrong_token_cannot_interrupt_progress(repository):
    run_id = repository.start(
        "synthetic-maintenance",
        execution_token="owner-token",
    )

    before = repository.get(run_id)

    # The repository must reject unauthorized interruption.
    with pytest.raises(ValueError):
        repository.interrupt(
            run_id,
            execution_token="wrong-token",
        )

    assert repository.get(run_id) == before


def test_missing_token_is_rejected(repository):
    run_id = repository.start(
        "synthetic-maintenance",
        execution_token="owner-token",
    )

    with pytest.raises(TypeError):
        repository.update(run_id, status="succeeded")

    with pytest.raises(TypeError):
        repository.interrupt(run_id)

    assert repository.get(run_id)["status"] == "running"


def test_tracker_rejects_wrong_execution_owner(repository):
    run_id = repository.start(
        "synthetic-maintenance",
        execution_token="owner-token",
        hosts=["host1"],
    )

    tracker = AutomationProgressTracker(
        repository,
        run_id,
        "wrong-token",
    )

    before = repository.get(run_id)

    with pytest.raises(ValueError, match="ownership mismatch"):
        tracker.handle_event(
            {
                "event": "task_ok",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "host": "host1",
                "task": "Synthetic ownership test",
                "changed": False,
            }
        )

    assert repository.get(run_id) == before
