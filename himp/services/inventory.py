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
from himp.services.inventory_publication import InventoryPublication
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
        inventory_path=None,
    ):
        inventory_path = str(inventory_path or config.inventory)
        inventory_result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                inventory_path,
                "--host",
                hostname,
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
                inventory_path,
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

    def _publication(self):
        return InventoryPublication(self.writer.filename, self.repository)

    def add_host(self, hostname, group, ip, user, become=False):
        return self._write_host("add_host", hostname, group, ip, user, become)

    def update_host(self, hostname, group, ip, user, become=False):
        return self._write_host("update_host", hostname, group, ip, user, become)

    def _write_host(self, operation, hostname, group, ip, user, become):
        publication = self._publication()
        with publication.locked():
            existing = self.repository.find_host(hostname, include_inactive=True)
            if operation == "add_host" and existing is not None:
                raise ValueError(f"Inventory host already exists: {hostname}")
            if operation == "update_host" and existing is None:
                raise ValueError(f"Inventory host does not exist: {hostname}")
            with publication.stage() as (writer, original):
                edit = writer.add_host if operation == "add_host" else writer.update_host
                host = edit(hostname=hostname, group=group, ip=ip, user=user, become=become)
                self._validate_inventory_host(
                    hostname=hostname, expected_ip=ip, inventory_path=writer.filename
                )
                publication.publish(writer, original, "save_host", host)
            return self.repository.find_host(hostname, include_inactive=True)

    def rename_group(self, group, new_group):
        publication = self._publication()
        with publication.locked(), publication.stage() as (writer, original):
            result = writer.rename_group(group=group, new_group=new_group)
            publication.publish(writer, original, "rename_group", group, new_group)
            return result

    def remove_host(self, hostname):
        publication = self._publication()
        with publication.locked(), publication.stage() as (writer, original):
            if self.repository.find_host(hostname, include_inactive=True) is None:
                raise ValueError(f"Inventory host does not exist: {hostname}")
            writer.remove_host(hostname=hostname)
            publication.publish(writer, original, "mark_removed", hostname)
            return self.repository.find_host(hostname, include_inactive=True)

    def restore_host(self, hostname):
        publication = self._publication()
        with publication.locked(), publication.stage() as (writer, original):
            existing = self.repository.find_host(hostname, include_inactive=True)
            if existing is None:
                raise ValueError(f"Inventory host does not exist: {hostname}")
            if existing["active"]:
                raise ValueError(f"Inventory host is already active: {hostname}")
            writer.restore_host(
                hostname=hostname,
                group=existing["group_name"],
                ip=existing["ip"],
                user=existing["ansible_user"],
                become=bool(existing["become"]),
            )
            publication.publish(writer, original, "restore_host", hostname)
            return self.repository.find_host(hostname, include_inactive=True)

    def sync(self):
        with self._publication().locked():
            return self._sync_locked()

    def _sync_locked(self):
        hosts = self.collector.hosts()

        collected_names = {host["hostname"] for host in hosts}
        known_hosts = self.repository.all_hosts(include_inactive=True)
        active_names = {host["hostname"] for host in known_hosts if host["active"]}
        inactive_names = {host["hostname"] for host in known_hosts if not host["active"]}
        if collected_names & inactive_names:
            raise ValueError("Inventory snapshot contains inactive hosts. Restore them explicitly before syncing.")
        missing = active_names - collected_names
        if missing:
            raise ValueError(
                f"Inventory snapshot omitted {len(missing)} active host(s). "
                "Remove managed hosts explicitly before syncing."
            )
        self.repository.save_snapshot(hosts)

        return {
            "synced": len(hosts),
            "membership_drift_count": len(collected_names ^ active_names),
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
