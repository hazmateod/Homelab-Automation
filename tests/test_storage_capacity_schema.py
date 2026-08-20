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


def test_storage_repository_uses_wide_numeric_capacity_columns():
    from pathlib import Path

    source = Path(
        "himp/database/storage_capacity.py"
    ).read_text()

    assert "total_bytes BIGINT NOT NULL" in source
    assert "used_bytes BIGINT NOT NULL" in source
    assert "available_bytes BIGINT NOT NULL" in source

    assert (
        "used_percent DOUBLE PRECISION NOT NULL"
        in source
    )
