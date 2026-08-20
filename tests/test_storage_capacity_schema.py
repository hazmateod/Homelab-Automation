from himp.database.postgresql_schema import (
    schema_statements,
)


def test_postgresql_schema_contains_storage_capacity_tables():
    schema = "\n".join(
        schema_statements()
    )

    assert (
        "storage_capacity_history"
        in schema
    )

    assert (
        "storage_alert_events"
        in schema
    )
