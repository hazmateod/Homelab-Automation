"""
Discovery Service.
"""

from himp.database.discovery import DiscoveryRepository


class DiscoveryService:

    def __init__(self):

        self.repository = DiscoveryRepository()

    def replace_host(
        self,
        plugin,
        hostname,
        records,
    ):

        self.repository.replace_host(
            plugin,
            hostname,
            records,
        )

    def all(self):

        return self.repository.all()

    def plugin(
        self,
        plugin,
    ):

        return self.repository.plugin(plugin)

    def host(
        self,
        hostname,
    ):

        return self.repository.host(hostname)

    def count(self):

        return self.repository.count()
