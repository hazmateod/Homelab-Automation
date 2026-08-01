"""
Plugin Loader
"""

from himp.plugins.registry import PluginRegistry
from himp.sdk.loader import SDKLoader


class PluginLoader:

    def __init__(self):

        self.registry = PluginRegistry()
        self.sdk = SDKLoader()

        self.load_plugins()

    def load_plugins(self):

        for plugin in self.sdk.plugins():
            self.registry.register(plugin)

    def plugins(self):
        return self.registry.all()

    def find(self, name):
        return self.registry.find(name)

    def enabled(self):

        return [
            plugin
            for plugin in self.registry.all()
            if plugin.is_enabled()
        ]

    def disabled(self):

        return [
            plugin
            for plugin in self.registry.all()
            if not plugin.is_enabled()
        ]
