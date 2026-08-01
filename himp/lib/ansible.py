"""
Shared Ansible helper functions.
"""

import subprocess


def run_playbook(playbook, inventory=None, limit=None):
    cmd = ["ansible-playbook"]

    if inventory:
        cmd.extend(["-i", inventory])

    if limit:
        cmd.extend(["--limit", limit])

    cmd.append(playbook)

    return subprocess.run(cmd)
