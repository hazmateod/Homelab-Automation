"""Durable automation execution progress repository."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from himp.database.factory import create_database


class AutomationProgressRepository:
    """Persist live execution progress independently of history."""

    def __init__(self, database=None):
        self.database = database or create_database()
        self._ensure_table()

    def _ensure_table(self):
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_execution_progress
            (
                run_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                execution_token TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                status TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT,
                host_results TEXT NOT NULL,
                completed_execution_id INTEGER
            )
            """
        )

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def start(
        self,
        task_id,
        attempt=1,
        hosts=None,
        execution_token=None,
    ):
        now = self._now()
        run_id = str(uuid4())
        execution_token = execution_token or str(uuid4())

        host_results = {
            host: {"host": host, "status": "pending"}
            for host in (hosts or [])
        }

        self.database.execute(
            """
            INSERT INTO automation_execution_progress
            (
                run_id, task_id, execution_token,
                attempt, status, revision,
                started_at, updated_at, host_results
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                task_id,
                execution_token,
                attempt,
                "running",
                0,
                now,
                now,
                json.dumps(host_results),
            ),
        )

        return run_id

    def get(self, run_id):
        rows = self.database.query(
            """
            SELECT *
            FROM automation_execution_progress
            WHERE run_id=?
            LIMIT 1
            """,
            (run_id,),
        )

        if not rows:
            return None

        result = dict(rows[0])
        result["host_results"] = json.loads(
            result["host_results"]
        )
        return result

    def latest_running(self, task_id):
        """Return the most recently started unfinished run."""
        rows = self.database.query(
            """
            SELECT run_id
            FROM automation_execution_progress
            WHERE task_id=? AND status='running'
            ORDER BY started_at DESC, run_id DESC
            LIMIT 1
            """,
            (task_id,),
        )

        if not rows:
            return None

        return self.get(rows[0]["run_id"])

    def interrupt(self, run_id, *, execution_token):
        """Atomically interrupt an execution owned by this token."""
        if not isinstance(execution_token, str) or not execution_token:
            raise ValueError("Execution token is required")
        now = self._now()

        affected = self.database.execute_affected(
            """
            UPDATE automation_execution_progress
            SET status='interrupted',
                revision=revision+1,
                updated_at=?,
                finished_at=?
            WHERE run_id=?
              AND execution_token=?
              AND status='running'
            """,
            (now, now, run_id, execution_token),
        )

        if affected != 1:
            raise ValueError(
                "Execution is missing or already finalized"
            )

        return self.get(run_id)

    def update(
        self,
        run_id,
        host_results=None,
        status=None,
        completed_execution_id=None,
        *,
        execution_token,
    ):
        if not isinstance(execution_token, str) or not execution_token:
            raise ValueError("Execution token is required")

        current = self.get(run_id)

        if current is None:
            raise ValueError("Unknown automation progress run")

        if current["execution_token"] != execution_token:
            raise ValueError("Execution token ownership mismatch")

        now = self._now()
        next_status = status or current["status"]

        if next_status not in {
            "running",
            "succeeded",
            "failed",
            "interrupted",
        }:
            raise ValueError("Invalid execution progress status")

        if current["status"] != "running":
            raise ValueError("Execution progress is already finalized")

        next_hosts = (
            host_results
            if host_results is not None
            else current["host_results"]
        )

        finished_at = (
            now if next_status != "running" else None
        )

        affected = self.database.execute_affected(
            """
            UPDATE automation_execution_progress
            SET status=?,
                revision=revision+1,
                updated_at=?,
                finished_at=?,
                host_results=?,
                completed_execution_id=?
            WHERE run_id=?
              AND execution_token=?
              AND status='running'
              AND revision=?
            """,
            (
                next_status,
                now,
                finished_at,
                json.dumps(next_hosts),
                completed_execution_id,
                run_id,
                execution_token,
                current["revision"],
            ),
        )

        if affected != 1:
            raise ValueError(
                "Concurrent execution progress update rejected"
            )

        return self.get(run_id)
