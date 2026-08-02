"""
Inventory dashboard models.
"""

from dataclasses import dataclass


@dataclass
class InventoryHost:

    hostname: str

    group: str

    ip: str

    user: str

    become: bool


@dataclass
class InventorySummary:

    total_hosts: int

    groups: int

    hosts: list
