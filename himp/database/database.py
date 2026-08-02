"""
SQLite Database Manager.
"""

import sqlite3
from pathlib import Path


class Database:

    def __init__(self):

        self.path = Path("data")

        self.path.mkdir(exist_ok=True)

        self.filename = self.path / "himp.db"

        self.connection = sqlite3.connect(
            self.filename,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self.initialize()

    def initialize(self):

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

    def execute(self, sql, parameters=()):

        cursor = self.connection.cursor()

        cursor.execute(sql, parameters)

        self.connection.commit()

        return cursor

    def query(self, sql, parameters=()):

        cursor = self.connection.cursor()

        cursor.execute(sql, parameters)

        return cursor.fetchall()
