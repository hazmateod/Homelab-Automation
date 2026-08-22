"""
Host Storage Capacity Intelligence.

Collects filesystem capacity through the existing Ansible execution boundary,
normalizes usage, persists history, and emits threshold state transitions.
"""

import json
from pathlib import Path

from himp.database.inventory import InventoryRepository
from himp.database.storage_capacity import (
    StorageCapacityRepository,
)
from himp.lib.ansible import run_playbook


class StorageCapacityCollector:

    ARTIFACT = Path(
        "reports/storage/capacity.json"
    )

    def collect(
        self,
        timeout=None,
    ):
        result = run_playbook(
            "playbooks/storage_capacity.yml",
            timeout=timeout,
        )

        if not result.success:
            message = (
                result.stderr
                or result.stdout
                or (
                    "Storage capacity collection "
                    f"failed with return code {result.return_code}."
                )
            )

            raise RuntimeError(message)

        if not self.ARTIFACT.exists():
            raise RuntimeError(
                "Storage capacity artifact was not generated."
            )

        data = json.loads(
            self.ARTIFACT.read_text(
                encoding="utf-8"
            )
        )

        return data.get(
            "hosts",
            [],
        )


class StorageCapacityService:

    WARNING_PERCENT = 80.0
    CRITICAL_PERCENT = 90.0

    SEVERITY = {
        "UNKNOWN": -1,
        "PASS": 0,
        "WARNING": 1,
        "CRITICAL": 2,
    }

    def __init__(
        self,
        repository=None,
        inventory=None,
        collector=None,
        notifications=None,
    ):
        self.repository = (
            repository
            or StorageCapacityRepository()
        )
        self.inventory = (
            inventory
            or InventoryRepository()
        )
        self.collector = (
            collector
            or StorageCapacityCollector()
        )
        self.notifications = notifications

    @classmethod
    def status_for(
        cls,
        used_percent,
    ):
        used_percent = float(
            used_percent
        )

        if used_percent >= cls.CRITICAL_PERCENT:
            return "CRITICAL"

        if used_percent >= cls.WARNING_PERCENT:
            return "WARNING"

        return "PASS"

    @staticmethod
    def _parse_host(
        host,
    ):
        hostname = host.get(
            "hostname"
        )

        lines = host.get(
            "stdout_lines",
            [],
        )

        if (
            not hostname
            or len(lines) <= 1
        ):
            return []

        records = []

        for line in lines[1:]:
            parts = line.split(
                None,
                5,
            )

            if len(parts) != 6:
                continue

            (
                filesystem,
                total,
                used,
                available,
                percent,
                mount_point,
            ) = parts

            try:
                total_bytes = int(total)
                used_bytes = int(used)
                available_bytes = int(
                    available
                )
                used_percent = float(
                    percent.rstrip("%")
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            records.append(
                {
                    "hostname": hostname,
                    "filesystem": filesystem,
                    "mount_point": mount_point,
                    "total_bytes": total_bytes,
                    "used_bytes": used_bytes,
                    "available_bytes": (
                        available_bytes
                    ),
                    "used_percent": used_percent,
                }
            )

        return records

    def collect_all(
        self,
        timeout=None,
    ):
        active_hosts = {
            host["hostname"]
            for host in self.inventory.all_hosts()
        }

        collected = (
            self.collector.collect(
                timeout=timeout
            )
        )

        records = []
        transitions = []

        for host in collected:
            hostname = host.get(
                "hostname"
            )

            if hostname not in active_hosts:
                continue

            for record in self._parse_host(
                host
            ):
                record["status"] = (
                    self.status_for(
                        record[
                            "used_percent"
                        ]
                    )
                )

                transition = (
                    self.repository.save(
                        record
                    )
                )

                records.append(
                    record
                )

                if transition[
                    "transition"
                ]:
                    transition_record = {
                        **record,
                        **transition,
                    }

                    transitions.append(
                        transition_record
                    )

                    if self.notifications is not None:
                        self.notifications.storage_transition(
                            transition_record
                        )

        return {
            "success": True,
            "hosts": len(
                {
                    record["hostname"]
                    for record in records
                }
            ),
            "filesystems": len(records),
            "warning": sum(
                record["status"] == "WARNING"
                for record in records
            ),
            "critical": sum(
                record["status"] == "CRITICAL"
                for record in records
            ),
            "transitions": transitions,
        }

    @staticmethod
    def _human_bytes(
        value,
    ):
        value = float(
            value
        )

        units = (
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB",
            "PiB",
        )

        for unit in units:
            if (
                abs(value) < 1024.0
                or unit == units[-1]
            ):
                if unit == "B":
                    return f"{int(value)} {unit}"

                return (
                    f"{value:.1f} {unit}"
                )

            value /= 1024.0

        return f"{value:.1f} PiB"

    def _decorate(
        self,
        record,
    ):
        return {
            **record,
            "total_display": (
                self._human_bytes(
                    record["total_bytes"]
                )
            ),
            "used_display": (
                self._human_bytes(
                    record["used_bytes"]
                )
            ),
            "available_display": (
                self._human_bytes(
                    record[
                        "available_bytes"
                    ]
                )
            ),
        }

    def host(
        self,
        hostname,
    ):
        host = self.inventory.find_host(
            hostname
        )

        if host is None:
            raise ValueError(
                "Inventory host not found: "
                f"{hostname}"
            )

        filesystems = [
            self._decorate(record)
            for record in (
                self.repository.current_host(
                    hostname
                )
            )
        ]

        status = "UNKNOWN"
        highest_percent = None

        if filesystems:
            status = max(
                (
                    record["status"]
                    for record in filesystems
                ),
                key=lambda item: (
                    self.SEVERITY[item]
                ),
            )

            highest_percent = max(
                record["used_percent"]
                for record in filesystems
            )

        return {
            "hostname": hostname,
            "status": status,
            "highest_used_percent": (
                highest_percent
            ),
            "warning_threshold": (
                self.WARNING_PERCENT
            ),
            "critical_threshold": (
                self.CRITICAL_PERCENT
            ),
            "filesystems": filesystems,
            "alerts": (
                self.repository.alert_events(
                    hostname=hostname,
                    limit=25,
                )
            ),
        }

    def summary(self):
        current = (
            self.repository.current_all()
        )

        by_host = {
            host["hostname"]: []
            for host in self.inventory.all_hosts()
        }

        for record in current:
            if record["hostname"] in by_host:
                by_host[
                    record["hostname"]
                ].append(record)

        hosts = []

        for hostname in sorted(
            by_host
        ):
            filesystems = by_host[
                hostname
            ]

            if filesystems:
                status = max(
                    (
                        record["status"]
                        for record in filesystems
                    ),
                    key=lambda item: (
                        self.SEVERITY[item]
                    ),
                )

                highest = max(
                    record["used_percent"]
                    for record in filesystems
                )
            else:
                status = "UNKNOWN"
                highest = None

            hosts.append(
                {
                    "hostname": hostname,
                    "status": status,
                    "highest_used_percent": (
                        highest
                    ),
                    "filesystem_count": len(
                        filesystems
                    ),
                    "filesystems": [
                        self._decorate(
                            record
                        )
                        for record in sorted(
                            filesystems,
                            key=lambda item: (
                                item["mount_point"]
                            ),
                        )
                    ],
                }
            )

        return {
            "warning_threshold": (
                self.WARNING_PERCENT
            ),
            "critical_threshold": (
                self.CRITICAL_PERCENT
            ),
            "hosts": hosts,
            "warning_hosts": sum(
                host["status"] == "WARNING"
                for host in hosts
            ),
            "critical_hosts": sum(
                host["status"] == "CRITICAL"
                for host in hosts
            ),
            "unknown_hosts": sum(
                host["status"] == "UNKNOWN"
                for host in hosts
            ),
        }
