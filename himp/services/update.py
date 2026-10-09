"""
Update Service.

Provides a shared, policy-enforced service for maintenance updates.
"""

from himp.config import config
from himp.lib.ansible import run_playbook
from himp.services.host_maintenance_eligibility import (
    HostMaintenanceEligibility,
)


class UpdateService:
    """Run maintenance only against policy-eligible hosts."""

    def __init__(self, eligibility=None):
        self.eligibility = (
            eligibility
            if eligibility is not None
            else HostMaintenanceEligibility()
        )

    def update(
        self,
        target,
        limit=None,
        timeout=None,
    ):
        if target == "maintenance":
            mode = "scheduled"
            requested = "maintenance"

        elif target == "update_host":
            mode = "host"
            requested = limit

        elif target == "update_group":
            mode = "group"
            requested = limit

        else:
            raise ValueError(
                f"Unsupported maintenance target: {target}"
            )

        selection = self.eligibility.resolve(
            requested,
            mode=mode,
        )

        eligible = selection["eligible_hosts"]
        excluded = selection["excluded_hosts"]

        if not eligible:
            return {
                "target": target,
                "success": True,
                "skipped": True,
                "return_code": 0,
                "elapsed": 0.0,
                "stdout": (
                    "Maintenance skipped: no eligible hosts"
                ),
                "stderr": "",
                "eligible_hosts": [],
                "excluded_hosts": excluded,
            }

        # Explicit hostname selection prevents disabled hosts
        # from being reached through an Ansible group.
        #
        # Never pass an empty --limit to Ansible.
        safe_limit = ",".join(eligible)

        result = run_playbook(
            config.maintenance_playbook,
            safe_limit,
            timeout=timeout,
        )

        return {
            "target": target,
            "success": result.success,
            "skipped": False,
            "return_code": result.return_code,
            "elapsed": round(result.elapsed, 3),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "eligible_hosts": eligible,
            "excluded_hosts": excluded,
        }
