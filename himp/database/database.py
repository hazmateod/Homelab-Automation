"""
SQLite Database Manager.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock

from himp.database.config import DatabaseConfig


def _adapt_datetime(value):
    return value.isoformat(" ")


def _convert_timestamp(value):
    return datetime.fromisoformat(
        value.decode()
    )


sqlite3.register_adapter(
    datetime,
    _adapt_datetime,
)

sqlite3.register_converter(
    "TIMESTAMP",
    _convert_timestamp,
)


class Database:

    def __init__(
        self,
        config=None,
    ):

        self.config = (
            config
            if config is not None
            else DatabaseConfig.from_environment()
        )

        if not self.config.is_sqlite:
            raise NotImplementedError(
                "PostgreSQL database connections are not "
                "enabled yet. Phase 11 backend migration "
                "is still in progress."
            )

        self.filename = self.config.sqlite_path
        self.path = self.filename.parent

        self.path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            self.filename,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )

        self.connection.row_factory = sqlite3.Row

        self._connection_lock = RLock()

        self.initialize()

    def initialize(self):

        with self._connection_lock:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS executions
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    plugin TEXT NOT NULL,

                    success INTEGER NOT NULL,

                    return_code INTEGER NOT NULL,

                    elapsed REAL NOT NULL,

                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Extend the existing executions table for persisted
            # execution output and diagnostic information.
            execution_columns = {
                row[1]
                for row in cursor.execute(
                    "PRAGMA table_info(executions)"
                ).fetchall()
            }

            execution_migrations = {
                "stdout": "ALTER TABLE executions ADD COLUMN stdout TEXT",
                "stderr": "ALTER TABLE executions ADD COLUMN stderr TEXT",
                "warnings": "ALTER TABLE executions ADD COLUMN warnings TEXT",
                "artifacts": "ALTER TABLE executions ADD COLUMN artifacts TEXT",
            }

            for column, statement in execution_migrations.items():

                if column not in execution_columns:

                    cursor.execute(statement)

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS health_history
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    plugin TEXT NOT NULL,

                    status TEXT NOT NULL,

                    score INTEGER NOT NULL,

                    possible INTEGER NOT NULL,

                    issues TEXT,

                    metadata TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self.connection.commit()

    @contextmanager
    def transaction(self):

        with self._connection_lock:
            try:
                yield self.connection
                self.connection.commit()

            except Exception:
                self.connection.rollback()
                raise

    def execute(self, sql, parameters=()):

        with self._connection_lock:
            cursor = self.connection.cursor()

            cursor.execute(
                sql,
                parameters,
            )

            self.connection.commit()

            return cursor

    def query(self, sql, parameters=()):

        with self._connection_lock:
            cursor = self.connection.cursor()

            cursor.execute(
                sql,
                parameters,
            )

            return cursor.fetchall()
