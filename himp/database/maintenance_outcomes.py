"""Write-ahead host outcomes for maintenance target plans."""

import json
from datetime import datetime, timezone

from himp.database.automation_target_plans import AutomationTargetPlanRepository
from himp.database.factory import create_database


class MaintenanceOutcomeRepository:
    def __init__(self):
        self.database = create_database()
        self.database.execute(
            """
            CREATE TABLE IF NOT EXISTS maintenance_host_outcomes (
                plan_id TEXT NOT NULL,
                host TEXT NOT NULL,
                outcome TEXT NOT NULL,
                PRIMARY KEY (plan_id, host)
            )
            """
        )
        self.database.execute(
            "CREATE INDEX IF NOT EXISTS maintenance_host_outcomes_host "
            "ON maintenance_host_outcomes (host)"
        )

    def find(self, plan_id):
        rows = self.database.query(
            "SELECT host, outcome FROM maintenance_host_outcomes WHERE plan_id=?",
            (plan_id,),
        )
        return {row["host"]: json.loads(row["outcome"]) for row in rows}

    def read_plan_outcomes(self, plan_id):
        plan = AutomationTargetPlanRepository().find(plan_id)
        if not plan or plan.get("outcome_schema") != 1:
            return None

        recorded = self.find(plan_id)
        return {
            host: recorded.get(host, {"host": host, "status": "unstarted"})
            for host in plan["eligible_hosts"]
        }

    def record(self, plan_id, host, outcome):
        self.database.execute(
            "INSERT INTO maintenance_host_outcomes (plan_id, host, outcome) VALUES (?, ?, ?)",
            (plan_id, host, json.dumps(outcome)),
        )

    def start(self, plan_id, host, *, host_id=None):
        # The shared maintenance lease serializes dispatch across entry points.
        # A committed marker survives the loss of the dispatching process.
        outcome = {
            "host": host,
            "status": "interrupted",
            "reason": "completion_unverified",
        }
        if host_id is not None:
            outcome["host_id"] = host_id
        self.record(plan_id, host, outcome)

    def finish(self, plan_id, host, outcome):
        self.database.execute(
            "UPDATE maintenance_host_outcomes SET outcome=? WHERE plan_id=? AND host=?",
            (json.dumps(outcome), plan_id, host),
        )

    def requires_reconciliation(self, host, *, host_id=None, aliases=()):
        names = tuple(dict.fromkeys((host, *aliases)))
        placeholders = ", ".join("?" for _ in names)
        rows = self.database.query(
            f"SELECT outcome FROM maintenance_host_outcomes WHERE host IN ({placeholders})",
            names,
        )
        return any(
            (host_id is None or outcome.get("host_id") in (None, host_id))
            and self.needs_reconciliation(outcome)
            for outcome in (json.loads(row["outcome"]) for row in rows)
        )

    @staticmethod
    def needs_reconciliation(outcome):
        if "reconciliation" in outcome:
            return False
        return (
            outcome["status"] in {"interrupted", "failed"}
            or (
                outcome["status"] == "unreachable"
                and bool(outcome.get("ok") or outcome.get("changed"))
            )
        )

    def reconcile(self, plan_id, host, note):
        """Acknowledge a manually verified mutation without rewriting its outcome."""
        note = note.strip()
        if not note:
            raise ValueError("Reconciliation requires a verification note")
        rows = self.database.query(
            "SELECT outcome FROM maintenance_host_outcomes WHERE plan_id=? AND host=?",
            (plan_id, host),
        )
        if not rows:
            return False

        original = rows[0]["outcome"]
        outcome = json.loads(original)
        if not self.needs_reconciliation(outcome):
            return False

        outcome["reconciliation"] = {
            "note": note,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        return self.database.execute_affected(
            "UPDATE maintenance_host_outcomes SET outcome=? "
            "WHERE plan_id=? AND host=? AND outcome=?",
            (json.dumps(outcome), plan_id, host, original),
        ) == 1
