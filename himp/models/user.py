"""
User model.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    username: str
    role: str
    active: bool = True
    display_name: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    failed_login_attempts: int = 0
    password_change_required: bool = False
