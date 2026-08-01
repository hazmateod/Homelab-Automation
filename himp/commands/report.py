"""
Reporting Commands
"""

from himp.lib.ansible import run_playbook


def run(args):
    print("Generating reports...")
    print()

    result = run_playbook(
        "playbooks/generate_reports.yml",
        "inventory/hosts.yml",
        args.limit,
    )

    if result.returncode == 0:
        print()
        print("Report generation completed successfully.")
    else:
        print()
        print("Report generation failed.")
