"""
Inventory Service.

Business logic layer for HIMP inventory.
"""

from collections import Counter

from himp.collectors.inventory import InventoryCollector
from himp.database.inventory import InventoryRepository
from himp.models.inventory import (
    InventoryGroup,
    InventoryHost,
    InventoryStatistics,
    InventorySummary,
)


class InventoryService:
    """
    Provides inventory operations.
    """

    def __init__(self):

        self.repository = InventoryRepository()

        self.collector = InventoryCollector()

    def all_hosts(
        self,
        include_inactive=False,
    ):

        return self.repository.all_hosts(
            include_inactive=include_inactive
        )

    def find_host(
        self,
        hostname,
    ):

        return self.repository.find_host(
            hostname
        )

    def count(self):

        return self.repository.count()

    def changes(
        self,
        limit=100,
    ):

        return self.repository.changes(
            limit
        )

    def sync(self):

        hosts = self.collector.hosts()

        self.repository.save_snapshot(
            hosts
        )

        return {
            "synced": len(hosts),
            "active_hosts": self.repository.count(),
            "total_hosts": len(
                self.repository.all_hosts(
                    include_inactive=True
                )
            ),
            "recent_changes": len(
                self.repository.changes(25)
            ),
        }

    def summary(self):

        hosts = []

        records = self.repository.all_hosts()

        groups = Counter()

        for item in records:

            groups[item["group_name"]] += 1

            hosts.append(
                InventoryHost(
                    hostname=item["hostname"],
                    group=item["group_name"],
                    ip=item["ip"],
                    user=item["ansible_user"],
                    become=bool(item["become"]),
                )
            )

        all_records = self.repository.all_hosts(
            include_inactive=True
        )

        statistics = InventoryStatistics(
            total_hosts=len(all_records),
            active_hosts=len(records),
            inactive_hosts=len(all_records) - len(records),
            groups=len(groups),
            recent_changes=len(
                self.repository.changes()
            ),
            group_counts=[
                InventoryGroup(
                    name=name,
                    hosts=count,
                )
                for name, count in sorted(
                    groups.items()
                )
            ],
        )

        return InventorySummary(
            total_hosts=len(records),
            groups=len(groups),
            hosts=hosts,
            statistics=statistics,
        )
