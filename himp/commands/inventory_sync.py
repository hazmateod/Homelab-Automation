"""
Scheduled Inventory Sync Command.
"""

import sys

from himp.services.inventory import InventoryService


def run(args):
    service = InventoryService()

    try:
        result = service.sync()
    except Exception as exc:
        print(f"Inventory sync failed: {exc}", file=sys.stderr)
        return 1

    print("Inventory sync completed successfully.")
    print(f"Synced hosts     : {result['synced']}")
    print(f"Active hosts     : {result['active_hosts']}")
    print(f"Total hosts      : {result['total_hosts']}")
    print(f"Recent changes   : {result['recent_changes']}")

    return 0
