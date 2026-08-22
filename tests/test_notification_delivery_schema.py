from himp.database.postgresql_schema import (
    schema_statements,
)


def test_postgresql_schema_contains_notification_deliveries():
    schema = "\n".join(
        schema_statements()
    )

    assert (
        "CREATE TABLE IF NOT EXISTS notification_deliveries"
        in schema
    )

    for column in (
        "notification_id",
        "destination_type",
        "destination_name",
        "status",
        "status_code",
        "error",
        "attempted_at",
    ):
        assert column in schema
