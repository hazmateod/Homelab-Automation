"""
HIMP database configuration.

Centralizes persistence backend configuration while preserving SQLite
as the default production backend until the Phase 11 PostgreSQL
migration and cutover are explicitly completed.
"""

import os
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_DATABASE_BACKENDS = {
    "sqlite",
    "postgresql",
}


@dataclass(frozen=True)
class DatabaseConfig:
    """
    Runtime database configuration.

    SQLite remains the default backend so introducing this configuration
    layer cannot implicitly move an existing HIMP installation to
    PostgreSQL.
    """

    backend: str = "sqlite"
    sqlite_path: Path = Path("data/himp.db")
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_database: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_schema: str = "public"

    @classmethod
    def from_environment(cls):
        backend = (
            os.getenv(
                "HIMP_DATABASE_BACKEND",
                "sqlite",
            )
            .strip()
            .lower()
        )

        if backend not in SUPPORTED_DATABASE_BACKENDS:
            raise ValueError(
                "Unsupported HIMP database backend: "
                f"{backend}"
            )

        sqlite_path = Path(
            os.getenv(
                "HIMP_DATABASE_PATH",
                "data/himp.db",
            )
        )

        postgres_port_text = os.getenv(
            "HIMP_DATABASE_PORT",
            "5432",
        ).strip()

        try:
            postgres_port = int(
                postgres_port_text
            )
        except ValueError as exc:
            raise ValueError(
                "HIMP_DATABASE_PORT must be an integer."
            ) from exc

        if not 1 <= postgres_port <= 65535:
            raise ValueError(
                "HIMP_DATABASE_PORT must be between "
                "1 and 65535."
            )

        config = cls(
            backend=backend,
            sqlite_path=sqlite_path,
            postgres_host=_optional_environment(
                "HIMP_DATABASE_HOST"
            ),
            postgres_port=postgres_port,
            postgres_database=_optional_environment(
                "HIMP_DATABASE_NAME"
            ),
            postgres_user=_optional_environment(
                "HIMP_DATABASE_USER"
            ),
            postgres_password=_optional_environment(
                "HIMP_DATABASE_PASSWORD"
            ),
            postgres_schema=(
                _optional_environment(
                    "HIMP_DATABASE_SCHEMA"
                )
                or "public"
            ),
        )

        config.validate()

        return config

    @property
    def is_sqlite(self):
        return self.backend == "sqlite"

    @property
    def is_postgresql(self):
        return self.backend == "postgresql"

    def validate(self):
        if self.is_sqlite:
            return

        if not self.postgres_schema:
            raise ValueError(
                "HIMP_DATABASE_SCHEMA must not be empty."
            )

        required = {
            "HIMP_DATABASE_HOST": self.postgres_host,
            "HIMP_DATABASE_NAME": self.postgres_database,
            "HIMP_DATABASE_USER": self.postgres_user,
            "HIMP_DATABASE_PASSWORD": self.postgres_password,
        }

        missing = [
            name
            for name, value in required.items()
            if not value
        ]

        if missing:
            raise ValueError(
                "PostgreSQL database configuration "
                "is incomplete. Missing: "
                + ", ".join(missing)
            )


def _optional_environment(name):
    value = os.getenv(name)

    if value is None:
        return None

    value = value.strip()

    return value or None
