"""
Inventory Service.

Business logic layer for HIMP inventory.
"""

from collections import Counter
import json
import subprocess

from himp.collectors.inventory import InventoryCollector
from himp.database.inventory import InventoryRepository
from himp.health.repository import HealthRepository
from himp.services.inventory_writer import InventoryFileWriter
from himp.config import config
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
        self.health_repository = HealthRepository()
        self.writer = InventoryFileWriter()

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

    def _validate_inventory_host(
        self,
        hostname,
        expected_ip,
    ):
        inventory_result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                config.inventory,
                "--host",
                hostname,
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if inventory_result.returncode != 0:
            raise ValueError(
                "Ansible inventory validation failed for "
                f"{hostname}: "
                f"{inventory_result.stderr.strip()}"
            )

        try:
            inventory_data = json.loads(
                inventory_result.stdout
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                "Ansible inventory returned invalid JSON for "
                f"{hostname}: {error}"
            ) from error

        actual_ip = inventory_data.get(
            "ansible_host"
        )

        if actual_ip != expected_ip:
            raise ValueError(
                "Ansible inventory IP mismatch for "
                f"{hostname}: expected {expected_ip}, "
                f"got {actual_ip}"
            )

        ping_result = subprocess.run(
            [
                "ansible",
                "-i",
                config.inventory,
                hostname,
                "-m",
                "ping",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if ping_result.returncode != 0:
            raise ValueError(
                "Ansible SSH validation failed for "
                f"{hostname}: "
                f"{ping_result.stderr.strip() or ping_result.stdout.strip()}"
            )

        return inventory_data

    def add_host(
        self,
        hostname,
        group,
        ip,
        user,
        become=False,
    ):
        existing = self.repository.find_host(
            hostname,
            include_inactive=True,
        )

        if existing is not None:
            raise ValueError(
                f"Inventory host already exists: {hostname}"
            )

        host = self.writer.add_host(
            hostname=hostname,
            group=group,
            ip=ip,
            user=user,
            become=become,
        )

        try:
            self._validate_inventory_host(
                hostname=hostname,
                expected_ip=ip,
            )
        except Exception:
            self.writer.remove_host(
                hostname=hostname,
            )
            raise

        self.repository.save_host(host)

        return self.repository.find_host(
            hostname,
            include_inactive=True,
        )

    def update_host(
        self,
        hostname,
        group,
        ip,
        user,
        become=False,
    ):
        existing = self.repository.find_host(
            hostname,
            include_inactive=True,
        )

        if existing is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        host = self.writer.update_host(
            hostname=hostname,
            group=group,
            ip=ip,
            user=user,
            become=become,
        )

        try:
            self._validate_inventory_host(
                hostname=hostname,
                expected_ip=ip,
            )
        except Exception:
            self.writer.update_host(
                hostname=hostname,
                group=existing["group_name"],
                ip=existing["ip"],
                user=existing["ansible_user"],
                become=bool(existing["become"]),
            )
            raise

        self.repository.save_host(host)

        return self.repository.find_host(
            hostname,
            include_inactive=True,
        )

    def rename_group(
        self,
        group,
        new_group,
    ):
        result = self.writer.rename_group(
            group=group,
            new_group=new_group,
        )

        hosts = self.repository.all_hosts(
            include_inactive=True,
        )

        for host in hosts:
            if host["group_name"] != group:
                continue

            self.repository.save_host(
                {
                    "hostname": host["hostname"],
                    "group": new_group,
                    "ip": host["ip"],
                    "user": host["ansible_user"],
                    "become": bool(host["become"]),
                }
            )

        return result

    def remove_host(
        self,
        hostname,
    ):
        existing = self.repository.find_host(
            hostname,
            include_inactive=True,
        )

        if existing is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        result = self.writer.remove_host(
            hostname=hostname,
        )

        self.repository.mark_removed(
            hostname
        )

        return self.repository.find_host(
            hostname,
            include_inactive=True,
        )

    def restore_host(
        self,
        hostname,
    ):
        existing = self.repository.find_host(
            hostname,
            include_inactive=True,
        )

        if existing is None:
            raise ValueError(
                f"Inventory host does not exist: {hostname}"
            )

        if existing["active"]:
            raise ValueError(
                f"Inventory host is already active: {hostname}"
            )

        host = self.writer.restore_host(
            hostname=hostname,
            group=existing["group_name"],
            ip=existing["ip"],
            user=existing["ansible_user"],
            become=bool(existing["become"]),
        )

        self.repository.restore_host(
            hostname
        )

        return self.repository.find_host(
            hostname,
            include_inactive=True,
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

    def _health_lookup(self):
        lookup = {}

        for execution in self.health_repository.plugins():
            inventory_group = execution.metadata.data.get(
                "inventory_group",
                "",
            )

            for host in execution.hosts:
                if not host.results:
                    continue

                result = host.results[0]
                health = result.details or {}

                lookup[
                    (
                        inventory_group,
                        host.hostname,
                    )
                ] = {
                    "status": result.status.value,
                    "earned": health.get(
                        "earned",
                        0,
                    ),
                    "possible": health.get(
                        "possible",
                        0,
                    ),
                }

        return lookup

    @staticmethod
    def _group_health(hosts):
        earned = sum(
            host.health_earned
            for host in hosts
        )

        possible = sum(
            host.health_possible
            for host in hosts
        )

        statuses = {
            host.health_status
            for host in hosts
            if host.health_status != "UNKNOWN"
        }

        if not statuses:
            status = "UNKNOWN"
        elif "FAIL" in statuses:
            status = "FAIL"
        elif "WARNING" in statuses:
            status = "WARNING"
        elif statuses == {"PASS"}:
            status = "PASS"
        else:
            status = "UNKNOWN"

        return {
            "status": status,
            "earned": earned,
            "possible": possible,
        }

    def summary(self):
        hosts = []

        records = self.repository.all_hosts()
        groups = Counter()

        health_lookup = self._health_lookup()

        for item in records:
            group = item["group_name"]
            hostname = item["hostname"]

            groups[group] += 1

            health = health_lookup.get(
                (
                    group,
                    hostname,
                ),
                {},
            )

            hosts.append(
                InventoryHost(
                    hostname=hostname,
                    group=group,
                    ip=item["ip"],
                    user=item["ansible_user"],
                    become=bool(item["become"]),
                    health_status=health.get(
                        "status",
                        "UNKNOWN",
                    ),
                    health_earned=health.get(
                        "earned",
                        0,
                    ),
                    health_possible=health.get(
                        "possible",
                        0,
                    ),
                )
            )

        group_hosts = {}

        for host in hosts:
            group_hosts.setdefault(
                host.group,
                [],
            ).append(host)

        group_counts = []

        for name, count in sorted(
            groups.items()
        ):
            health = self._group_health(
                group_hosts.get(name, [])
            )

            group_counts.append(
                InventoryGroup(
                    name=name,
                    hosts=count,
                    health_status=health["status"],
                    health_earned=health["earned"],
                    health_possible=health["possible"],
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
            group_counts=group_counts,
        )

        return InventorySummary(
            total_hosts=len(records),
            groups=len(groups),
            hosts=hosts,
            statistics=statistics,
        )
