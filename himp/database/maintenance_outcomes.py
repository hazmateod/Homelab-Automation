"""Write-ahead host outcomes for maintenance target plans."""

import json

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
        return any(json.loads(row["outcome"])["status"] == "interrupted" for row in rows)
