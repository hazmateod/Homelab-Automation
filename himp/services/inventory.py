"""
Inventory Service.

Business logic layer for HIMP inventory.
"""

from collections import Counter
import json
import re
import subprocess
from tempfile import NamedTemporaryFile
from uuid import uuid4

from himp.collectors.inventory import InventoryCollector
from himp.database.host_automation_policies import HostAutomationPolicyRepository
from himp.database.host_identity import HostIdentityRepository
from himp.database.inventory import InventoryRepository
from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository
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
        expected_user=None,
        readiness=None,
        expected_become=None,
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

        if expected_user is not None and inventory_data.get("ansible_user") != expected_user:
            raise ValueError(f"Ansible inventory user changed for {hostname}")

        if expected_become is not None and inventory_data.get("ansible_become", False) != expected_become:
            raise ValueError(f"Ansible privilege escalation setting differs for {hostname}")

        if readiness == "pending":
            return inventory_data

        try:
            if readiness == "verify":
                # Use effective host/group variables but restrict the invocation
                # to one host, even when its name is also an inventory group.
                # Maintenance enables become at play level. Match that default;
                # an explicit inventory variable takes precedence in Ansible.
                with NamedTemporaryFile(mode="w", suffix=".yml") as candidate:
                    json.dump({"all": {"hosts": {hostname: inventory_data}}}, candidate)
                    candidate.flush()
                    result = subprocess.run(
                        ["ansible", "-i", candidate.name, "all", "--become", "-m",
                         "ansible.builtin.setup", "-a", "filter=ansible_distribution"],
                        capture_output=True, text=True, timeout=30, check=False,
                    )
            else:
                result = subprocess.run(
                    ["ansible", "-i", inventory_path, hostname, "-m", "ping"],
                    capture_output=True, text=True, timeout=60, check=False,
                )
        except subprocess.TimeoutExpired as error:
            raise ValueError(f"Ansible connection check timed out for {hostname}") from error

        if result.returncode != 0:
            output = result.stdout.strip() or result.stderr.strip()
            label = "Ansible readiness check" if readiness else "Ansible SSH validation"
            raise ValueError(f"{label} failed for {hostname}: {output[-2000:]}")

        return inventory_data

    def _publication(self):
        return InventoryPublication(self.writer.filename, self.repository)

    def add_host(self, hostname, group, ip, user, become=False, *, readiness=None):
        return self._write_host("add_host", hostname, group, ip, user, become, readiness=readiness)

    def update_host(self, hostname, group, ip, user, become=False, *, readiness=None):
        return self._write_host("update_host", hostname, group, ip, user, become, readiness=readiness)

    def _write_host(self, operation, hostname, group, ip, user, become, *, readiness=None):
        if readiness is not None and (
            not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", hostname)
            or not re.fullmatch(r"[A-Za-z0-9:][A-Za-z0-9_.:%-]*", ip)
            or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", user)
        ):
            raise ValueError("Enter a valid hostname, address, and SSH username.")
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
                validation = {}
                if readiness is not None:
                    validation.update(expected_user=user, expected_become=become, readiness=readiness)
                    host["readiness_pending"] = readiness == "pending"
                try:
                    self._validate_inventory_host(
                        hostname=hostname, expected_ip=ip, inventory_path=writer.filename,
                        **validation,
                    )
                except subprocess.TimeoutExpired as error:
                    raise ValueError(f"Ansible inventory check timed out for {hostname}") from error
                publication.publish(writer, original, "save_host", host)
            return self.repository.find_host(hostname, include_inactive=True)

    def rename_group(self, group, new_group):
        publication = self._publication()
        with publication.locked(), publication.stage() as (writer, original):
            result = writer.rename_group(group=group, new_group=new_group)
            publication.publish(writer, original, "rename_group", group, new_group)
            return result

    def rename_host(self, hostname, new_hostname):
        publication = self._publication()
        with publication.locked(), publication.stage() as (writer, original):
            existing = self.repository.find_host(hostname)
            if existing is None:
                raise ValueError(f"Inventory host does not exist: {hostname}")
            if self.repository.find_host(new_hostname, include_inactive=True) is not None:
                raise ValueError(f"Inventory host already exists: {new_hostname}")
            policy = HostAutomationPolicyRepository(self.repository.database).get(new_hostname)
            if policy["changed_by"] is not None:
                raise ValueError(f"An automation policy already exists for {new_hostname}")
            writer.rename_host(hostname, new_hostname)
            self._validate_inventory_host(
                hostname=new_hostname,
                expected_ip=existing["ip"],
                inventory_path=writer.filename,
                expected_user=existing["ansible_user"],
            )
            publication.publish(
                writer, original, "rename_host", existing["id"], hostname, new_hostname,
                str(uuid4()),
            )
            return self.repository.find_host(new_hostname)

    def maintenance_readiness(self):
        identities = HostIdentityRepository(self.repository)
        outcomes = MaintenanceOutcomeRepository()
        result = {}
        for row in identities.current():
            hostname = row["hostname"]
            pending = self._pending_outcomes(row, identities, outcomes)
            if pending or row["endpoint_review_required"] or row["readiness_pending"]:
                result[hostname] = {
                    "host_id": row["host_id"],
                    "incarnation": row["current_incarnation"],
                    "ip": row["ip"],
                    "user": row["ansible_user"],
                    "endpoint_review": bool(row["endpoint_review_required"]),
                    "readiness_pending": bool(row["readiness_pending"]),
                    "outcomes": pending,
                }
                if row["endpoint_review_required"]:
                    result[hostname]["endpoint_changes"] = self.repository.latest_endpoint_changes(hostname)
        return result

    @staticmethod
    def _pending_outcomes(row, identities, outcomes):
        aliases = {
            name for alias in identities.aliases(row["host_id"])
            for name in (alias["old_hostname"], alias["new_hostname"])
        }
        return outcomes.pending(row["hostname"], host_id=row["host_id"], aliases=aliases)

    def reconcile_maintenance(self, hostname, host_id, incarnation, plan_id, plan_host, note, *, endpoint):
        from himp.services.maintenance_reconciliation import maintenance_reconciliation

        with maintenance_reconciliation(), self._publication().locked():
            identities = HostIdentityRepository(self.repository)
            current = next((row for row in identities.current() if row["hostname"] == hostname), None)
            if current is None or (current["host_id"], current["current_incarnation"]) != (host_id, incarnation):
                raise ValueError("The inventory host incarnation has changed")
            if endpoint != (current["ip"], current["ansible_user"]):
                raise ValueError("The inventory endpoint changed. Verify the current address and SSH user.")
            outcomes = MaintenanceOutcomeRepository()
            pending = self._pending_outcomes(current, identities, outcomes)
            if not any((row["plan_id"], row["host"]) == (plan_id, plan_host) for row in pending):
                raise ValueError("No unreconciled maintenance outcome matched the plan and host.")
            if not outcomes.reconcile(plan_id, plan_host, note):
                raise ValueError("No unreconciled maintenance outcome matched the plan and host.")

    def record_verified_rebuild(self, hostname, host_id, expected_incarnation, *, endpoint=None):
        return self._verify_host_binding(hostname, host_id, expected_incarnation, endpoint, rebuild=True)

    def record_verified_move(self, hostname, host_id, expected_incarnation, *, endpoint):
        return self._verify_host_binding(hostname, host_id, expected_incarnation, endpoint, rebuild=False)

    def _verify_host_binding(self, hostname, host_id, expected_incarnation, endpoint, *, rebuild):
        with self._publication().locked():
            host = self.repository.find_host(hostname)
            if host is None:
                raise ValueError(f"Inventory host does not exist: {hostname}")
            identities = HostIdentityRepository(self.repository)
            target = (host["id"], hostname, host["ip"], host["ansible_user"])
            current = identities.current_host(*target, include_pending=True)
            if current != {"host_id": host_id, "incarnation": expected_incarnation}:
                raise ValueError("The inventory host incarnation has changed")
            if (endpoint is not None or identities.current_host(*target) is None) and endpoint != target[2:]:
                raise ValueError("Verify the current inventory address and SSH user")
            if not rebuild:
                if not identities.confirm_endpoint_move(host["id"]):
                    raise ValueError("The host has no pending endpoint review")
                return current
            incarnation = identities.record_rebuild(host_id, expected_incarnation)
            if incarnation is None:
                raise ValueError("The inventory host incarnation has changed")
            return {"host_id": host_id, "incarnation": incarnation}

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
        publication = self._publication()
        with publication.locked():
            result = self._sync_locked()
            publication.reconcile_identities()
            return result

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
