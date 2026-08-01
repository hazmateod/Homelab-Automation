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

        search = name.lower()

        for plugin in self._plugins:

            if plugin.id.lower() == search:
                return plugin

            if plugin.name.lower() == search:
                return plugin

            if search in plugin.name.lower():
                return plugin

        return None
