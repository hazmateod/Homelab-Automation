"""
Discovery Importer.

Imports discovery artifacts into the Discovery Repository.
"""

import json
from pathlib import Path

from himp.database.discovery import DiscoveryRepository


class DiscoveryImporter:

    REPORT_DIR = Path("reports/discovery")

    def __init__(self):

        self.repository = DiscoveryRepository()

        self.normalizers = {
            "proxmox": self._normalize_proxmox,
        }

    def import_all(self):

        if not self.REPORT_DIR.exists():
            return

        for artifact in sorted(
            self.REPORT_DIR.glob("*.json")
        ):

            self.import_file(artifact)

    def import_file(
        self,
        artifact,
    ):

        with Path(artifact).open(
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        for plugin, report in data.get(
            "plugins",
            {},
        ).items():

            normalizer = self.normalizers.get(plugin)

            if normalizer is None:
                continue

            hostname, records = normalizer(report)

            self.repository.replace_host(
                plugin,
                hostname,
                records,
            )

    def _normalize_proxmox(
        self,
        report,
    ):

        records = []

        hostname = "unknown"

        for node in report.get(
            "nodes",
            [],
        ):

            hostname = node["node"]

            records.append(
                {
                    "category": "node",
                    "name": node["node"],
                    "value": node["status"],
                }
            )

        return hostname, records
