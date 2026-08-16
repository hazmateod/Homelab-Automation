"""
PostgreSQL database backend.

Phase 11 foundation for PostgreSQL connectivity. This backend intentionally
does not initialize HIMP schema yet; schema migration is handled by later
Phase 11 slices.
"""

from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from himp.database.config import DatabaseConfig


class PostgreSQLDatabase:

    def __init__(
        self,
        config=None,
    ):
        self.config = (
            config
            if config is not None
            else DatabaseConfig.from_environment()
        )

        if not self.config.is_postgresql:
            raise ValueError(
                "PostgreSQLDatabase requires "
                "backend=postgresql."
            )

        self.connection = psycopg.connect(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            dbname=self.config.postgres_database,
            user=self.config.postgres_user,
            password=self.config.postgres_password,
            row_factory=dict_row,
            autocommit=True,
        )

    @staticmethod
    def _normalize_sql(sql):
        """
        Convert HIMP's existing SQLite-style positional placeholders
        to Psycopg positional placeholders.

        Repository migration will eventually remove this compatibility
        shim, but keeping it here allows backend compatibility work to
        proceed incrementally.
        """
        return sql.replace(
            "?",
            "%s",
        )

    def execute(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()

        cursor.execute(
            self._normalize_sql(sql),
            parameters,
        )

        return cursor

    def query(
        self,
        sql,
        parameters=(),
    ):
        cursor = self.connection.cursor()

        cursor.execute(
            self._normalize_sql(sql),
            parameters,
        )

        return cursor.fetchall()

    @contextmanager
    def transaction(self):
        try:
            with self.connection.transaction():
                yield self.connection

        except Exception:
            raise

    def close(self):
        self.connection.close()
