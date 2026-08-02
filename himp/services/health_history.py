"""
Health History Service.
"""

from himp.database.health_history import HealthHistoryRepository


class HealthHistoryService:

    def __init__(self):

        self.repository = HealthHistoryRepository()

    def record(self, execution):

        self.repository.save(
            execution
        )

    def latest(self, plugin):

        return self.repository.latest(
            plugin
        )

    def plugin(self, plugin):

        return self.repository.plugin(
            plugin
        )

    def history(self, limit=50):

        return self.repository.history(
            limit
        )

    def summary(self):

        history = self.history()

        return {
            "records": len(history),
            "plugins": len(
                {
                    item["plugin"]
                    for item in history
                }
            ),
        }
