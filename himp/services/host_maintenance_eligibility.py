"""
Host maintenance eligibility.

Resolve approved Ansible targets and apply persistent
operator-controlled host automation exclusions.
"""

import json
import subprocess

from himp.config import config
from himp.database.host_automation_policies import (
    HostAutomationPolicyRepository,
)


class HostMaintenanceEligibility:
    """Fail-closed host eligibility resolution."""

    def __init__(self, policies=None):
        self.policies = (
            policies
            if policies is not None
            else HostAutomationPolicyRepository()
        )

    def _inventory(self):
        result = subprocess.run(
            [
                "ansible-inventory",
                "-i",
                config.inventory,
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

    def resolve(self, target, mode="scheduled"):
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

        inventory = self._inventory()

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

        disabled = self.policies.disabled_hosts()

        eligible = sorted(selected - disabled)
        excluded = sorted(selected & disabled)

        return {
            "target": target,
            "mode": mode,
            "eligible_hosts": eligible,
            "excluded_hosts": excluded,
            "selected_count": len(selected),
            "eligible_count": len(eligible),
            "excluded_count": len(excluded),
        }
