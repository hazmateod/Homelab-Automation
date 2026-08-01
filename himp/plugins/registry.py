"""
Plugin Registry
"""

from himp.models.plugin import Plugin


class PluginRegistry:

    VERSION = "1.0"

    def __init__(self):

        self._plugins = []

    @property
    def version(self):
        return self.VERSION

    def register(self, plugin):

        if not isinstance(plugin, Plugin):
            raise TypeError(
                "Only Plugin objects may be registered."
            )

        self._plugins.append(plugin)

    def all(self):

        return self._plugins

    def count(self):

        return len(self._plugins)

    def find(self, name):

        for plugin in self._plugins:

            if plugin.name.lower() == name.lower():
                return plugin

        return None
