"""
Status Commands
"""

from pathlib import Path
import json


def run(args):
    dashboard = Path("reports/dashboard/dashboard.json")

    if not dashboard.exists():
        print("Dashboard has not been generated.")
        print("Run: ./bin/himp dashboard")
        return

    with dashboard.open() as f:
        data = json.load(f)

    healthy = 0
    warning = 0
    critical = 0

    for host in data["hosts"]:

        status = host["status"]

        if status == "HEALTHY":
            healthy += 1
        elif status == "WARNING":
            warning += 1
        elif status == "CRITICAL":
            critical += 1

    print("HIMP Status")
    print("===========")
    print()

    print(f"Generated : {data['generated']}")
    print(f"Hosts     : {data['host_count']}")
    print(f"Healthy   : {healthy}")
    print(f"Warning   : {warning}")
    print(f"Critical  : {critical}")
