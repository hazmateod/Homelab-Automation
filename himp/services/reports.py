"""
Report Service.

Provides report inventory and dashboard report information.
"""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from himp.config import config
from himp.database.automation_executions import AutomationExecutionRepository
from himp.database.automation_target_plans import AutomationTargetPlanRepository
from himp.database.host_identity import HostIdentityRepository
from himp.database.inventory import InventoryRepository
from himp.lib.ansible import run_playbook
from himp.services.host_maintenance_eligibility import (
    HostMaintenanceEligibility,
    fingerprint_host,
    literal_host_pattern,
)
from himp.models.dashboard import Dashboard
from himp.services.inventory_publication import inventory_admission


class ReportTargetChangedError(ValueError):
    """The recorded report target cannot be proven safe to retry."""


class ReportService:

    def __init__(self):

        self.root = Path("reports")
        self.automation_executions = (
            AutomationExecutionRepository()
        )


    def generate(self, limit=None, timeout=None, *, expected_target_plan_id=None):
        with inventory_admission(config.inventory):
            return self._generate(limit, timeout, expected_target_plan_id=expected_target_plan_id)

    def _generate(self, limit, timeout, *, expected_target_plan_id):
        from himp.database.host_automation_policies import HostAutomationPolicyRepository

        disabled = HostAutomationPolicyRepository().disabled_hosts()
        if not limit or not literal_host_pattern(limit, {}):
            if expected_target_plan_id is not None:
                raise ReportTargetChangedError("Report retry requires one verified host")
            return self._run_broad_report(limit, timeout, disabled)

        source = Path(config.inventory).resolve()
        contents = source.read_bytes()
        with NamedTemporaryFile(
            dir=source.parent, prefix=".himp-stage-", suffix=".yml"
        ) as snapshot:
            snapshot.write(contents)
            snapshot.flush()
            inventory = HostMaintenanceEligibility.read_inventory(snapshot.name)
            variables = inventory.get("_meta", {}).get("hostvars", {}).get(limit)
            if not literal_host_pattern(limit, inventory) or variables is None:
                if expected_target_plan_id is not None:
                    raise ReportTargetChangedError("The original report host is no longer identifiable")
                return self._run_broad_report(limit, timeout, disabled)
            if limit in disabled:
                raise ReportTargetChangedError("Report host is disabled by automation policy")
            repository = InventoryRepository()
            row = repository.find_host(limit)
            if row is None or row["ip"] != variables.get("ansible_host"):
                raise ReportTargetChangedError("Report host is inactive or differs from inventory")

            plan = {
                "task": "generate_reports",
                "mode": "host",
                "requested": limit,
                "inventory_revision": sha256(contents).hexdigest(),
                "eligible_hosts": [limit],
                "target_fingerprints": {limit: fingerprint_host(row, variables)},
            }
            identity = HostIdentityRepository(repository).current_host(
                row["id"], limit, variables.get("ansible_host"), variables.get("ansible_user")
            )
            bindings = {}
            if identity is not None:
                plan["host_identity"] = identity
                bindings[limit] = {**identity, "ip": row["ip"], "user": row["ansible_user"]}
            plans = AutomationTargetPlanRepository()
            if expected_target_plan_id is not None and plans.find(expected_target_plan_id) != plan:
                raise ReportTargetChangedError("The report inventory or host identity has changed")
            if source.with_name(f".{source.name}.pending").exists() or source.read_bytes() != contents:
                raise ReportTargetChangedError("Inventory changed while preparing the report")
            plan_id = plans.save(plan)
            try:
                return {
                    **self._run_report(
                        limit, timeout, inventory_path=snapshot.name, bindings=bindings
                    ),
                    "target_plan_id": plan_id,
                }
            except Exception as error:
                error.target_plan_id = plan_id
                raise

    def _run_broad_report(self, limit, timeout, disabled):
        if disabled:
            import re

            if any(re.fullmatch(r"[A-Za-z0-9_.-]+", host) is None for host in disabled):
                raise ValueError("Invalid hostname in automation exclusion policy")
            limit = (limit or "all") + "".join(f":!{host}" for host in sorted(disabled))
        identities = HostIdentityRepository()
        return self._run_report(limit, timeout, bindings=identities.execution_bindings())

    @staticmethod
    def _run_report(limit, timeout, *, inventory_path=None, bindings=None):
        options = {"timeout": timeout}
        if inventory_path is not None:
            options["inventory_path"] = inventory_path
        if bindings:
            options["extra_vars"] = {"himp_host_bindings": bindings}
        result = run_playbook(config.report_playbook, limit, **options)
        return {"success": result.success, "elapsed": result.elapsed}

    @staticmethod
    def generated_at(report):
        metadata = report.get("metadata")
        timestamp = metadata.get("report_generated") if isinstance(metadata, dict) else None
        return timestamp if isinstance(timestamp, str) else None

    def current_host_reports(self, current=None):
        """Shadow view of verified JSON reports, including evidence from a prior alias."""
        if current is None:
            current = HostIdentityRepository().current_hostnames()
        return self._select_host_reports(current)[0]

    def dashboard_variables(self):
        bindings = HostIdentityRepository().report_bindings()
        current = {
            (identity["host_id"], identity["incarnation"]): hostname
            for hostname, identity in bindings.items() if identity is not None
        }
        reports, skipped = self._select_host_reports(current, dashboard_bindings=bindings)
        return {
            "himp_dashboard_reports": list(reports.values()),
            "himp_dashboard_skipped_reports": skipped,
        }

    def _select_host_reports(self, current, *, dashboard_bindings=None):
        root = self.root / "json"
        artifacts = list(root.glob("*.json"))
        if dashboard_bindings is not None:
            artifacts.extend((root / "unverified").glob("*.json"))
        selected = {}
        ranks = {}
        skipped = []
        for artifact in sorted(artifacts):
            try:
                report = json.loads(artifact.read_text(encoding="utf-8"))
            except (OSError, ValueError, RecursionError):
                skipped.append(str(artifact.relative_to(root)))
                continue
            if not isinstance(report, dict):
                skipped.append(str(artifact.relative_to(root)))
                continue
            identity = report.get("host_identity")
            canonical = artifact.parent == root
            hostname = (
                HostIdentityRepository.projected_hostname(current, identity) if canonical else None
            )
            if hostname is None and dashboard_bindings is not None:
                if identity is None and artifact.stem not in dashboard_bindings:
                    hostname = artifact.stem
            if hostname is None:
                continue
            rank = (identity is not None, canonical, self.generated_at(report) or "", artifact.stem == hostname)
            if dashboard_bindings is not None:
                try:
                    report = self._dashboard_report(report, hostname)
                except (ValueError, RecursionError):
                    skipped.append(str(artifact.relative_to(root)))
                    continue
            if hostname not in ranks or rank > ranks[hostname]:
                selected[hostname] = report
                ranks[hostname] = rank
        return selected, skipped

    @staticmethod
    def _dashboard_report(report, hostname):
        metadata = report.get("metadata")
        network = report.get("network", {})
        health = report.get("health", {})
        if not all(isinstance(section, dict) for section in (metadata, network, health)):
            raise ValueError("Invalid dashboard report sections")
        overall = health.get("overall", {})
        if not isinstance(overall, dict) or type(overall.get("score", 0)) is not int:
            raise ValueError("Invalid dashboard health data")
        return {
            "metadata": {
                "hostname": hostname,
                "operating_system": str(metadata.get("operating_system", "Unknown")),
                "kernel": str(metadata.get("kernel", "Unknown")),
            },
            "network": {"primary_ip": str(network.get("primary_ip", "Unknown"))},
            "health": {"overall": {
                "score": overall.get("score", 0),
                "status": str(overall.get("status", "UNKNOWN")),
            }},
            "host_identity": report.get("host_identity"),
        }

    def summary(self):

        return {
            "dashboard": self.dashboard(),
            "health": self.count_files(
                self.root / "health"
            ),
            "discovery": self.count_files(
                self.root / "discovery"
            ),
            "current": self.count_files(
                self.root / "current"
            ),
            "history": self.count_files(
                self.root / "history"
            ),
            "json": self.count_files(
                self.root / "json"
            ),
        }


    def count_files(
        self,
        path,
    ):

        if not path.exists():

            return 0

        return len(
            [
                item
                for item in path.rglob("*")
                if item.is_file()
            ]
        )


    def dashboard(self):

        filename = (
            self.root
            / "dashboard"
            / "dashboard.json"
        )

        if not filename.exists():

            return None

        dashboard = Dashboard.load(
            str(filename), bindings=HostIdentityRepository().report_bindings()
        )

        return {
            "generated": dashboard.generated,
            "hosts": len(dashboard.hosts),
            "healthy": dashboard.healthy_count(),
            "warnings": dashboard.warning_count(),
            "critical": dashboard.critical_count(),
            "unknown": dashboard.unknown_count(),
            "average_score": dashboard.average_score(),
            **({"skipped_reports": dashboard.skipped_reports} if dashboard.skipped_reports else {}),
        }


    def operational_summary(self):
        dashboard = self.dashboard()
        execution_history = (
            self.automation_executions.history(
                limit=50
            )
        )

        executions = {
            "total": len(execution_history),
            "successful": sum(
                1
                for execution in execution_history
                if execution["success"]
            ),
            "failed": sum(
                1
                for execution in execution_history
                if not execution["success"]
            ),
            "recent": [
                {
                    "id": execution["id"],
                    "task_id": execution["task_id"],
                    "success": execution["success"],
                    "elapsed": execution["elapsed"],
                    "executed_at": execution["executed_at"],
                }
                for execution in execution_history
            ],
        }

        return {
            "generated": (
                dashboard["generated"]
                if dashboard
                else None
            ),
            "dashboard": (
                {
                    key: dashboard[key]
                    for key in (
                        "hosts",
                        "healthy",
                        "warnings",
                        "critical",
                        "unknown",
                        "average_score",
                    )
                }
                if dashboard
                else None
            ),
            "reports": {
                "current": self.count_files(
                    self.root / "current"
                ),
                "history": self.count_files(
                    self.root / "history"
                ),
                "health": self.count_files(
                    self.root / "health"
                ),
                "discovery": self.count_files(
                    self.root / "discovery"
                ),
                "json": self.count_files(
                    self.root / "json"
                ),
            },
            "executions": executions,
        }


    def files(self):

        reports = []

        if not self.root.exists():

            return reports


        for item in sorted(
            self.root.rglob("*")
        ):

            if item.is_file():

                reports.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": item.suffix.replace(
                            ".",
                            "",
                        ),
                    }
                )


        return reports
