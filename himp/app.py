"""
HIMP Application.
"""

from himp.services.dashboard import DashboardService
from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.plugins import PluginService
from himp.services.validation import ValidationService


class HIMP:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.validation = ValidationService()

        self.dashboard = DashboardService()

        self.health = HealthService()
