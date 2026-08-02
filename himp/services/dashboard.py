"""
Dashboard Service.
"""

import socket

from himp.services.execution import ExecutionService
from himp.services.plugins import PluginService
from himp.services.inventory import InventoryService


class DashboardService:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.inventory = InventoryService()

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

            "health": {},

            "inventory": self.inventory_summary(),

            "recent_execution": self.execution.history(10),
        }
