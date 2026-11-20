"""
Report Service.

Provides report inventory and dashboard report information.
"""

from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from himp.config import config
from himp.database.automation_executions import AutomationExecutionRepository
from himp.database.automation_target_plans import AutomationTargetPlanRepository
from himp.database.inventory import InventoryRepository
from himp.lib.ansible import run_playbook
from himp.services.host_maintenance_eligibility import (
    HostMaintenanceEligibility,
    fingerprint_host,
    literal_host_pattern,
)
from himp.models.dashboard import Dashboard


class ReportTargetChangedError(ValueError):
    """The recorded report target cannot be proven safe to retry."""


class ReportService:

    def __init__(self):

        self.root = Path("reports")
        self.automation_executions = (
            AutomationExecutionRepository()
        )


    def generate(self, limit=None, timeout=None, *, expected_target_plan_id=None):
        if not limit or not literal_host_pattern(limit, {}):
            if expected_target_plan_id is not None:
                raise ReportTargetChangedError("Report retry requires one verified host")
            return self._run_report(limit, timeout)

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
                return self._run_report(limit, timeout)
            row = InventoryRepository().find_host(limit)
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
            plans = AutomationTargetPlanRepository()
            if expected_target_plan_id is not None and plans.find(expected_target_plan_id) != plan:
                raise ReportTargetChangedError("The report inventory or host identity has changed")
            if source.with_name(f".{source.name}.pending").exists() or source.read_bytes() != contents:
                raise ReportTargetChangedError("Inventory changed while preparing the report")
            plan_id = plans.save(plan)
            try:
                return {
                    **self._run_report(limit, timeout, inventory_path=snapshot.name),
                    "target_plan_id": plan_id,
                }
            except Exception as error:
                error.target_plan_id = plan_id
                raise

    @staticmethod
    def _run_report(limit, timeout, *, inventory_path=None):
        options = {"timeout": timeout}
        if inventory_path is not None:
            options["inventory_path"] = inventory_path
        result = run_playbook(config.report_playbook, limit, **options)
        return {"success": result.success, "elapsed": result.elapsed}


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
            str(filename)
        )

        return {
            "generated": dashboard.generated,
            "hosts": len(dashboard.hosts),
            "healthy": dashboard.healthy_count(),
            "warnings": dashboard.warning_count(),
            "critical": dashboard.critical_count(),
            "unknown": dashboard.unknown_count(),
            "average_score": dashboard.average_score(),
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
