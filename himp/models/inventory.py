"""
Inventory dashboard models.
"""

from dataclasses import dataclass, field


@dataclass
class InventoryHost:
    hostname: str
    group: str
    ip: str
    user: str
    become: bool
    health_status: str = "UNKNOWN"
    health_earned: int = 0
    health_possible: int = 0


@dataclass
class InventoryGroup:
    name: str
    hosts: int
    health_status: str = "UNKNOWN"
    health_earned: int = 0
    health_possible: int = 0


@dataclass
class InventoryStatistics:
    total_hosts: int
    active_hosts: int
    inactive_hosts: int
    groups: int
    recent_changes: int
    group_counts: list[InventoryGroup] = field(
        default_factory=list
    )


@dataclass
class InventorySummary:
    total_hosts: int
    groups: int
    hosts: list[InventoryHost]
    statistics: InventoryStatistics
