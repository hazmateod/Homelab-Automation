"""Controller-side state for the newest attempt of each health plugin."""

from contextlib import closing
from datetime import UTC, datetime
import sqlite3


class HealthAttempts:
    def __init__(self, root):
        self.root = root
        self.path = root / ".attempts.sqlite3"

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                plugin TEXT PRIMARY KEY, attempt_id TEXT NOT NULL,
                timestamp TEXT NOT NULL, status TEXT NOT NULL, failure_category TEXT
            )
        """)
        return connection

    def start(self, plugin, attempt_id):
        self.root.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                INSERT INTO attempts VALUES (?, ?, ?, 'running', NULL)
                ON CONFLICT(plugin) DO UPDATE SET attempt_id=excluded.attempt_id,
                    timestamp=excluded.timestamp, status='running', failure_category=NULL
            """, (plugin, attempt_id, datetime.now(UTC).isoformat()))

    def finish(self, plugin, attempt_id, failure, artifact=None, destination=None):
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT attempt_id FROM attempts WHERE plugin=?", (plugin,)
            ).fetchone()
            if row is None or row["attempt_id"] != attempt_id:
                return "superseded"
            if artifact is not None:
                try:
                    artifact.replace(destination)
                except OSError:
                    failure = "publication_failed"
            connection.execute("""
                UPDATE attempts SET status=?, failure_category=? WHERE plugin=?
            """, ("failed" if failure else "succeeded", failure, plugin))
            return failure

    def all(self):
        if not self.path.exists():
            return {}
        with closing(self._connect()) as connection:
            return {
                row["plugin"]: dict(row)
                for row in connection.execute("SELECT * FROM attempts")
            }


def current_evidence(attempt, report):
    """Return freshness relative to the newest admitted run."""
    if report is None:
        return "missing"
    if attempt is None:
        return "untracked"
    if attempt["status"] == "succeeded" and report.metadata.data.get("attempt_id") == attempt["attempt_id"]:
        return "current"
    return "stale"
