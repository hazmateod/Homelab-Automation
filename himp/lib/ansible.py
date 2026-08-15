"""
Shared Ansible helper functions.
"""

import subprocess
import time
from dataclasses import dataclass

from himp.config import config


@dataclass(frozen=True)
class AnsiblePlaybookResult:
    """Result returned by an Ansible playbook execution."""

    success: bool
    return_code: int
    elapsed: float
    stdout: str
    stderr: str


class AnsiblePlaybookTimeoutError(TimeoutError):
    """Raised when an Ansible playbook exceeds its timeout."""


def run_playbook(
    playbook,
    limit=None,
    timeout=None,
):
    cmd = [
        "ansible-playbook",
        "-i",
        config.inventory,
        playbook,
    ]

    if limit:
        cmd.extend([
            "--limit",
            limit,
        ])

    start = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            check=False,
            timeout=timeout,
            capture_output=True,
            text=True,
        )

    except subprocess.TimeoutExpired as error:
        raise AnsiblePlaybookTimeoutError(
            "Ansible playbook timed out"
        ) from error

    elapsed = time.perf_counter() - start

    return AnsiblePlaybookResult(
        success=result.returncode == 0,
        return_code=result.returncode,
        elapsed=elapsed,
        stdout=result.stdout.strip(),
        stderr=result.stderr.strip(),
    )
