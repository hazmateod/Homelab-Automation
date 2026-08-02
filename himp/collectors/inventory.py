"""
Inventory Collector.

Collects infrastructure inventory data from Ansible inventory.
"""

from __future__ import annotations

import yaml

from himp.config import config


class InventoryCollector:
    """
    Collects inventory information.
    """

    def load_inventory(self):

        with open(config.inventory) as file:

            return yaml.safe_load(file)

    def groups(self):

        inventory = self.load_inventory()

        return inventory.get(
            "all",
            {}
        ).get(
            "children",
            {}
        )

    def hosts(self):

        results = []

        for group, data in self.groups().items():

            hosts = data.get(
                "hosts",
                {}
            )

            for hostname, details in hosts.items():

                results.append(
                    {
                        "hostname": hostname,
                        "group": group,
                        "ip": details.get(
                            "ansible_host"
                        ),
                        "user": details.get(
                            "ansible_user"
                        ),
                        "become": details.get(
                            "ansible_become",
                            False,
                        ),
                    }
                )

        return results

    def find_host(
        self,
        hostname: str,
    ):

        for host in self.hosts():

            if host["hostname"] == hostname:

                return host

        return None

    def summary(self):

        hosts = self.hosts()

        groups = self.groups()

        return {
            "inventory": config.inventory,
            "group_count": len(groups),
            "host_count": len(hosts),
            "hosts": hosts,
        }
