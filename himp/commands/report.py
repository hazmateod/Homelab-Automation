"""
Reporting Commands
"""

import subprocess


def run(args):
    print("Generating reports...")
    print()

    cmd = [
        "ansible-playbook",
        "-i",
        "inventory/hosts.yml",
        "playbooks/generate_reports.yml",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("Report generation completed successfully.")
    else:
        print()
        print("Report generation failed.")
