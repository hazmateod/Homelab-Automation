"""
Dashboard Commands
"""

import subprocess


def run(args):
    print("Generating dashboard...")
    print()

    cmd = [
        "ansible-playbook",
        "playbooks/dashboard.yml",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("Dashboard generation completed successfully.")
    else:
        print()
        print("Dashboard generation failed.")
