"""
Status Commands
"""

from pathlib import Path
from himp.models.dashboard import Dashboard

from himp.lib.git import current_branch, is_clean


def run(args):
    dashboard = Path("reports/dashboard/dashboard.json")

    if not dashboard.exists():
        print("Dashboard has not been generated.")
        print("Run: ./bin/himp dashboard")
        return

    dashboard = Dashboard.load()

    print("HIMP Status")
    print("===========")
    print()

    print(f"Generated : {dashboard.generated}")
    print(f"Branch    : {current_branch()}")
    print(f"Git Status: {'Clean' if is_clean() else 'Dirty'}")

    print()

    print(f"Hosts     : {len(dashboard.hosts)}")
    print(f"Healthy   : {dashboard.healthy_count()}")
    print(f"Warning   : {dashboard.warning_count()}")
    print(f"Critical  : {dashboard.critical_count()}")
    print(f"Unknown   : {dashboard.unknown_count()}")


