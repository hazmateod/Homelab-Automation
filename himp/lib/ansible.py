"""
Shared Ansible helper functions.
"""

import subprocess
import time

from himp.config import config


def run_playbook(playbook, limit=None):
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

    result = subprocess.run(
        cmd,
        check=False,
    )

    elapsed = time.perf_counter() - start

    return (
        result.returncode == 0,
        elapsed,
    )
