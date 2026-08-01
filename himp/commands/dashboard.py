"""
Dashboard Commands
"""

from himp.lib.ansible import run_playbook


def run(args):
    print("Generating dashboard...")
    print()

    result = run_playbook(
        "playbooks/dashboard.yml",
    )

    if result.returncode == 0:
        print()
        print("Dashboard generation completed successfully.")
    else:
        print()
        print("Dashboard generation failed.")
