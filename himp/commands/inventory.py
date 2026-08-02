"""
Inventory Commands.
"""

from himp.lib.output import error
from himp.services.inventory import InventoryService


def run(args):

    service = InventoryService()

    records = service.all_hosts()

    if args.hostname:

        host = service.find_host(args.hostname)

        if host is None:

            error(f"Host '{args.hostname}' not found.")

            return

        print(f"Hostname : {host['hostname']}")
        print(f"Group    : {host['group_name']}")
        print(f"IP       : {host['ip']}")
        print(f"User     : {host['ansible_user']}")
        print(f"Become   : {bool(host['become'])}")

        return

    if args.status:

        print(
            "Filtering by status is not yet supported "
            "by the live inventory."
        )

        return

    print(
        f"{'Hostname':<20} "
        f"{'Group':<15} "
        f"{'IP Address':<16} "
        f"{'User':<10} "
        f"{'Become'}"
    )

    print("-" * 76)

    for host in sorted(
        records,
        key=lambda h: h["hostname"].lower(),
    ):

        print(
            f"{host['hostname']:<20} "
            f"{host['group_name']:<15} "
            f"{host['ip']:<16} "
            f"{host['ansible_user']:<10} "
            f"{bool(host['become'])}"
        )
