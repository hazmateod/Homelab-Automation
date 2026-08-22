from datetime import datetime

from himp.models.notification import NotificationEvent
from himp.services.notifications import (
    NotificationRoutingPolicy,
    NotificationService,
)


class FakeRepository:
    def __init__(self):
        self.records = []
        self.active = {}
        self.recovered = []
        self.acknowledged = []

    def active_for_deduplication(
        self,
        key,
    ):
        return self.active.get(key)

    def recover_correlation(
        self,
        correlation_key,
        recovered_at=None,
    ):
        self.recovered.append(
            (
                correlation_key,
                recovered_at,
            )
        )

    def create(
        self,
        event,
        *,
        lifecycle_status,
        routing_decision,
        logical_destinations,
        suppression_reason=None,
    ):
        record = {
            "id": len(self.records) + 1,
            "event_type": event.event_type,
            "source_type": event.source_type,
            "source_id": event.source_id,
            "severity": event.severity,
            "deduplication_key": (
                event.deduplication_key
            ),
            "correlation_key": (
                event.correlation_key
            ),
            "lifecycle_status": lifecycle_status,
            "routing_decision": routing_decision,
            "logical_destinations": list(
                logical_destinations
            ),
            "suppression_reason": (
                suppression_reason
            ),
            "metadata": event.metadata,
        }

        self.records.append(record)

        if lifecycle_status in {
            "PENDING",
            "ACKNOWLEDGED",
        }:
            self.active[
                event.deduplication_key
            ] = record

        return record

    def acknowledge(
        self,
        notification_id,
        acknowledged_by,
    ):
        self.acknowledged.append(
            (
                notification_id,
                acknowledged_by,
            )
        )

        return {
            "id": notification_id,
            "lifecycle_status": (
                "ACKNOWLEDGED"
            ),
            "acknowledged_by": acknowledged_by,
        }


def make_event(
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
        ),
        metadata={},
    )


def test_warning_routes_to_default_destination():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.publish(
        make_event()
    )

    assert result["lifecycle_status"] == "PENDING"
    assert result["routing_decision"] == "ROUTE"
    assert result["logical_destinations"] == [
        "DEFAULT",
    ]


def test_duplicate_active_notification_is_suppressed():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    first = service.publish(
        make_event()
    )

    repository.active[
        first["deduplication_key"]
    ] = first

    duplicate = service.publish(
        make_event()
    )

    assert (
        duplicate["lifecycle_status"]
        == "SUPPRESSED"
    )
    assert (
        duplicate["routing_decision"]
        == "SUPPRESS"
    )
    assert duplicate["logical_destinations"] == []
    assert (
        duplicate["suppression_reason"]
        == "duplicate active notification"
    )


def test_recovery_closes_open_correlation_and_routes():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.publish(
        make_event(
            event_type="STORAGE_RECOVERED",
            severity="RECOVERY",
        )
    )

    assert repository.recovered == [
        (
            "storage:host01:/",
            datetime(
                2026,
                8,
                22,
                16,
                0,
            ),
        )
    ]

    assert result["lifecycle_status"] == "RECOVERED"
    assert result["routing_decision"] == "ROUTE"


def test_storage_transition_maps_warning_event():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.storage_transition(
        {
            "hostname": "host01",
            "filesystem": "/dev/sda1",
            "mount_point": "/",
            "used_percent": 82.0,
            "previous_status": "PASS",
            "current_status": "WARNING",
        },
        occurred_at=datetime(
            2026,
            8,
            22,
            16,
            5,
        ),
    )

    assert (
        result["event_type"]
        == "STORAGE_WARNING"
    )
    assert result["severity"] == "WARNING"
    assert (
        result["source_type"]
        == "storage_filesystem"
    )
    assert result["source_id"] == "host01:/"
    assert result["metadata"]["used_percent"] == 82.0


def test_storage_transition_maps_critical_event():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.storage_transition(
        {
            "hostname": "host01",
            "filesystem": "/dev/sda1",
            "mount_point": "/",
            "used_percent": 93.0,
            "previous_status": "WARNING",
            "current_status": "CRITICAL",
        }
    )

    assert (
        result["event_type"]
        == "STORAGE_CRITICAL"
    )
    assert result["severity"] == "CRITICAL"


def test_storage_transition_maps_recovery_event():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.storage_transition(
        {
            "hostname": "host01",
            "filesystem": "/dev/sda1",
            "mount_point": "/",
            "used_percent": 60.0,
            "previous_status": "CRITICAL",
            "current_status": "PASS",
        }
    )

    assert (
        result["event_type"]
        == "STORAGE_RECOVERED"
    )
    assert result["severity"] == "RECOVERY"
    assert (
        result["lifecycle_status"]
        == "RECOVERED"
    )


def test_routing_policy_suppresses_info():
    policy = NotificationRoutingPolicy()

    result = policy.route(
        make_event(
            event_type="STORAGE_WARNING",
            severity="INFO",
        )
    )

    assert result == {
        "decision": "SUPPRESS",
        "logical_destinations": [],
        "reason": "severity is not routable",
    }


def test_acknowledge_delegates_to_repository():
    repository = FakeRepository()

    service = NotificationService(
        repository=repository
    )

    result = service.acknowledge(
        42,
        "operator",
    )

    assert repository.acknowledged == [
        (
            42,
            "operator",
        )
    ]
    assert (
        result["lifecycle_status"]
        == "ACKNOWLEDGED"
    )
