"""
Inventory Service.

Business logic layer for HIMP inventory.
"""

from himp.collectors.inventory import InventoryCollector
from himp.database.inventory import InventoryRepository
from himp.models.inventory import (
    InventoryHost,
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

        groups = set()

        for item in records:

            groups.add(
                item["group_name"]
            )

            hosts.append(
                InventoryHost(
                    hostname=item["hostname"],
                    group=item["group_name"],
                    ip=item["ip"],
                    user=item["ansible_user"],
                    become=bool(item["become"]),
                )
            )

        return InventorySummary(
            total_hosts=len(hosts),
            groups=len(groups),
            hosts=hosts,
        )
