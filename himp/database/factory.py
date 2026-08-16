"""
HIMP runtime database factory.

Selects the configured persistence backend while keeping backend-specific
connection implementations isolated from repositories and services.
"""

from himp.database.config import DatabaseConfig
from himp.database.database import Database
from himp.database.postgresql import PostgreSQLDatabase


def create_database(
    config=None,
):
    """
    Create the configured HIMP database backend.

    When no explicit configuration is supplied, runtime configuration is
    resolved from the HIMP_DATABASE_* environment variables.

    SQLite remains the default backend unless PostgreSQL is explicitly
    configured.
    """
    if config is None:
        config = DatabaseConfig.from_environment()

    if config.is_sqlite:
        return Database(
            config=config
        )

    if config.is_postgresql:
        return PostgreSQLDatabase(
            config=config
        )

    raise ValueError(
        "Unsupported HIMP database backend: "
        f"{config.backend}"
    )
