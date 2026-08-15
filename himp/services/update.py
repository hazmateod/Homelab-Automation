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
        result = run_playbook(
            config.maintenance_playbook,
            limit or target,
            timeout=timeout,
        )

        return {
            "target": target,
            "success": result.success,
            "return_code": result.return_code,
            "elapsed": round(result.elapsed, 3),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
