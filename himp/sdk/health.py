"""
Plugin Health Engine.
"""

import json
from pathlib import Path
import subprocess
import time
from uuid import uuid4

from himp.config import config
from himp.database.host_identity import HostIdentityRepository
from himp.models.execution import Execution
from himp.plugins.loader import PluginLoader


class PluginHealthRunner:

    REPORT_DIR = Path("reports/health")

    def __init__(self):

        self.loader = PluginLoader()

    def health(
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

        result = Execution(plugin=plugin.id)

        result.health_attempt_id = uuid4().hex
        start = time.perf_counter()
        bindings = HostIdentityRepository().execution_bindings()
        identity_options = (
            ["--extra-vars", json.dumps({"himp_host_bindings": bindings})]
            if bindings else []
        )

        from himp.database.host_automation_policies import (
            HostAutomationPolicyRepository,
        )
        import re

        disabled = HostAutomationPolicyRepository().disabled_hosts()

        command = [
            "ansible-playbook",
            "-i",
            config.inventory,
            "playbooks/run_health.yml",
            "-e",
            f"plugin={plugin.id}",
            "-e",
            f"inventory_group={plugin.inventory_group}",
            "-e",
            f"himp_health_attempt_id={result.health_attempt_id}",
            *identity_options,
        ]

        if disabled:
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

        try:
            process = subprocess.run(command, check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            result.return_code = 124
            result.add_warning("Health collection timed out.")
        else:
            result.return_code = process.returncode
            result.success = process.returncode == 0
        result.elapsed = round(time.perf_counter() - start, 3)

        if result.success:
            report = self.REPORT_DIR / f"{plugin.id}.json"
            try:
                document = json.loads(report.read_text(encoding="utf-8"))
            except (OSError, ValueError, RecursionError):
                document = None
            if isinstance(document, dict) and document.get("attempt_id") == result.health_attempt_id:
                result.add_artifact(str(report))
            else:
                result.success = False
                result.return_code = 1
                result.add_warning("Health collection did not publish a report for this attempt.")

        return result

    def health_all(
        self,
        timeout=None,
    ):

        return [
            self.health(
                plugin.id,
                timeout=timeout,
            )
            for plugin in self.loader.plugins()
            if plugin.supports_health()
        ]
