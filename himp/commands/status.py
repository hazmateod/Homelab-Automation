"""
Status Commands.
"""

from himp.lib.git import current_branch, is_clean
from himp.services.dashboard import DashboardService


def run(args):

    dashboard = DashboardService().summary()

    print("HIMP Status")
    print("===========")
    print()

    print(f"Hostname  : {dashboard['system']['hostname']}")
    print(f"Version   : {dashboard['system']['version']}")
    print(f"Branch    : {current_branch()}")
    print(f"Git Status: {'Clean' if is_clean() else 'Dirty'}")

    print()

    print("Plugins")
    print("-------")
    print(f"Installed : {dashboard['plugins']['plugins']}")
    print(f"Enabled   : {dashboard['plugins']['enabled']}")
    print(f"Disabled  : {dashboard['plugins']['disabled']}")

    print()

    print("Inventory")
    print("---------")
    print(f"Hosts     : {dashboard['inventory']['total_hosts']}")
    print(f"Groups    : {dashboard['inventory']['groups']}")

    print()

    print("Health")
    print("------")
    print(f"Score     : {dashboard['health']['score']}")
    print(f"Passed    : {dashboard['health']['passed']}")
    print(f"Warnings  : {dashboard['health']['warnings']}")
    print(f"Failed    : {dashboard['health']['failed']}")
    print(f"Unknown   : {dashboard['health']['unknown']}")

    print()

    print(f"Recent Inventory Changes : {len(dashboard['recent_inventory_changes'])}")
    print(f"Recent Executions        : {len(dashboard['recent_execution'])}")
