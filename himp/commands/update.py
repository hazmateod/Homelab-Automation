"""
Update Commands
"""

from himp.lib.history import log
from himp.lib.output import error, info, success
from himp.app import HIMP


def run(args):
    if not args.target:
        error("Host or group is required.")
        return

    if args.target != "maintenance":
        error("Use the automation API for explicit host or group updates.")
        return 1

    service = HIMP().automation

    info(f"Updating {args.target}...")
    print()

    execution = service.run("scheduled_updates", confirmed=True)
    result = execution["result"]

    ok = result["success"]
    elapsed = result["elapsed"]

    log(
        f"update {args.target}",
        ok,
        elapsed,
    )

    print()

    if ok:
        success("Update completed successfully.")
    else:
        error("Update failed.")

    info(f"Execution time: {elapsed:.2f} seconds")
    return 0 if ok else 1


def reconcile(args):
    from uuid import uuid4

    from himp.database.automation_locks import AutomationLockRepository
    from himp.database.maintenance_outcomes import MaintenanceOutcomeRepository
    from himp.services.automation import MAINTENANCE_RESOURCE

    if not args.confirm_drained:
        error("Verify the worker and remote mutation have stopped before reconciliation.")
        raise SystemExit(1)

    locks = AutomationLockRepository()
    token = str(uuid4())
    if not locks.acquire(MAINTENANCE_RESOURCE, lease_seconds=60, execution_token=token):
        error("Maintenance is still active.")
        raise SystemExit(1)

    try:
        reconciled = MaintenanceOutcomeRepository().reconcile(
            args.plan_id, args.host, args.note,
        )
    finally:
        locks.release(MAINTENANCE_RESOURCE, execution_token=token)

    if not reconciled:
        error("No unreconciled maintenance outcome matched the plan and host.")
        raise SystemExit(1)
    success("Reconciliation recorded. No maintenance was dispatched.")
