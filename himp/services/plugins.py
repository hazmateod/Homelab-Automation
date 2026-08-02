"""
Plugin Service.
"""

from himp.health.repository import HealthRepository
from himp.database.discovery import DiscoveryRepository
from himp.plugins.loader import PluginLoader
from himp.services.execution import ExecutionService
from himp.services.validation import ValidationService


class PluginService:

    def __init__(self):

        self.loader = PluginLoader()

        self.validation = ValidationService()

        self.execution = ExecutionService()

        self.health = HealthRepository()

        self.discovery = DiscoveryRepository()

    def all(self):

        return self.loader.plugins()

    def enabled(self):

        return self.loader.enabled()

    def disabled(self):

        return self.loader.disabled()

    def find(self, name):

        return self.loader.find(name)

    def details(self, name):

        plugin = self.find(name)

        if plugin is None:
            return None

        return {
            "plugin": plugin,
            "validation": self.validation.validate(name),
            "health": self.health.plugin(name),
            "executions": [
                execution
                for execution in self.execution.history(50)
                if execution["plugin"] == name
            ],
            "discovery": self.discovery.plugin(name),
        }

    def summary(self):

        return {
            "plugins": len(self.all()),
            "enabled": len(self.enabled()),
            "disabled": len(self.disabled()),
        }
