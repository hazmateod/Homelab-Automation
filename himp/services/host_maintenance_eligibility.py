"""
Host maintenance eligibility.

Resolve approved Ansible targets and apply persistent
operator-controlled host automation exclusions.
"""

from hashlib import sha256
import json
import re
import subprocess

from himp.config import config
from himp.database.inventory import InventoryRepository
from himp.database.host_automation_policies import (
    HostAutomationPolicyRepository,
)


def literal_host_pattern(hostname, inventory):
    return (
        re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", hostname) is not None
        and hostname not in inventory
    )


def fingerprint_host(row, variables):
    identity = (row["id"], row["first_seen"], variables)
    return sha256(
        json.dumps(identity, default=str, sort_keys=True).encode()
    ).hexdigest()


class HostMaintenanceEligibility:
    """Fail-closed host eligibility resolution."""

    def __init__(self, policies=None, inventory_repository=None):
        self.policies = (
            policies
            if policies is not None
            else HostAutomationPolicyRepository()
        )

        self.inventory_repository = inventory_repository

    @staticmethod
    def read_inventory(inventory_path=None):
        result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                str(inventory_path or config.inventory),
                "--list",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Cannot resolve Ansible inventory: "
                + result.stderr.strip()
            )

        try:
            inventory = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Ansible inventory returned invalid JSON"
            ) from error

        if not isinstance(inventory, dict):
            raise RuntimeError("Invalid Ansible inventory structure")

        return inventory

    @staticmethod
    def _group_hosts(inventory, group_name):
        """Expand Ansible groups from --list JSON safely."""
        visited = set()

        def expand(name):
            if name in visited:
                return set()

            group = inventory.get(name)
            if not isinstance(group, dict):
                raise ValueError(
                    f"Unknown inventory group: {name}"
                )

            visited.add(name)

            raw_hosts = group.get("hosts", {})
            raw_children = group.get("children", {})

            if isinstance(raw_hosts, dict):
                hosts = set(raw_hosts)
            elif isinstance(raw_hosts, list):
                hosts = set(raw_hosts)
            else:
                raise RuntimeError(
                    f"Invalid hosts for group: {name}"
                )

            if isinstance(raw_children, dict):
                children = list(raw_children)
            elif isinstance(raw_children, list):
                children = raw_children
            else:
                raise RuntimeError(
                    f"Invalid children for group: {name}"
                )

            for child in children:
                if not isinstance(child, str):
                    raise RuntimeError(
                        f"Invalid child group in: {name}"
                    )
                hosts.update(expand(child))

            return hosts

        return expand(group_name)

    def resolve(self, target, mode="scheduled", *, inventory_path=None):
        """
        Return eligible hosts and exclusions.

        Scheduled updates are restricted to maintenance.
        Manual host/group updates use explicit inventory targets,
        but still enforce operator exclusions.
        """

        if mode not in ("scheduled", "host", "group"):
            raise ValueError("Unsupported maintenance mode")

        if not isinstance(target, str) or not target.strip():
            raise ValueError("Maintenance target is required")

        target = target.strip()

        inventory = self.read_inventory(inventory_path)

        all_hosts = set(
            inventory.get("_meta", {})
            .get("hostvars", {})
            .keys()
        )

        if not all_hosts:
            raise RuntimeError(
                "Ansible inventory contains no hosts"
            )

        maintenance_hosts = self._group_hosts(
            inventory,
            "maintenance",
        )

        if not maintenance_hosts:
            raise RuntimeError(
                "Maintenance group contains no hosts"
            )

        if mode == "scheduled":
            if target != "maintenance":
                raise ValueError(
                    "Scheduled updates must target maintenance"
                )

            selected = maintenance_hosts

        elif mode == "host":
            if target not in all_hosts:
                raise ValueError(
                    f"Unknown inventory host: {target}"
                )

            selected = {target}

        else:
            selected = self._group_hosts(
                inventory,
                target,
            )

        if not selected or not selected.issubset(all_hosts):
            raise RuntimeError(
                "Maintenance target resolution failed"
            )

        if any(
            not literal_host_pattern(host, inventory)
            for host in selected
        ):
            raise ValueError("Maintenance selected an ambiguous Ansible host pattern")

        repository = self.inventory_repository or InventoryRepository()
        active = {row["hostname"]: row for row in repository.all_hosts()}
        disabled = self.policies.disabled_hosts()
        eligible = sorted((selected & active.keys()) - disabled)
        excluded = sorted(selected - set(eligible))
        hostvars = inventory["_meta"]["hostvars"]
        fingerprints = {}
        for hostname in eligible:
            row = active[hostname]
            variables = hostvars[hostname]
            if row["ip"] != variables.get("ansible_host"):
                raise ValueError("Maintenance target differs between inventory and database")
            fingerprints[hostname] = fingerprint_host(row, variables)

        return {
            "target": target,
            "mode": mode,
            "eligible_hosts": eligible,
            "target_fingerprints": fingerprints,
            "excluded_hosts": excluded,
            "selected_count": len(selected),
            "eligible_count": len(eligible),
            "excluded_count": len(excluded),
        }
