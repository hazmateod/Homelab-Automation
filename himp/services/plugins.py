"""
Plugin Service.
"""

from himp.plugins.loader import PluginLoader


class PluginService:

    def __init__(self):

        self.loader = PluginLoader()

    def all(self):

        return self.loader.plugins()

    def enabled(self):

        return self.loader.enabled()

    def disabled(self):

        return self.loader.disabled()

    def find(self, name):

        return self.loader.find(name)

    def summary(self):

        return {
            "plugins": len(self.all()),
            "enabled": len(self.enabled()),
            "disabled": len(self.disabled()),
        }
