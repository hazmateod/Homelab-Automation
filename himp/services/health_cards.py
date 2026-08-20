"""
Dashboard Health Cards Service.
"""

from himp.health.repository import HealthRepository


class HealthCardsService:

    def __init__(self):

        self.repository = HealthRepository()

    def all(self):

        cards = []

        for execution in self.repository.plugins():

            summary = execution.summary

            cards.append(
                {
                    "source": "PLUGIN",
                    "plugin": summary.plugin,
                    "status": summary.status.value,
                    "earned": summary.score,
                    "possible": summary.possible,
                    "hosts": len(execution.hosts) or 1,
                }
            )

        return cards

    def summary(self):

        return {
            "source": "PLUGIN",
            "label": "Plugin Health",
            "cards": self.all(),
        }
