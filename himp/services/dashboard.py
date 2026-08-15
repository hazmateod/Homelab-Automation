"""
Dashboard Service.
"""

import socket

from himp.database.remediation_audit import RemediationAuditRepository

from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.health_trends import HealthTrendsService
from himp.services.health_cards import HealthCardsService
from himp.services.host_health_dashboard import HostHealthDashboardService
from himp.services.inventory import InventoryService
from himp.services.plugins import PluginService
from himp.services.scheduler import SchedulerService
from himp.services.workflow_history import WorkflowHistoryService
from himp.services.workflows import WorkflowService


class DashboardService:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.inventory = InventoryService()

        self.health = HealthService()

        self.health_trends = HealthTrendsService()

        self.health_cards = HealthCardsService()
        self.host_health = HostHealthDashboardService()

        self.scheduler = SchedulerService()
        self.remediation_audit = RemediationAuditRepository()

        self.workflows = WorkflowService()
        self.workflow_history = WorkflowHistoryService(
            workflow_service=self.workflows,
        )


    def workflow_summary(self):
        workflows = []

        for workflow in self.workflows.list_workflows():
            history = self.workflow_history.history(
                workflow["id"],
                limit=1,
            )

            latest = history[0] if history else None

            if latest is None:
                status = "NEVER_RUN"
            elif latest["success"] is None:
                status = "RUNNING"
            elif latest["success"]:
                status = "SUCCESS"
            else:
                status = "FAILED"

            workflows.append(
                {
                    "id": workflow["id"],
                    "name": workflow["name"],
                    "description": workflow["description"],
                    "enabled": workflow["enabled"],
                    "status": status,
                    "current_task_id": (
                        latest.get("current_task_id")
                        if latest
                        else None
                    ),
                    "workflow_execution_id": (
                        latest.get("workflow_execution_id")
                        if latest
                        else None
                    ),
                    "started_at": (
                        latest.get("started_at")
                        if latest
                        else None
                    ),
                    "completed_at": (
                        latest.get("completed_at")
                        if latest
                        else None
                    ),
                    "success": (
                        latest.get("success")
                        if latest
                        else None
                    ),
                }
            )

        return workflows


    def automation_summary(self):
        automations = []

        for schedule in self.scheduler.all():
            status = self.scheduler.execution_status(
                schedule["task_id"]
            )

            automations.append(
                {
                    "task_id": schedule["task_id"],
                    "name": schedule["name"],
                    "description": schedule["description"],
                    "enabled": bool(schedule["enabled"]),
                    "frequency": schedule["frequency"],
                    "schedule_time": schedule["schedule_time"],
                    "day_of_week": schedule["day_of_week"],
                    "day_of_month": schedule["day_of_month"],
                    "last_run": schedule["last_run"],
                    "next_run": status["next_run"],
                    "last_execution": status["last_execution"],
                    "last_execution_success": (
                        status["last_execution_success"]
                    ),
                    "last_execution_at": (
                        status["last_execution_at"]
                    ),
                    "last_execution_elapsed": (
                        status["last_execution_elapsed"]
                    ),
                    "last_execution_error": (
                        status["last_execution_error"]
                    ),
                }
            )

        return automations


    def remediation_summary(self):
        return self.remediation_audit.summary()


    def operational_summary(self):
        health = self.host_health.summary()

        health_summary = {
            "score": health.get("score", 0),
            "passed": health.get("passed", 0),
            "warnings": health.get("warnings", 0),
            "failed": health.get("failed", 0),
            "unknown": health.get("unknown", 0),
        }

        workflows = self.workflow_summary()
        automations = self.automation_summary()
        remediation = self.remediation_summary()

        workflow_summary = {
            "total": len(workflows),
            "running": sum(
                workflow["status"] == "RUNNING"
                for workflow in workflows
            ),
            "failed": sum(
                workflow["status"] == "FAILED"
                for workflow in workflows
            ),
            "never_run": sum(
                workflow["status"] == "NEVER_RUN"
                for workflow in workflows
            ),
        }

        automation_summary = {
            "total": len(automations),
            "enabled": sum(
                automation["enabled"]
                for automation in automations
            ),
            "failed": sum(
                automation["last_execution_success"] is False
                for automation in automations
            ),
        }

        has_failure = any(
            (
                health_summary["failed"] > 0,
                workflow_summary["failed"] > 0,
                automation_summary["failed"] > 0,
                remediation["execution_failure_count"] > 0,
            )
        )

        has_warning = any(
            (
                health_summary["warnings"] > 0,
                remediation["confirmation_required_count"] > 0,
            )
        )

        if has_failure:
            status = "FAIL"
        elif has_warning:
            status = "WARNING"
        else:
            status = "PASS"

        return {
            "status": status,
            "health": health_summary,
            "workflows": workflow_summary,
            "automations": automation_summary,
            "remediation": remediation,
        }


    def inventory_summary(self):

        inventory = self.inventory.summary()

        return {
            "total_hosts": inventory.total_hosts,
            "groups": inventory.groups,
            "group_health": [
                {
                    "name": group.name,
                    "hosts": group.hosts,
                    "health_status": group.health_status,
                    "health_earned": group.health_earned,
                    "health_possible": group.health_possible,
                }
                for group in inventory.statistics.group_counts
            ],
            "hosts": [
                {
                    "hostname": host.hostname,
                    "group": host.group,
                    "ip": host.ip,
                    "user": host.user,
                    "become": host.become,
                    "health_status": host.health_status,
                    "health_earned": host.health_earned,
                    "health_possible": host.health_possible,
                }
                for host in inventory.hosts
            ],
        }


    def health_summary(self):

        summary = self.health.summary()

        plugins = []

        for plugin in summary.plugins:

            hosts = []

            if plugin.details:

                raw_hosts = plugin.details.get(
                    "hosts",
                    []
                )

                for host in raw_hosts:

                    health = host.get(
                        "health",
                        {}
                    )

                    hosts.append(
                        {
                            "hostname": host.get(
                                "hostname",
                                "unknown"
                            ),
                            "status": health.get(
                                "status",
                                "UNKNOWN"
                            ),
                            "score": health.get(
                                "earned",
                                0
                            ),
                            "possible": health.get(
                                "possible",
                                0
                            ),
                            "issues": health.get(
                                "issues",
                                []
                            ),
                        }
                    )


            plugins.append(
                {
                    "plugin": plugin.plugin,
                    "status": plugin.status.value,
                    "message": plugin.message,
                    "duration_ms": plugin.duration_ms,
                    "details": plugin.details,
                    "hosts": hosts,
                }
            )


        return {
            "score": summary.score,
            "passed": summary.passed,
            "warnings": summary.warnings,
            "failed": summary.failed,
            "unknown": summary.unknown,
            "plugins": plugins,
        }


    def summary(self):

        plugin_list = []

        for plugin in self.plugins.all():

            latest = self.execution.latest(plugin.id)

            plugin_list.append(
                {
                    "id": plugin.id,
                    "name": plugin.name,
                    "description": plugin.description,
                    "version": plugin.version,
                    "enabled": plugin.enabled,
                    "supports": plugin.supports,
                    "requirements": len(plugin.requirements),
                    "artifacts": len(plugin.artifacts),
                    "latest": latest,
                }
            )


        return {

            "system": {

                "hostname": socket.gethostname(),

                "version": "1.0.0",
            },

            "plugins": self.plugins.summary(),

            "plugin_list": plugin_list,

            "health": self.health_summary(),

            "health_trends": self.health_trends.summary(),

            "health_cards": self.health_cards.summary(),
            "host_health": self.host_health.summary(),

            "workflows": self.workflow_summary(),

            "automations": self.automation_summary(),

            "remediation": self.remediation_summary(),

            "inventory": self.inventory_summary(),

            "recent_execution": self.execution.history(10),

            "recent_inventory_changes": self.inventory.changes(10),

        }
