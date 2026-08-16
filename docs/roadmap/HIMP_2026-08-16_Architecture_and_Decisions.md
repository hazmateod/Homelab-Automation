# HIMP — Architecture and Decisions Record
## 2026-08-16 Engineering Session

## 1. Executive Summary

Today's work completed the production PostgreSQL application cutover validation, corrected a scheduler PostgreSQL connection-pool lifecycle defect, enabled the production scheduler, and verified production backup protection using the existing Proxmox Backup Server architecture.

The architectural direction was deliberately conservative:

- PostgreSQL is the production database backend.
- HIMP remains a dedicated systemd-managed production service.
- Existing Proxmox/PBS infrastructure remains the backup and disaster-recovery mechanism.
- The scheduler remains a systemd timer plus oneshot service.
- Production cutover used explicit gates and controlled validation.
- Testing was narrowed to tests that proved an observed defect or release gate.

## 2. Production Database Architecture

### Decision

HIMP production uses PostgreSQL as the authoritative database backend.

Verified configuration:
- Backend: PostgreSQL
- Host: himpdb01.server.arpa
- Database: himp
- Schema: public

Production validation showed:
- 46 inventory hosts
- 594 automation executions
- 10,982 host-health history records
- 55 inventory changes
- 10 sessions
- 2 users

## 3. HIMP Runtime Architecture

HIMP remains:
- systemd managed
- user/group: himp:himp
- working directory: /opt/himp
- Uvicorn application server
- listener: 0.0.0.0:9347

A controlled stop/start test proved that HIMP could terminate and reconnect to PostgreSQL successfully.

## 4. Scheduler Architecture

### Decision

The production scheduler uses:

`systemd timer -> himp-scheduler.service -> python -m himp.cli scheduler-run`

The scheduler service is `Type=oneshot`.

The timer evaluates persisted schedules once per minute. The scheduler service normally becomes inactive after each evaluation; that is expected behavior.

### Production Gate

The cutover gate is:

`/run/himp-scheduler-cutover-enabled`

It remained disabled during diagnosis and was enabled only after the scheduler lifecycle was proven clean.

## 5. Scheduler Lifecycle Defect and Resolution

### Problem

Controlled scheduler executions initially produced psycopg_pool warnings that worker and scheduler threads could not stop within the default timeout.

The scheduler returned success, but PostgreSQL connection pools were not explicitly closed before process termination.

### Decision

The scheduler command was changed to guarantee pool cleanup:

`finally: PostgreSQLDatabase.close_pools()`

A focused regression test was added.

Scheduler command tests passed:

`13 passed`

### Release

Commit:

`c71ad23 — fix: close postgres pools in scheduler command`

The fix was pushed to `origin/feature/plugin-sdk` and deployed to `/opt/himp`.

### Production Proof

Post-deployment scheduler executions completed successfully with:

- exit status: 0
- no pool shutdown warnings
- HIMP active
- scheduler timer active
- scheduler service inactive after oneshot completion

The lifecycle defect is resolved.

## 6. Scheduler Cutover Decision

The scheduler was enabled only after:

1. Persisted production schedules were inspected.
2. Controlled execution exposed the pool lifecycle issue.
3. The lifecycle defect was corrected.
4. A focused regression test was added.
5. The fix was committed and deployed.
6. A real scheduler execution showed no pool warnings.
7. The cutover gate was enabled.
8. Normal timer-triggered executions were observed.
9. The oneshot service settled normally.

Production schedules verified:
- Health Check — manual
- Generate Reports — manual
- Inventory Refresh — daily 03:00
- Scheduled Updates — daily 03:15
- Host Health Check — daily 03:30

## 7. Backup Architecture Decision

### Decision

No new backup system was created.

The existing Proxmox/PBS architecture is sufficient for HIMP production protection.

This avoids redundant backup software, additional credentials, storage paths, and operational complexity.

### HIMP Protection

Production HIMP:
- VMID 600
- automation.server.arpa
- 10.10.37.56
- pve01

Existing PBS protection:
- schedule: 23:00
- mode: snapshot
- storage: PBS
- retention: 30 daily / 1 monthly

A manual post-cutover backup completed successfully:

`ct/600/2026-08-16T21:46:37Z`

The backup completed in approximately 10 seconds and VMID 600 remained running.

## 8. PostgreSQL Backup Architecture

PostgreSQL production:
- VMID 610
- himpdb01.server.arpa
- pve02
- running
- onboot enabled

Existing PBS protection:
- schedule: 08:00
- mode: snapshot
- storage: PBS
- retention: 14 daily / 2 weekly

Verified PBS artifact:

`PBS:backup/ct/610/2026-08-16T16:25:36Z`

Size:

`952,307,348 bytes`

This confirms PostgreSQL is protected outside the PostgreSQL host.

## 9. PBS Architecture

Primary PBS:
- server: 10.10.37.52
- datastore: PrimaryBackup
- namespace: Blackwatch

The PBS datastore was verified active at approximately 41.45% utilization during validation.

The existing PBS architecture remains the authoritative HIMP backup destination.

## 10. Backup Strategy Principles

### Protect application and database independently

HIMP VMID 600 and PostgreSQL VMID 610 have independent PBS protection.

### Keep backups off the production database host

PostgreSQL recovery points reside on PBS.

### Use existing infrastructure

No new backup daemon, NAS mount, application-level backup framework, or custom storage target was introduced.

### Validate actual artifacts

Configuration alone was not treated as proof. Real HIMP and PostgreSQL PBS recovery points were verified.

## 11. Production Safety Model

The cutover used explicit gates.

The scheduler remained disabled until lifecycle behavior was proven.

The PostgreSQL production container was never intentionally overwritten.

Backup validation used existing production protection mechanisms without modifying production data.

## 12. Git and Release Discipline

The scheduler lifecycle correction was kept as a focused implementation slice.

Commit:
`c71ad23`

Message:
`fix: close postgres pools in scheduler command`

The commit was pushed to:
`origin/feature/plugin-sdk`

Local and remote revisions were synchronized.

The production deployment script requires a clean Git working tree before deployment, preserving a deliberate relationship between source control and `/opt/himp` production state.

## 13. Current Production State

```text
Branch:
feature/plugin-sdk

HEAD:
c71ad23

Git:
clean / synchronized

Database:
PostgreSQL

HIMP:
active

HIMP listener:
0.0.0.0:9347

Scheduler timer:
active

Scheduler service:
inactive between oneshot executions

Scheduler cutover gate:
ENABLED

PBS:
active

HIMP backup:
verified

PostgreSQL backup:
verified
```

## 14. Remaining Phase 11.7 Work

The remaining meaningful work is intentionally narrow:

1. Use a verified PostgreSQL PBS recovery point.
2. Restore to an isolated temporary target.
3. Do not modify production VMID 610.
4. Start PostgreSQL.
5. Verify database connectivity.
6. Validate critical HIMP data.
7. Remove the temporary recovery target.
8. Record the recovery result.
9. Commit the final Phase 11.7 checkpoint.

No broad regression cycle is required merely to close this backup phase.

## 15. Architectural Direction Going Forward

Unless a concrete production requirement proves otherwise, retain today's architecture.

Avoid:
- replacing PBS with another backup system
- adding redundant database backup daemons without need
- converting the scheduler into a long-running process
- broad production refactoring
- tests that do not prove a release criterion or observed defect

Prefer:
- small end-to-end implementation slices
- explicit production gates
- focused regression tests for observed defects
- existing infrastructure when it already satisfies the requirement
- production evidence over speculative redesign
- Git checkpoints after completed implementation slices

## 16. Session Conclusion

Today's work moved HIMP from PostgreSQL cutover validation into an operational production state.

Architecture:

```text
HIMP
  |
  +-- FastAPI / Uvicorn
  |       |
  |       +-- systemd
  |
  +-- PostgreSQL
  |       |
  |       +-- himpdb01.server.arpa
  |
  +-- Scheduler
  |       |
  |       +-- systemd timer
  |       +-- oneshot scheduler service
  |
  +-- Proxmox
  |       |
  |       +-- VM/LXC 600 HIMP
  |       +-- VM/LXC 610 PostgreSQL
  |
  +-- PBS
          |
          +-- PrimaryBackup
          +-- Blackwatch namespace
          +-- HIMP recovery points
          +-- PostgreSQL recovery points
```

The remaining Phase 11.7 task is recovery proof, not architectural construction.
