"""
Scheduled Inventory Sync Command.
"""

import sys

from himp.database.postgresql import PostgreSQLDatabase
from himp.services.inventory import InventoryService


def run(args):
    try:
        service = InventoryService()

        result = service.sync()

        print(
            "Inventory sync completed successfully."
        )

        print(
            "Synced hosts     : "
            f"{result['synced']}"
        )

        print(
            "Active hosts     : "
            f"{result['active_hosts']}"
        )

        print(
            "Total hosts      : "
            f"{result['total_hosts']}"
        )

        print(
            "Recent changes   : "
            f"{result['recent_changes']}"
        )

        return 0

    except Exception as exc:
        print(
            f"Inventory sync failed: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        PostgreSQLDatabase.close_pools()
