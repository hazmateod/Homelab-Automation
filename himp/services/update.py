"""
Update Service.

Provides a shared service for running maintenance updates.
"""

from himp.config import config
from himp.lib.ansible import run_playbook


class UpdateService:
    """
    Provides maintenance update operations.
    """

    def update(
        self,
        target,
        limit=None,
        timeout=None,
    ):
        success, elapsed = run_playbook(
            config.maintenance_playbook,
            limit or target,
            timeout=timeout,
        )

        return {
            "target": target,
            "success": success,
            "elapsed": round(elapsed, 3),
        }
