"""
Health Trends Service.
"""

from himp.database.health_history import HealthHistoryRepository


class HealthTrendsService:

    def __init__(self):

        self.repository = HealthHistoryRepository()

    def plugin(self, plugin):

        history = self.repository.plugin(plugin)

        if not history:
            return None

        latest = history[0]

        return {
            "plugin": plugin,
            "status": latest["status"],
            "score": latest["score"],
            "possible": latest["possible"],
            "latest": latest["created_at"],
            "trend": [
                {
                    "created_at": item["created_at"],
                    "score": item["score"],
                    "status": item["status"],
                }
                for item in reversed(history)
            ],
        }

    def all(self):

        records = self.repository.history()

        plugins = sorted(
            {
                record["plugin"]
                for record in records
            }
        )

        return [
            self.plugin(plugin)
            for plugin in plugins
        ]

    def summary(self):

        trends = self.all()

        return {
            "plugins": len(trends),
            "healthy": sum(
                item["status"] == "PASS"
                for item in trends
            ),
            "warnings": sum(
                item["status"] == "WARNING"
                for item in trends
            ),
            "failed": sum(
                item["status"] == "FAIL"
                for item in trends
            ),
            "trends": trends,
        }
