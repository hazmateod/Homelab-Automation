"""
Execution Service.
"""

from himp.database.executions import ExecutionRepository
from himp.plugins.loader import PluginLoader
from himp.sdk.runner import PluginRunner


class ExecutionService:

    def __init__(self):

        self.runner = PluginRunner()

        self.repository = ExecutionRepository()

        self.loader = PluginLoader()

    def run(self, plugin):

        execution = self.runner.run(plugin)

        self.repository.save(execution)

        return execution

    def latest(self, plugin):

        return self.repository.latest(plugin)

    def history(self, limit=50):

        history = self.repository.history(limit)

        for execution in history:

            plugin = self.loader.find(execution["plugin"])

            if plugin:

                execution["plugin_name"] = plugin.name

            else:

                execution["plugin_name"] = execution["plugin"]

        return history
