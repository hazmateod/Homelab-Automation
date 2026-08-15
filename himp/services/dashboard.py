"""
Dashboard Service.
"""

import socket

from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.health_trends import HealthTrendsService
from himp.services.health_cards import HealthCardsService
from himp.services.host_health_dashboard import HostHealthDashboardService
from himp.services.inventory import InventoryService
from himp.services.plugins import PluginService
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

            "inventory": self.inventory_summary(),

            "recent_execution": self.execution.history(10),

            "recent_inventory_changes": self.inventory.changes(10),

        }
