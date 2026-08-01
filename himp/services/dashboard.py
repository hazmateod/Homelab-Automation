"""
Dashboard Service.
"""

import socket

from himp.services.execution import ExecutionService
from himp.services.plugins import PluginService


class DashboardService:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

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

            "inventory": {},

            "recent_execution": self.execution.history(10),
        }
