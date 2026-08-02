"""
HIMP Application.
"""

from himp.services.dashboard import DashboardService
from himp.services.discovery import DiscoveryService
from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.health_history import HealthHistoryService
from himp.services.health_trends import HealthTrendsService
from himp.services.inventory import InventoryService
from himp.services.plugins import PluginService
from himp.services.reports import ReportService
from himp.services.validation import ValidationService


class HIMP:

    def __init__(self):

        self.plugins = PluginService()

        self.execution = ExecutionService()

        self.validation = ValidationService()

        self.dashboard = DashboardService()

        self.inventory = InventoryService()

        self.discovery = DiscoveryService()

        self.health = HealthService()

        self.health_history = HealthHistoryService()

        self.health_trends = HealthTrendsService()

        self.reports = ReportService()
