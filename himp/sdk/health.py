"""
Plugin Health Engine.
"""

from pathlib import Path
import subprocess
import time

from himp.config import config
from himp.models.execution import Execution
from himp.plugins.loader import PluginLoader


class PluginHealthRunner:

    REPORT_DIR = Path("reports/health")

    def __init__(self):

        self.loader = PluginLoader()

    def health(self, name):

        plugin = self.loader.find(name)

        if plugin is None:

            result = Execution(plugin=name)
            result.success = False
            result.return_code = 1
            result.add_warning("Plugin not found.")

            return result

        result = Execution(plugin=plugin.id)

        start = time.perf_counter()

        process = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                config.inventory,
                "playbooks/run_health.yml",
                "-e",
                f"plugin={plugin.id}",
                "-e",
                f"inventory_group={plugin.inventory_group}",
            ],
            check=False,
        )

        result.elapsed = round(
            time.perf_counter() - start,
            3,
        )

        result.return_code = process.returncode
        result.success = process.returncode == 0

        report = self.REPORT_DIR / f"{plugin.id}.json"

        if report.exists():
            result.add_artifact(str(report))

        return result

    def health_all(self):

        return [
            self.health(plugin.id)
            for plugin in self.loader.plugins()
            if plugin.supports_health()
        ]
