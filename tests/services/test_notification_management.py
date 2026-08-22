from datetime import datetime

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.notification_deliveries import (
    NotificationDeliveryRepository,
)
from himp.database.notifications import (
    NotificationRepository,
)
from himp.models.notification import NotificationEvent
from himp.services.notifications import NotificationService


class DeliveryFacade:
    def __init__(
        self,
        repository,
    ):
        self.repository = repository

    def deliver(
        self,
        notification,
    ):
        return []


def make_service(tmp_path):
    database = Database(
        config=DatabaseConfig(
            backend="sqlite",
            sqlite_path=(
                tmp_path
                / "notification-management.db"
            ),
        )
    )

    notifications = NotificationRepository(
        database=database
    )

    deliveries = (
        NotificationDeliveryRepository(
            database=database
        )
    )

    service = NotificationService(
        repository=notifications,
        delivery=DeliveryFacade(
            deliveries
        ),
    )

    return service, deliveries, database


def make_event(
    *,
    severity,
    event_type,
    source_id,
):
    return NotificationEvent(
        event_type=event_type,
        source_type="storage_filesystem",
        source_id=source_id,
        severity=severity,
        title=event_type,
        message=f"{event_type} message",
        deduplication_key=(
            f"{event_type}:{source_id}"
        ),
        correlation_key=(
            f"storage:{source_id}"
        ),
        occurred_at=datetime(
            2026,
            8,
            22,
            19,
            0,
        ),
        metadata={},
    )


def test_history_includes_latest_delivery(tmp_path):
    service, deliveries, database = (
        make_service(tmp_path)
    )

    try:
        notification = service.publish(
            make_event(
                severity="CRITICAL",
                event_type="STORAGE_CRITICAL",
                source_id="pbs01:/backup",
            )
        )

        deliveries.record(
            notification_id=notification["id"],
            destination_type="DISCORD",
            destination_name="DEFAULT",
            status="FAILED",
            error="first failure",
        )

        deliveries.record(
            notification_id=notification["id"],
            destination_type="DISCORD",
            destination_name="DEFAULT",
            status="SUCCESS",
            status_code=204,
        )

        rows = service.history()

        assert len(rows) == 1
        assert (
            rows[0]["latest_delivery"]["status"]
            == "SUCCESS"
        )
        assert (
            rows[0]["latest_delivery"]["status_code"]
            == 204
        )

    finally:
        database.connection.close()


def test_history_filters_by_severity(tmp_path):
    service, _, database = (
        make_service(tmp_path)
    )

    try:
        service.publish(
            make_event(
                severity="WARNING",
                event_type="STORAGE_WARNING",
                source_id="host01:/",
            )
        )

        service.publish(
            make_event(
                severity="CRITICAL",
                event_type="STORAGE_CRITICAL",
                source_id="host02:/",
            )
        )

        rows = service.history(
            severity="CRITICAL"
        )

        assert len(rows) == 1
        assert rows[0]["severity"] == "CRITICAL"

    finally:
        database.connection.close()


def test_history_filters_by_lifecycle_status(
    tmp_path,
):
    service, _, database = (
        make_service(tmp_path)
    )

    try:
        notification = service.publish(
            make_event(
                severity="WARNING",
                event_type="STORAGE_WARNING",
                source_id="host01:/",
            )
        )

        service.acknowledge(
            notification["id"],
            "admin",
        )

        rows = service.history(
            lifecycle_status="ACKNOWLEDGED"
        )

        assert len(rows) == 1
        assert (
            rows[0]["lifecycle_status"]
            == "ACKNOWLEDGED"
        )
        assert (
            rows[0]["acknowledged_by"]
            == "admin"
        )

    finally:
        database.connection.close()


def test_summary_counts_visible_notification_state(
    tmp_path,
):
    service, deliveries, database = (
        make_service(tmp_path)
    )

    try:
        warning = service.publish(
            make_event(
                severity="WARNING",
                event_type="STORAGE_WARNING",
                source_id="host01:/",
            )
        )

        critical = service.publish(
            make_event(
                severity="CRITICAL",
                event_type="STORAGE_CRITICAL",
                source_id="host02:/",
            )
        )

        deliveries.record(
            notification_id=critical["id"],
            destination_type="DISCORD",
            destination_name="DEFAULT",
            status="FAILED",
            error="transport unavailable",
        )

        result = service.summary()

        assert result["count"] == 2
        assert result["pending"] == 2
        assert result["critical"] == 1
        assert result["delivery_failures"] == 1

    finally:
        database.connection.close()


def test_invalid_severity_filter_is_rejected(
    tmp_path,
):
    service, _, database = (
        make_service(tmp_path)
    )

    try:
        try:
            service.history(
                severity="INVALID"
            )
        except ValueError as error:
            assert (
                "invalid notification severity"
                in str(error)
            )
        else:
            raise AssertionError(
                "invalid severity was accepted"
            )

    finally:
        database.connection.close()
