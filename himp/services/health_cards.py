"""
Dashboard Health Cards Service.
"""

from himp.health.repository import HealthRepository


class HealthCardsService:

    def __init__(self):

        self.repository = HealthRepository()

    def all(self):

        cards = []

        for name, execution, attempt, freshness in self.repository.observations():

            summary = execution.summary if execution is not None else None
            current = summary is not None and freshness != "stale"

            cards.append(
                {
                    "source": "PLUGIN",
                    "plugin": name,
                    "status": summary.status.value if current else "UNKNOWN",
                    "earned": summary.score if current else 0,
                    "possible": summary.possible if summary else 0,
                    "hosts": (len(execution.hosts) or 1) if current else 0,
                    **({"latest_attempt": attempt, "evidence_freshness": freshness} if attempt else {}),
                }
            )

        return cards

    def summary(self):

        return {
            "source": "PLUGIN",
            "label": "Plugin Health",
            "cards": self.all(),
        }
