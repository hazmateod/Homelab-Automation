"""
Plugin Health Engine.
"""

import json
import os
from pathlib import Path
import subprocess
import time
from tempfile import TemporaryDirectory
from uuid import uuid4

from himp.config import config
from himp.database.host_identity import HostIdentityRepository
from himp.health.attempts import HealthAttempts
from himp.health.parser import HealthArtifactParser
from himp.models.execution import Execution
from himp.plugins.loader import PluginLoader


TECHNITIUM_SSH_OPTIONS = (
    "-o StrictHostKeyChecking=yes -o UpdateHostKeys=no "
    "-o ControlMaster=no -o ControlPath=none -o BatchMode=yes"
)


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

        attempts = HealthAttempts(self.REPORT_DIR)
        attempts.start(plugin.id, result.health_attempt_id)
        destination = self.REPORT_DIR / f"{plugin.id}.json"
        with TemporaryDirectory(dir=self.REPORT_DIR) as directory:
            artifact = Path(directory).resolve() / destination.name
            command.extend(["-e", json.dumps({"himp_health_output": str(artifact)})])
            failure = None
            try:
                options = {}
                if plugin.id == "technitium":
                    command.extend(["-e", json.dumps({
                        "ansible_host_key_checking": True,
                        "ansible_ssh_host_key_checking": True,
                        "ansible_ssh_args": TECHNITIUM_SSH_OPTIONS,
                        "himp_require_technitium_ssh": True,
                    })])
                    options["env"] = {**os.environ, "LC_ALL": "C"}
                process = subprocess.run(command, check=False, timeout=timeout, **options)
                result.return_code = process.returncode
                if process.returncode:
                    failure = "execution_failed"
            except subprocess.TimeoutExpired:
                result.return_code = 124
                failure = "timeout"
            except OSError:
                failure = "runner_unavailable"

            if failure is None:
                if not artifact.is_file():
                    failure = "artifact_missing"
                else:
                    try:
                        report = HealthArtifactParser().parse(artifact)
                        if (
                            report is None or report.summary.plugin != plugin.id
                            or report.metadata.data.get("attempt_id") != result.health_attempt_id
                        ):
                            failure = "artifact_invalid"
                    except (OSError, ValueError, TypeError, AttributeError, RecursionError):
                        failure = "artifact_invalid"

            failure = attempts.finish(
                plugin.id, result.health_attempt_id, failure,
                None if failure else artifact, destination,
            )
        result.elapsed = round(time.perf_counter() - start, 3)
        result.success = failure is None
        if result.success:
            result.add_artifact(str(destination))
        else:
            result.return_code = result.return_code or 1
            result.add_warning(f"Health collection failed: {failure}.")

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
