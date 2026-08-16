"""
SQLite to PostgreSQL migration command.
"""

import sys

from himp.database.factory import create_database
from himp.database.postgresql import PostgreSQLDatabase
from himp.database.migration import (
    MigrationError,
    SQLitePostgreSQLMigrator,
)
from himp.lib.output import error, info, success


SQLITE_SOURCE = "/opt/himp/data/himp.db"


def run(args):
    rehearsal = not getattr(
        args,
        "execute",
        False,
    )

    mode = (
        "REHEARSAL"
        if rehearsal
        else "EXECUTE"
    )

    info(
        "Starting SQLite to PostgreSQL "
        f"migration {mode}..."
    )

    database = None

    try:
        database = create_database()

        if not database.config.is_postgresql:
            error(
                "Migration target must use "
                "the PostgreSQL backend."
            )
            return 1

        migrator = SQLitePostgreSQLMigrator(
            SQLITE_SOURCE,
            database,
        )

        result = migrator.migrate(
            rehearsal=rehearsal,
        )

        print()
        print(
            "Migration mode     : "
            f"{mode}"
        )
        print(
            "Tables processed    : "
            f"{len(result.tables)}"
        )
        print(
            "Rows processed      : "
            f"{result.total_rows}"
        )

        if rehearsal:
            success(
                "Migration rehearsal completed "
                "successfully. PostgreSQL changes "
                "were rolled back."
            )
        else:
            success(
                "SQLite to PostgreSQL migration "
                "completed successfully."
            )

        return 0

    except MigrationError as exc:
        error(
            f"Migration failed: {exc}"
        )
        return 1

    except Exception as exc:
        error(
            f"Migration failed: {exc}"
        )
        return 1

    finally:
        if database is not None:
            close = getattr(
                database,
                "close",
                None,
            )

            if callable(close):
                close()

        PostgreSQLDatabase.close_pools()
