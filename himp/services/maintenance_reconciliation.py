"""Serialize operator verification with maintenance execution."""

from contextlib import contextmanager
from uuid import uuid4

from himp.database.automation_locks import AutomationLockRepository
from himp.services.automation import MAINTENANCE_RESOURCE


@contextmanager
def maintenance_reconciliation():
    locks = AutomationLockRepository()
    token = str(uuid4())
    if not locks.acquire(MAINTENANCE_RESOURCE, lease_seconds=60, execution_token=token):
        raise ValueError("Maintenance is still active.")
    try:
        yield
    finally:
        locks.release(MAINTENANCE_RESOURCE, execution_token=token)
