"""
Plugin Execution Engine.
"""

import subprocess
import time

from himp.config import config
from himp.models.execution import Execution
from himp.plugins.loader import PluginLoader


class PluginRunner:

    def __init__(self):

        self.loader = PluginLoader()

    def run(self, name):

        plugin = self.loader.find(name)

        if plugin is None:

            result = Execution(plugin=name)
            result.success = False
            result.return_code = 1
            result.add_warning("Plugin not found.")

            return result

        result = Execution(plugin=plugin.id)

        start = time.perf_counter()

        from himp.database.host_automation_policies import (
            HostAutomationPolicyRepository,
        )

        disabled = HostAutomationPolicyRepository().disabled_hosts()

        command = [
            "ansible-playbook",
            "-i",
            config.inventory,
            "playbooks/run_plugin.yml",
            "-e",
            f"plugin={plugin.id}",
            "-e",
            f"target_group={plugin.inventory_group}",
        ]

        if disabled:
            import re

            for hostname in disabled:
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", hostname):
                    raise ValueError(
                        "Invalid hostname in automation exclusion policy"
                    )

            exclusions = "all" + "".join(
                f":!{hostname}"
                for hostname in sorted(disabled)
            )

            command.extend(["--limit", exclusions])

        process = subprocess.run(
            command,
            check=False,
        )

        result.elapsed = round(
            time.perf_counter() - start,
            3,
        )

        result.return_code = process.returncode

        result.success = (
            process.returncode == 0
        )

        return result
