from datetime import datetime

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.notifications import NotificationRepository
from himp.models.notification import NotificationEvent


def make_repository(tmp_path):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path / "notifications.db"
            ),
        )
    )

    return (
        NotificationRepository(
            database=database
        ),
        database,
    )


def event(
    *,
    event_type="STORAGE_WARNING",
    severity="WARNING",
):
    return NotificationEvent(
        event_type=event_type,
        source_type="storage_filesystem",
        source_id="host01:/",
        severity=severity,
        title="Storage event",
        message="Storage event message",
        deduplication_key=(
            f"{event_type}:host01:/"
        ),
        correlation_key="storage:host01:/",
        occurred_at=datetime(
            2026,
            8,
            22,
            16,
            0,
            0,
        ),
        metadata={
            "hostname": "host01",
        },
    )


def test_repository_persists_notification(tmp_path):
    repository, database = make_repository(
        tmp_path
    )

    try:
        record = repository.create(
            event(),
            lifecycle_status="PENDING",
            routing_decision="ROUTE",
            logical_destinations=[
                "DEFAULT",
            ],
        )

        assert record["id"] > 0
        assert (
            record["event_type"]
            == "STORAGE_WARNING"
        )
        assert (
            record["lifecycle_status"]
            == "PENDING"
        )
        assert (
            record["routing_decision"]
            == "ROUTE"
        )
        assert (
            record["logical_destinations"]
            == ["DEFAULT"]
        )
        assert record["metadata"] == {
            "hostname": "host01",
        }

    finally:
        database.connection.close()


def test_repository_finds_active_deduplication_record(
    tmp_path,
):
    repository, database = make_repository(
        tmp_path
    )

    try:
        created = repository.create(
            event(),
            lifecycle_status="PENDING",
            routing_decision="ROUTE",
            logical_destinations=[
                "DEFAULT",
            ],
        )

        active = (
            repository
            .active_for_deduplication(
                created[
                    "deduplication_key"
                ]
            )
        )

        assert active["id"] == created["id"]

    finally:
        database.connection.close()


def test_repository_acknowledges_pending_notification(
    tmp_path,
):
    repository, database = make_repository(
        tmp_path
    )

    try:
        created = repository.create(
            event(),
            lifecycle_status="PENDING",
            routing_decision="ROUTE",
            logical_destinations=[
                "DEFAULT",
            ],
        )

        acknowledged = repository.acknowledge(
            created["id"],
            "automation-admin",
        )

        assert (
            acknowledged["lifecycle_status"]
            == "ACKNOWLEDGED"
        )
        assert (
            acknowledged["acknowledged_by"]
            == "automation-admin"
        )
        assert (
            acknowledged["acknowledged_at"]
            is not None
        )

    finally:
        database.connection.close()


def test_repository_recovers_open_correlation(
    tmp_path,
):
    repository, database = make_repository(
        tmp_path
    )

    try:
        created = repository.create(
            event(),
            lifecycle_status="PENDING",
            routing_decision="ROUTE",
            logical_destinations=[
                "DEFAULT",
            ],
        )

        repository.recover_correlation(
            created["correlation_key"]
        )

        recovered = repository.find(
            created["id"]
        )

        assert (
            recovered["lifecycle_status"]
            == "RECOVERED"
        )
        assert recovered["recovered_at"] is not None

    finally:
        database.connection.close()
