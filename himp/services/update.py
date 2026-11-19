"""
Update Service.

Provides a shared, policy-enforced service for maintenance updates.
"""

from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic

from himp.config import config
from himp.database.automation_target_plans import AutomationTargetPlanRepository
from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository
from himp.lib.ansible import run_playbook, run_playbook_streaming
from himp.lib.ansible_recap import parse_play_recap
from himp.services.host_maintenance_eligibility import (
    HostMaintenanceEligibility,
)
from himp.services.inventory_publication import inventory_admission


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
                "outcome_schema": 1,
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

                def validate():
                    latest = self.eligibility.resolve(
                        requested, mode=mode, inventory_path=snapshot.name
                    )
                    return (
                        latest == selection
                        and not pending.exists()
                        and sha256(source.read_bytes()).hexdigest() == revision
                    )

                if selection["eligible_hosts"] and not validate():
                    raise RuntimeError("Maintenance target plan changed before dispatch")

                return self._run_plan(
                    target, selection, plan_id, snapshot.name, timeout, on_event,
                    validate, source,
                )
            except Exception as error:
                error.target_plan_id = plan_id
                raise

    def _run_plan(self, target, selection, plan_id, snapshot, timeout, on_event, validate, source):
        eligible = selection["eligible_hosts"]
        excluded = selection["excluded_hosts"]

        if not eligible:
            return {
                "target": target,
                "target_plan_id": plan_id,
                "success": True,
                "status": "skipped",
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

        outcomes = MaintenanceOutcomeRepository()
        results = {}
        stdout = []
        stderr = []
        elapsed = 0.0
        return_code = 0
        deadline = None if timeout is None else monotonic() + timeout
        for index, host in enumerate(eligible):
            with inventory_admission(source):
                if outcomes.requires_reconciliation(host):
                    results[host] = {"host": host, "status": "unstarted",
                                     "reason": "prior_mutation_unverified"}
                    continue
                if not validate():
                    results[host] = {"host": host, "status": "unstarted",
                                     "reason": "target_plan_changed"}
                    continue
                remaining = timeout
                if deadline is not None and index:
                    remaining = deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    results[host] = {"host": host, "status": "unstarted",
                                     "reason": "run_timeout"}
                    continue

                outcomes.start(plan_id, host)
                try:
                    if on_event is None:
                        result = run_playbook(
                            config.maintenance_playbook, host,
                            timeout=remaining, inventory_path=snapshot,
                        )
                    else:
                        result = run_playbook_streaming(
                            config.maintenance_playbook, host, timeout=remaining,
                            inventory_path=snapshot, on_event=on_event,
                            structured_events=True,
                        )
                except Exception:
                    results[host] = {"host": host, "status": "interrupted",
                                     "reason": "completion_unverified"}
                    continue

                stdout.append(result.stdout)
                stderr.append(result.stderr)
                elapsed += result.elapsed
                return_code = return_code or result.return_code
                outcome = parse_play_recap(result.stdout).get(host)
                if outcome is None or (
                    not result.success and outcome["status"] in {"succeeded", "skipped"}
                ):
                    outcome = {"host": host, "status": "interrupted",
                               "reason": "completion_unverified"}
                outcomes.finish(plan_id, host, outcome)
                results[host] = outcome

        for host, outcome in results.items():
            if outcome["status"] == "unstarted":
                outcomes.record(plan_id, host, outcome)

        statuses = {result["status"] for result in results.values()}
        if statuses == {"skipped"}:
            status = "skipped"
        elif statuses <= {"succeeded", "skipped"}:
            status = "succeeded"
        elif "succeeded" in statuses:
            status = "partial"
        elif "interrupted" in statuses:
            status = "interrupted"
        else:
            status = "failed"
        dashboard = {"status": "skipped"}
        if "succeeded" in statuses:
            remaining = None if deadline is None else deadline - monotonic()
            if remaining is None or remaining > 0:
                dashboard = self._refresh_dashboard(snapshot, remaining)
        success = status in {"succeeded", "skipped"}
        return {
            "target": target,
            "target_plan_id": plan_id,
            "status": status,
            "success": success,
            "skipped": status == "skipped",
            "return_code": return_code or int(not success),
            "elapsed": round(elapsed, 3),
            "stdout": "\n".join(stdout),
            "stderr": "\n".join(stderr),
            "host_results": results,
            "dashboard": dashboard,
            "eligible_hosts": eligible,
            "excluded_hosts": excluded,
        }

    @staticmethod
    def _refresh_dashboard(snapshot, timeout):
        try:
            result = run_playbook(
                config.dashboard_playbook, timeout=timeout, inventory_path=snapshot,
            )
        except Exception:
            return {"status": "failed", "reason": "dashboard_execution_error"}
        return {
            "status": "succeeded" if result.success else "failed",
            "return_code": result.return_code,
        }
