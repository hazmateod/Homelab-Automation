"""
HIMP Application.
"""
import logging

from himp.services.application_health import ApplicationHealthService
from himp.services.automation import AutomationService
from himp.services.dashboard import DashboardService
from himp.services.discovery import DiscoveryService
from himp.services.execution import ExecutionService
from himp.services.health import HealthService
from himp.services.health_history import HealthHistoryService
from himp.services.health_trends import HealthTrendsService
from himp.services.inventory import InventoryService
from himp.services.notifications import NotificationService
from himp.services.operator_guidance import OperatorGuidanceService
from himp.services.plugins import PluginService
from himp.services.reports import ReportService
from himp.services.settings import SettingsService
from himp.services.storage_capacity import StorageCapacityService
from himp.services.validation import ValidationService
from himp.services.update import UpdateService
from himp.services.user_management import UserManagementService


logger = logging.getLogger("himp")


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

        self.settings = SettingsService()

        self.notifications = NotificationService()

        self.operator_guidance = OperatorGuidanceService()

        self.storage = StorageCapacityService(
            notifications=self.notifications,
        )

        self.updates = UpdateService()
        self.user_management = UserManagementService()

        self.automation = AutomationService()

        self.application_health = ApplicationHealthService(
            automation=self.automation,
            settings=self.settings,
        )

        self.automation.configure(
            self.health,
            self.reports,
            self.inventory,
            self.updates,
            self.dashboard.host_health.health,
            self.storage,
        )

        logger.info("HIMP application initialized")
