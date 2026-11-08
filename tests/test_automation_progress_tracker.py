"""Phase 17.1 per-host automation progress tracking tests."""

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
def tracker(tmp_path):
    database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "tracker.db",
        )
    )

    repository = AutomationProgressRepository(
        database=database
    )

    run_id = repository.start(
        "synthetic-maintenance",
        hosts=["host1", "host2"],
    )

    return (
        AutomationProgressTracker(
            repository,
            run_id,
            repository.get(run_id)["execution_token"],
        ),
        repository,
        run_id,
    )


def event(event_type, **fields):
    return {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **fields,
    }


def recap(host, failed=0, unreachable=0):
    return event(
        "playbook_finished",
        hosts={
            host: {
                "ok": 2,
                "changed": 1,
                "failed": failed,
                "unreachable": unreachable,
                "skipped": 0,
            }
        },
    )


def test_task_event_marks_host_running(tracker):
    processor, repository, run_id = tracker

    processor.handle_event(
        event(
            "task_ok",
            host="host1",
            task="Synthetic task",
            changed=False,
        )
    )

    host = repository.get(run_id)["host_results"]["host1"]

    assert host["status"] == "running"
    assert host["last_task"] == "Synthetic task"
    assert host["last_event"] == "task_ok"


def test_successful_recap_marks_host_succeeded(tracker):
    processor, repository, run_id = tracker

    processor.handle_event(recap("host1"))

    host = repository.get(run_id)["host_results"]["host1"]

    assert host["status"] == "succeeded"
    assert host["ok"] == 2


def test_failed_recap_marks_host_failed(tracker):
    processor, repository, run_id = tracker

    processor.handle_event(recap("host1", failed=1))

    assert (
        repository.get(run_id)["host_results"]["host1"]["status"]
        == "failed"
    )


def test_unreachable_recap_marks_host_unreachable(tracker):
    processor, repository, run_id = tracker

    processor.handle_event(recap("host1", unreachable=1))

    assert (
        repository.get(run_id)["host_results"]["host1"]["status"]
        == "unreachable"
    )


def test_ignored_failure_does_not_fail_host(tracker):
    processor, repository, run_id = tracker

    processor.handle_event(
        event(
            "failed",
            host="host1",
            task="Ignored synthetic failure",
            changed=False,
            error="password=synthetic-secret",
        )
    )

    interim = repository.get(run_id)["host_results"]["host1"]

    assert interim["status"] == "running"
    assert interim["last_event"] == "failed"
    assert "synthetic-secret" not in str(interim)

    processor.handle_event(recap("host1", failed=0))

    final = repository.get(run_id)["host_results"]["host1"]

    assert final["status"] == "succeeded"


def test_interrupted_execution_rejects_updates(tracker):
    processor, repository, run_id = tracker

    repository.interrupt(run_id, execution_token=repository.get(run_id)["execution_token"])

    with pytest.raises(ValueError, match="already finalized"):
        processor.handle_event(
            event(
                "task_ok",
                host="host1",
                task="Late task",
                changed=False,
            )
        )


def test_unknown_run_rejected(tracker):
    processor, repository, run_id = tracker

    processor.run_id = "nonexistent-run"

    with pytest.raises(ValueError, match="Unknown"):
        processor.handle_event(
            event(
                "task_ok",
                host="host1",
                task="Synthetic task",
                changed=False,
            )
        )


def test_invalid_event_does_not_modify_progress(tracker):
    processor, repository, run_id = tracker

    before = repository.get(run_id)

    with pytest.raises(ValueError, match="Unexpected"):
        processor.handle_event(
            event(
                "task_ok",
                host="host1",
                task="Synthetic task",
                changed=False,
                password="synthetic-secret",
            )
        )

    after = repository.get(run_id)

    assert after["revision"] == before["revision"]
    assert after["host_results"] == before["host_results"]
