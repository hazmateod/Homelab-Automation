"""
Dashboard Service.
"""

import socket

from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.inventory import InventoryService
from himp.services.plugins import PluginService


class DashboardService:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.inventory = InventoryService()

        self.health = HealthService()

    def inventory_summary(self):

        inventory = self.inventory.summary()

        return {
            "total_hosts": inventory.total_hosts,
            "groups": inventory.groups,
            "hosts": [
                {
                    "hostname": host.hostname,
                    "group": host.group,
                    "ip": host.ip,
                    "user": host.user,
                    "become": host.become,
                }
                for host in inventory.hosts
            ],
        }

    def health_summary(self):

        summary = self.health.summary()

        return {
            "score": summary.score,
            "passed": summary.passed,
            "warnings": summary.warnings,
            "failed": summary.failed,
            "unknown": summary.unknown,
            "plugins": [
                {
                    "plugin": plugin.plugin,
                    "status": plugin.status.value,
                    "message": plugin.message,
                    "duration_ms": plugin.duration_ms,
                    "details": plugin.details,
                }
                for plugin in summary.plugins
            ],
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

            "inventory": self.inventory_summary(),

            "recent_execution": self.execution.history(10),

            "recent_inventory_changes": self.inventory.changes(10),
        }
