from himp.database.postgresql_schema import (
    schema_statements,
)


def test_postgresql_schema_contains_notifications():
    schema = "\n".join(
        schema_statements()
    )

    assert (
        "CREATE TABLE IF NOT EXISTS notifications"
        in schema
    )

    for column in (
        "event_type",
        "source_type",
        "source_id",
        "severity",
        "deduplication_key",
        "correlation_key",
        "lifecycle_status",
        "routing_decision",
        "logical_destinations",
        "acknowledged_by",
        "recovered_at",
    ):
        assert column in schema


def test_notification_schema_exposes_lifecycle_contract():
    schema = "\n".join(
        schema_statements()
    )

    for status in (
        "PENDING",
        "SUPPRESSED",
        "ACKNOWLEDGED",
        "RECOVERED",
    ):
        assert status in schema
