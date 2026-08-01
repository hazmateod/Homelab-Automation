"""
Inventory Commands
"""

from himp.models.dashboard import Dashboard
from himp.lib.output import error


def run(args):

    dashboard = Dashboard.load()

    if args.hostname:

        host = dashboard.find_host(args.hostname)

        if host is None:
            error(f"Host '{args.hostname}' not found.")
            return

        print(f"Hostname : {host.hostname}")
        print(f"IP       : {host.ip}")
        print(f"OS       : {host.os}")
        print(f"Kernel   : {host.kernel}")
        print(f"Score    : {host.score}")
        print(f"Status   : {host.status}")
        return

    if args.status:
        hosts = dashboard.hosts_by_status(args.status)
    else:
        hosts = sorted(
            dashboard.hosts,
            key=lambda h: h.hostname.lower(),
        )

    print(f"{'Hostname':<20} {'IP Address':<16} {'Status':<10} {'Score':>5}")
    print("-" * 58)

    for host in hosts:
        print(
            f"{host.hostname:<20} "
            f"{host.ip:<16} "
            f"{host.status:<10} "
            f"{host.score:>5}"
        )
