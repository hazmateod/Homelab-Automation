"""
Dashboard Health Cards Service.
"""

import json
from pathlib import Path


class HealthCardsService:

    REPORT_DIR = Path("reports/health")

    def all(self):

        cards = []

        for report in sorted(self.REPORT_DIR.glob("*.json")):

            with report.open() as f:
                data = json.load(f)

            hosts = data.get("hosts", [])

            if hosts:

                scores = [
                    host.get("health", {})
                    for host in hosts
                ]

                earned = sum(
                    item.get("earned", 0)
                    for item in scores
                )

                possible = sum(
                    item.get("possible", 0)
                    for item in scores
                )

                status = (
                    "HEALTHY"
                    if all(
                        item.get("status") == "HEALTHY"
                        for item in scores
                    )
                    else "WARNING"
                )

            else:

                health = data.get("health", {})

                earned = health.get("earned", 0)
                possible = health.get("possible", 0)
                status = health.get("status", "UNKNOWN")

            cards.append(
                {
                    "plugin": data.get("plugin"),
                    "status": status,
                    "earned": earned,
                    "possible": possible,
                    "hosts": len(hosts) if hosts else 1,
                }
            )

        return cards

    def summary(self):

        return {
            "cards": self.all()
        }
