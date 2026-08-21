"""
HIMP Configuration
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    inventory: str
    dashboard: str
    maintenance_playbook: str
    report_playbook: str
    dashboard_playbook: str
    infrastructure_relationships: str

    def validate(self):

        required = [
            self.inventory,
            self.dashboard,
            self.maintenance_playbook,
            self.report_playbook,
            self.dashboard_playbook,
            self.infrastructure_relationships,
        ]

        for filename in required:
            if not Path(filename).exists():
                raise FileNotFoundError(filename)


def load():

    config = Config(
        inventory="inventory/hosts.yml",
        dashboard="reports/dashboard/dashboard.json",
        maintenance_playbook="playbooks/maintenance.yml",
        report_playbook="playbooks/generate_reports.yml",
        dashboard_playbook="playbooks/dashboard.yml",
        infrastructure_relationships=(
            "config/infrastructure_relationships.yml"
        ),
    )

    config.validate()

    return config


config = load()
