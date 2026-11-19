"""Durable resolved scope for admitted maintenance runs."""

import json
from uuid import uuid4

from himp.database.factory import create_database


class AutomationTargetPlanRepository:
    def save(self, plan):
        database = create_database()
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_target_plans (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                plan TEXT NOT NULL
            )
            """
        )
        plan_id = str(uuid4())
        database.execute(
            "INSERT INTO automation_target_plans (id, plan) VALUES (?, ?)",
            (plan_id, json.dumps(plan, sort_keys=True)),
        )
        return plan_id
