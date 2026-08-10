"""
Host Health Dashboard Service.
"""

from himp.services.host_health import HostHealthService
from himp.database.inventory import InventoryRepository


class HostHealthDashboardService:
    """
    Aggregates persisted host health results for dashboard use.
    """

    def __init__(self):

        self.inventory = InventoryRepository()

        self.health = HostHealthService()

    @staticmethod
    def _score(status):

        if status == "PASS":
            return 100

        if status == "WARNING":
            return 50

        if status == "UNKNOWN":
            return 25

        return 0

    @staticmethod
    def _status_rank(status):

        return {
            "FAIL": 4,
            "WARNING": 3,
            "UNKNOWN": 2,
            "PASS": 1,
        }.get(
            status,
            2,
        )

    def hosts(self):

        results = []

        for host in self.inventory.all_hosts():

            latest = self.health.latest(
                hostname=host["hostname"],
            )

            if latest is None:

                status = "UNKNOWN"
                score = 0

                results.append(
                    {
                        "hostname": host["hostname"],
                        "group": host["group_name"],
                        "ip": host["ip"],
                        "user": host["ansible_user"],
                        "status": status,
                        "score": score,
                        "check": None,
                        "message": "No host health check has been run.",
                        "duration_ms": 0,
                        "created_at": None,
                        "details": {},
                    }
                )

                continue

            status = latest["status"]

            results.append(
                {
                    "hostname": host["hostname"],
                    "group": host["group_name"],
                    "ip": host["ip"],
                    "user": host["ansible_user"],
                    "status": status,
                    "score": self._score(status),
                    "check": latest["check_name"],
                    "message": latest["message"],
                    "duration_ms": latest["duration_ms"],
                    "created_at": latest["created_at"],
                    "details": latest["details"],
                }
            )

        return results

    def current(
        self,
        hostname,
    ):

        for host in self.hosts():

            if host["hostname"] == hostname:

                return host

        return None


    def history(
        self,
        hostname=None,
        limit=50,
    ):

        if hostname is None:

            return self.health.history(
                limit=limit,
            )

        return self.health.host(
            hostname=hostname,
            limit=limit,
        )


    def summary(self):

        hosts = self.hosts()

        total = len(hosts)

        passed = sum(
            host["status"] == "PASS"
            for host in hosts
        )

        warnings = sum(
            host["status"] == "WARNING"
            for host in hosts
        )

        failed = sum(
            host["status"] == "FAIL"
            for host in hosts
        )

        unknown = sum(
            host["status"] == "UNKNOWN"
            for host in hosts
        )

        score = (
            round(
                sum(
                    host["score"]
                    for host in hosts
                ) / total
            )
            if total
            else 0
        )

        failures = [
            host
            for host in hosts
            if host["status"] == "FAIL"
        ]

        failures.sort(
            key=lambda host: (
                host["created_at"] or "",
                host["hostname"],
            ),
            reverse=True,
        )

        return {
            "total": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "unknown": unknown,
            "score": score,
            "hosts": hosts,
            "failures": failures,
            "trends": self.trends(),
        }

    def trends(
        self,
        limit=10,
    ):

        trends = []

        for host in self.inventory.all_hosts():

            history = self.health.host(
                hostname=host["hostname"],
                limit=limit,
            )

            trends.append(
                {
                    "hostname": host["hostname"],
                    "group": host["group_name"],
                    "ip": host["ip"],
                    "status": (
                        history[0]["status"]
                        if history
                        else "UNKNOWN"
                    ),
                    "latest": (
                        history[0]["created_at"]
                        if history
                        else None
                    ),
                    "trend": [
                        {
                            "created_at": record["created_at"],
                            "status": record["status"],
                            "duration_ms": record["duration_ms"],
                            "message": record["message"],
                        }
                        for record in reversed(history)
                    ],
                }
            )

        return trends


    def recent_failures(
        self,
        limit=10,
    ):

        history = self.health.history(
            limit=limit * 5,
        )

        failures = [
            record
            for record in history
            if record["status"] == "FAIL"
        ]

        return failures[:limit]
