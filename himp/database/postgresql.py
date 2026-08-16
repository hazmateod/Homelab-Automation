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
from himp.database.postgresql_schema import (
    schema_statements,
)


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

    def initialize_schema(self):
        """
        Initialize the complete HIMP PostgreSQL schema atomically.

        Every schema statement is executed inside one PostgreSQL
        transaction. If any statement fails, PostgreSQL rolls back
        the entire schema initialization.
        """
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for statement in schema_statements():
                    cursor.execute(statement)

    def close(self):
        self.connection.close()

    def table_columns(
        self,
        table_name,
    ):
        """
        Return the column names for a PostgreSQL table in the
        current schema.
        """
        rows = self.query(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            (
                table_name,
            ),
        )

        return {
            row["column_name"]
            for row in rows
        }

    def execute_insert(
        self,
        sql,
        parameters=(),
    ):
        """
        Execute an INSERT and return its generated integer ID.

        PostgreSQL requires the INSERT to expose the generated
        identifier through RETURNING id.
        """
        normalized_sql = sql.rstrip().rstrip(";")

        if "returning" not in normalized_sql.lower():
            normalized_sql += " RETURNING id"

        cursor = self.connection.cursor()

        cursor.execute(
            self._normalize_sql(
                normalized_sql
            ),
            parameters,
        )

        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "PostgreSQL INSERT did not return "
                "a generated identifier."
            )

        return row["id"]

    @staticmethod
    def is_integrity_error(exception):
        """
        Return whether an exception represents a PostgreSQL
        integrity/constraint violation.
        """
        return isinstance(
            exception,
            psycopg.IntegrityError,
        )

    def begin_lock_transaction(
        self,
        connection,
    ):
        """
        PostgreSQL transaction serialization is provided by its
        transaction/constraint semantics. No SQLite-style
        BEGIN IMMEDIATE statement is required.
        """
        return None
