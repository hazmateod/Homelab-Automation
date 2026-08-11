"""
Shared Ansible helper functions.
"""

import subprocess
import time

from himp.config import config


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
        )

        success = result.returncode == 0

    except subprocess.TimeoutExpired:
        success = False

    elapsed = time.perf_counter() - start

    return (
        success,
        elapsed,
    )
