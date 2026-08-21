from datetime import datetime, timedelta

import pytest

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.remediation_schedules import (
    RemediationScheduleRepository,
)


def make_repository(tmp_path):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path
                / "remediation-schedules.db"
            ),
        )
    )

    return RemediationScheduleRepository(
        database=database
    )


def test_create_persists_scheduled_state(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    scheduled_for = (
        datetime.now()
        + timedelta(hours=1)
    )

    record = repository.create(
        approval_id=7,
        scheduled_for=scheduled_for,
        scheduled_by="admin",
    )

    assert record["id"] == 1
    assert record["approval_id"] == 7
    assert record["status"] == "SCHEDULED"
    assert record["scheduled_by"] == "admin"
    assert record["started_at"] is None
    assert record["completed_at"] is None
    assert record["audit_id"] is None
    assert record["error"] is None


def test_find_by_approval_returns_schedule(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    record = repository.create(
        approval_id=8,
        scheduled_for=(
            datetime.now()
            + timedelta(hours=1)
        ),
        scheduled_by="admin",
    )

    assert repository.find_by_approval(
        8
    )["id"] == record["id"]

    assert repository.find_by_approval(
        999
    ) is None


def test_due_returns_only_due_scheduled_records(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    due = repository.create(
        approval_id=1,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    repository.create(
        approval_id=2,
        scheduled_for=(
            now + timedelta(hours=1)
        ),
        scheduled_by="admin",
    )

    result = repository.due(
        now=now
    )

    assert [
        item["id"]
        for item in result
    ] == [
        due["id"],
    ]


def test_claim_is_atomic_and_only_happens_once(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    record = repository.create(
        approval_id=3,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    first = repository.claim(
        record["id"],
        now=now,
    )

    second = repository.claim(
        record["id"],
        now=now,
    )

    assert first["status"] == "RUNNING"
    assert first["started_at"] is not None
    assert second is None


def test_future_schedule_cannot_be_claimed(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    record = repository.create(
        approval_id=4,
        scheduled_for=(
            now + timedelta(hours=1)
        ),
        scheduled_by="admin",
    )

    assert repository.claim(
        record["id"],
        now=now,
    ) is None


def test_running_schedule_can_complete(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    record = repository.create(
        approval_id=5,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    repository.claim(
        record["id"],
        now=now,
    )

    completed = repository.complete(
        record["id"],
        audit_id=42,
    )

    assert completed["status"] == "COMPLETED"
    assert completed["audit_id"] == 42
    assert completed["completed_at"] is not None


def test_running_schedule_can_fail(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    record = repository.create(
        approval_id=6,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    repository.claim(
        record["id"],
        now=now,
    )

    failed = repository.fail(
        record["id"],
        error="execution failed",
        audit_id=43,
    )

    assert failed["status"] == "FAILED"
    assert failed["error"] == "execution failed"
    assert failed["audit_id"] == 43


def test_scheduled_record_can_be_cancelled(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    record = repository.create(
        approval_id=9,
        scheduled_for=(
            datetime.now()
            + timedelta(hours=1)
        ),
        scheduled_by="admin",
    )

    cancelled = repository.cancel(
        schedule_id=record["id"],
        cancelled_by="admin",
        cancellation_note="Maintenance deferred.",
    )

    assert cancelled["status"] == "CANCELLED"
    assert cancelled["cancelled_by"] == "admin"
    assert cancelled["cancellation_note"] == (
        "Maintenance deferred."
    )
    assert cancelled["cancelled_at"] is not None


def test_non_scheduled_record_cannot_be_cancelled(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    record = repository.create(
        approval_id=10,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    repository.claim(
        record["id"],
        now=now,
    )

    with pytest.raises(
        ValueError,
        match="only a scheduled remediation",
    ):
        repository.cancel(
            record["id"],
            cancelled_by="admin",
        )


def test_summary_counts_schedule_lifecycle(
    tmp_path,
):
    repository = make_repository(
        tmp_path
    )

    now = datetime.now()

    one = repository.create(
        approval_id=11,
        scheduled_for=(
            now + timedelta(hours=1)
        ),
        scheduled_by="admin",
    )

    two = repository.create(
        approval_id=12,
        scheduled_for=(
            now - timedelta(minutes=1)
        ),
        scheduled_by="admin",
    )

    three = repository.create(
        approval_id=13,
        scheduled_for=(
            now + timedelta(hours=2)
        ),
        scheduled_by="admin",
    )

    repository.claim(
        two["id"],
        now=now,
    )

    repository.complete(
        two["id"]
    )

    repository.cancel(
        three["id"],
        cancelled_by="admin",
    )

    summary = repository.summary()

    assert summary == {
        "total": 3,
        "scheduled": 1,
        "running": 0,
        "completed": 1,
        "failed": 0,
        "cancelled": 1,
    }

    assert repository.find(
        one["id"]
    )["status"] == "SCHEDULED"
