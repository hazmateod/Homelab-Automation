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

    def start(self, plan_id, host):
        # The shared maintenance lease serializes dispatch across entry points.
        # A committed marker survives the loss of the dispatching process.
        self.record(plan_id, host, {
            "host": host,
            "status": "interrupted",
            "reason": "completion_unverified",
        })

    def finish(self, plan_id, host, outcome):
        self.database.execute(
            "UPDATE maintenance_host_outcomes SET outcome=? WHERE plan_id=? AND host=?",
            (json.dumps(outcome), plan_id, host),
        )

    def requires_reconciliation(self, host):
        rows = self.database.query(
            "SELECT outcome FROM maintenance_host_outcomes WHERE host=?", (host,)
        )
        return any(
            outcome["status"] == "interrupted" and "reconciliation" not in outcome
            for outcome in (json.loads(row["outcome"]) for row in rows)
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
        if outcome["status"] != "interrupted" or "reconciliation" in outcome:
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
