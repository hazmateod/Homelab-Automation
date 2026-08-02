"""
Plugin Registry.
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

        #
        # Pass 1: Exact ID match
        #
        for plugin in self._plugins:

            if plugin.id.lower() == search:
                return plugin

        #
        # Pass 2: Exact display name match
        #
        for plugin in self._plugins:

            if plugin.name.lower() == search:
                return plugin

        #
        # Pass 3: Partial display name match
        #
        matches = [
            plugin
            for plugin in self._plugins
            if search in plugin.name.lower()
        ]

        if len(matches) == 1:
            return matches[0]

        return None
