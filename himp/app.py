"""
HIMP Application.
"""

from himp.services.dashboard import DashboardService
from himp.services.execution import ExecutionService
from himp.services.plugins import PluginService


class HIMP:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.dashboard = DashboardService()
