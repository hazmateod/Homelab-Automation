"""
Plugin Manager
"""

from himp.models.plugin import Plugin


class PluginManager:

    def __init__(self):

        self.plugins = [
            Plugin(
                name="Proxmox",
                version="1.0",
                description="Proxmox VE Plugin",
            ),
            Plugin(
                name="PBS",
                version="1.0",
                description="Proxmox Backup Server Plugin",
            ),
            Plugin(
                name="Technitium",
                version="1.0",
                description="Technitium DNS Plugin",
            ),
            Plugin(
                name="Unbound",
                version="1.0",
                description="Unbound DNS Plugin",
            ),
        ]

    def all(self):
        return self.plugins

    def find(self, name):

        for plugin in self.plugins:

            if plugin.name.lower() == name.lower():
                return plugin

        return None

    def enabled(self):

        return [
            plugin
            for plugin in self.plugins
            if plugin.is_enabled()
        ]

    def disabled(self):

        return [
            plugin
            for plugin in self.plugins
            if not plugin.is_enabled()
        ]
