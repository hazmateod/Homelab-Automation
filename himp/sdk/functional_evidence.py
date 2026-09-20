"""
Plugin Functional Evidence Engine.

Executes plugin-specific functional evidence collectors and records
their raw evidence artifact.

Interpretation, freshness evaluation, service redundancy, failover,
and remediation remain outside this runner.
"""

from pathlib import Path
import subprocess
import time

from himp.config import config
from himp.models.execution import Execution
from himp.plugins.loader import PluginLoader


class PluginFunctionalEvidenceRunner:

    REPORT_DIR = Path(
        "reports/functional_evidence"
    )

    def __init__(self):

        self.loader = PluginLoader()

    def collect(
        self,
        name,
        timeout=None,
    ):

        plugin = self.loader.find(name)

        if plugin is None:

            result = Execution(plugin=name)
            result.success = False
            result.return_code = 1
            result.add_warning("Plugin not found.")

            return result

        if not plugin.functional_evidence_ready():

            result = Execution(plugin=plugin.id)
            result.success = False
            result.return_code = 1
            result.add_warning(
                "Plugin functional evidence "
                "collector is not ready."
            )

            return result

        result = Execution(plugin=plugin.id)

        start = time.perf_counter()

        process = subprocess.run(
            [
                "ansible-playbook",
                "-i",
                config.inventory,
                "playbooks/run_functional_evidence.yml",
                "-e",
                f"plugin={plugin.id}",
                "-e",
                (
                    "inventory_group="
                    f"{plugin.inventory_group}"
                ),
            ],
            check=False,
            timeout=timeout,
        )

        result.elapsed = round(
            time.perf_counter() - start,
            3,
        )

        result.return_code = process.returncode
        result.success = process.returncode == 0

        report = (
            self.REPORT_DIR
            / f"{plugin.id}.json"
        )

        if report.exists():
            result.add_artifact(str(report))

        return result

    def collect_all(
        self,
        timeout=None,
    ):

        return [
            self.collect(
                plugin.id,
                timeout=timeout,
            )
            for plugin in self.loader.plugins()
            if plugin.functional_evidence_ready()
        ]
