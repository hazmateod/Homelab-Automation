"""
Update Service.

Provides a shared, policy-enforced service for maintenance updates.
"""

from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from himp.config import config
from himp.database.automation_target_plans import AutomationTargetPlanRepository
from himp.lib.ansible import run_playbook, run_playbook_streaming
from himp.lib.ansible_recap import parse_play_recap
from himp.services.host_maintenance_eligibility import (
    HostMaintenanceEligibility,
)


class UpdateService:
    """Run maintenance only against policy-eligible hosts."""

    def __init__(self, eligibility=None, plans=None):
        self.eligibility = (
            eligibility
            if eligibility is not None
            else HostMaintenanceEligibility()
        )

        self.plans = plans or AutomationTargetPlanRepository()

    def update(
        self,
        target,
        limit=None,
        timeout=None,
        *,
        on_event=None,
        on_hosts_resolved=None,
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

        source = Path(config.inventory).resolve()
        pending = source.with_name(f".{source.name}.pending")
        if pending.exists():
            raise RuntimeError("Inventory publication must be reconciled before maintenance")
        source_contents = source.read_bytes()
        revision = sha256(source_contents).hexdigest()
        with NamedTemporaryFile(
            dir=source.parent, prefix=".himp-stage-", suffix=".yml"
        ) as snapshot:
            snapshot.write(source_contents)
            snapshot.flush()
            selection = self.eligibility.resolve(
                requested, mode=mode, inventory_path=snapshot.name
            )
            plan_id = self.plans.save({
                "task": target,
                "mode": mode,
                "requested": requested,
                "inventory_revision": revision,
                "eligible_hosts": selection["eligible_hosts"],
                "excluded_hosts": selection["excluded_hosts"],
                "target_fingerprints": selection["target_fingerprints"],
            })
            try:
                if on_hosts_resolved is not None:
                    on_hosts_resolved(
                        list(selection["eligible_hosts"]),
                        list(selection["excluded_hosts"]),
                    )
                if selection["eligible_hosts"]:
                    latest = self.eligibility.resolve(
                        requested, mode=mode, inventory_path=snapshot.name
                    )
                    if (
                        latest != selection
                        or pending.exists()
                        or sha256(source.read_bytes()).hexdigest() != revision
                    ):
                        raise RuntimeError("Maintenance target plan changed before dispatch")
                return self._run_plan(
                    target, selection, plan_id, snapshot.name, timeout, on_event
                )
            except Exception as error:
                error.target_plan_id = plan_id
                raise

    def _run_plan(self, target, selection, plan_id, snapshot, timeout, on_event):
        eligible = selection["eligible_hosts"]
        excluded = selection["excluded_hosts"]

        if not eligible:
            return {
                "target": target,
                "target_plan_id": plan_id,
                "success": True,
                "skipped": True,
                "return_code": 0,
                "elapsed": 0.0,
                "stdout": (
                    "Maintenance skipped: no eligible hosts"
                ),
                "stderr": "",
                "host_results": {},
                "eligible_hosts": [],
                "excluded_hosts": excluded,
            }

        # Explicit hostname selection prevents disabled hosts
        # from being reached through an Ansible group.
        #
        # Never pass an empty --limit to Ansible.
        safe_limit = ",".join(eligible)
        if on_event is None:
            result = run_playbook(
                config.maintenance_playbook,
                safe_limit,
                timeout=timeout,
                inventory_path=snapshot,
            )
        else:
            result = run_playbook_streaming(
                config.maintenance_playbook,
                safe_limit,
                timeout=timeout,
                inventory_path=snapshot,
                on_event=on_event,
                structured_events=True,
            )

        return {
            "target": target,
            "target_plan_id": plan_id,
            "success": result.success,
            "skipped": False,
            "return_code": result.return_code,
            "elapsed": round(result.elapsed, 3),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "host_results": parse_play_recap(result.stdout),
            "eligible_hosts": eligible,
            "excluded_hosts": excluded,
        }
