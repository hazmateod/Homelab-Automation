"""
Notification event model.

Transport-independent event contract used by HIMP notification sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NotificationEvent:
    event_type: str
    source_type: str
    source_id: str
    severity: str
    title: str
    message: str
    deduplication_key: str
    correlation_key: str
    occurred_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
