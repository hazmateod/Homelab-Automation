"""
Settings Service.

Provides HIMP configuration and runtime settings information.
"""

import platform
import socket
from pathlib import Path

from himp.config import config


class SettingsService:

    def summary(self):

        return {
            "application": {
                "name": "HIMP",
                "version": "1.0.0",
            },
            "system": self.system(),
            "paths": self.paths(),
            "configuration": self.configuration(),
        }


    def system(self):

        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        }


    def paths(self):

        return {
            "inventory": self.exists(config.inventory),
            "dashboard": self.exists(config.dashboard),
            "maintenance_playbook": self.exists(
                config.maintenance_playbook
            ),
            "report_playbook": self.exists(
                config.report_playbook
            ),
            "dashboard_playbook": self.exists(
                config.dashboard_playbook
            ),
        }


    def configuration(self):

        return {
            "inventory": config.inventory,
            "dashboard": config.dashboard,
            "maintenance_playbook": config.maintenance_playbook,
            "report_playbook": config.report_playbook,
            "dashboard_playbook": config.dashboard_playbook,
        }


    def exists(self, filename):

        return {
            "path": filename,
            "exists": Path(filename).exists(),
        }
