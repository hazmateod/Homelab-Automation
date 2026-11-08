"""Phase 17.1 automation lock ownership regression tests."""

from datetime import datetime, timedelta, timezone

from himp.database.automation_locks import (
    AutomationLockRepository,
)
from himp.database.config import DatabaseConfig
from himp.database.factory import create_database


def test_old_execution_cannot_release_new_lock(tmp_path, monkeypatch):
    database = create_database(
        DatabaseConfig(
            backend="sqlite",
            sqlite_path=tmp_path / "locks.db",
        )
    )

    # Keep the test isolated from production configuration.
    monkeypatch.setattr(
        "himp.database.automation_locks.create_database",
        lambda: database,
    )

    repository = AutomationLockRepository()

    old_token = "execution-original"

    assert repository.acquire(
        "scheduled_updates",
        lease_seconds=300,
        execution_token=old_token,
    )

    original = repository.get("scheduled_updates")
    assert original is not None

    # Simulate the original lease expiring.
    expired = (
        datetime.now(timezone.utc)
        - timedelta(seconds=10)
    ).replace(tzinfo=None)

    database.execute(
        """
        UPDATE automation_locks
        SET expires_at=?
        WHERE task_id=?
        """,
        (expired, "scheduled_updates"),
    )

    # A newer execution acquires the task.
    new_token = "execution-replacement"

    assert repository.acquire(
        "scheduled_updates",
        lease_seconds=300,
        execution_token=new_token,
    )

    newer = repository.get("scheduled_updates")
    assert newer is not None

    # The older execution must not remove the newer lock.
    assert repository.release(
        "scheduled_updates",
        execution_token=old_token,
    ) == 0

    current = repository.get("scheduled_updates")

    assert current is not None
    assert current["execution_token"] == new_token

    assert repository.release(
        "scheduled_updates",
        execution_token=new_token,
    ) == 1

    assert repository.get("scheduled_updates") is None
