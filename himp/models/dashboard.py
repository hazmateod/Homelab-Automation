"""
Dashboard model.
"""

import json
from pathlib import Path

from himp.models.host import Host


class Dashboard:

    def __init__(self, generated, hosts):
        self.generated = generated
        self.hosts = hosts

    @classmethod
    def load(cls, filename="reports/dashboard/dashboard.json"):

        path = Path(filename)

        with path.open() as f:
            data = json.load(f)

        hosts = []

        for item in data["hosts"]:
            hosts.append(
                Host(
                    hostname=item["hostname"],
                    ip=item["ip"],
                    os=item["os"],
                    kernel=item["kernel"],
                    score=item["score"],
                    status=item["status"],
                )
            )

        return cls(
            generated=data["generated"],
            hosts=hosts,
        )

    def count_by_status(self, status):
        return sum(
            1
            for host in self.hosts
            if host.status == status
        )

    def healthy_count(self):
        return self.count_by_status("HEALTHY")

    def warning_count(self):
        return self.count_by_status("WARNING")

    def critical_count(self):
        return self.count_by_status("CRITICAL")

    def unknown_count(self):
        return len(self.hosts) - (
            self.healthy_count()
            + self.warning_count()
            + self.critical_count()
        )

    def average_score(self):
        if not self.hosts:
            return 0

        return round(
            sum(host.score for host in self.hosts) / len(self.hosts),
            1,
        )

    def hosts_by_score(self):
        return sorted(
            self.hosts,
            key=lambda host: host.score,
        )

    def hosts_by_status(self, status):
        return [
            host
            for host in self.hosts
            if host.status == status
        ]

    def find_host(self, hostname):
        for host in self.hosts:
            if host.hostname == hostname:
                return host

        return None
