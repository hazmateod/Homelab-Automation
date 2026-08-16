# HIMP — Current Project Status & Authoritative Roadmap

**Document date:** 2026-08-16  
**Project:** Homelab Infrastructure Management Platform (HIMP)  
**Repository:** `Homelab-Automation`  
**Branch:** `feature/plugin-sdk`  
**Current verified implementation commit:** `c71ad23`  
**Git state at latest checkpoint:** LOCAL == REMOTE / working tree clean  
**Production state:** ACTIVE / PRODUCTION ACCEPTANCE PASSED

---

# 1. Purpose

This document is the **current authoritative project status and roadmap snapshot** for HIMP.

It supersedes older planning documents when they describe work as "planned",
"next", or "remaining" even though that work has subsequently been completed.

Historical completion documents remain valuable as records of what happened.
They are not, however, the authoritative source for what remains to be built.

The project has now progressed through the major production platform,
operations UX, PostgreSQL modernization, scheduler cutover, backup, recovery,
and production-readiness work.

The next planning decision should therefore be based on the **actual current
system**, not the older Phase 9/10 roadmap.

---

# 2. Executive Summary

HIMP is a production operational-management platform for the homelab.

The current production architecture is:

```text
                         ┌─────────────────────────────┐
                         │       HIMP VM 600           │
                         │ automation.server.arpa      │
                         │ 10.10.37.56                 │
                         │ pve01                       │
                         │                             │
                         │ FastAPI / Uvicorn           │
                         │ HIMP application            │
                         │ Scheduler client            │
                         └──────────────┬──────────────┘
                                        │
                              PostgreSQL connections
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   PostgreSQL VM 610         │
                         │ himpdb01.server.arpa        │
                         │ 10.10.37.57                 │
                         │ pve02                       │
                         │ PostgreSQL 18                │
                         │ database: himp               │
                         └──────────────┬──────────────┘
                                        │
                                  PBS protection
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │       PBS PrimaryBackup     │
                         │       10.10.37.52           │
                         │       namespace: Blackwatch │
                         └─────────────────────────────┘
```

The production acceptance state is:

```text
HIMP service:                  ACTIVE
PostgreSQL backend:            ACTIVE / AUTHORITATIVE
Scheduler timer:               ENABLED / ACTIVE
Scheduler cutover gate:        ENABLED
Legacy scheduled-update timer: DISABLED
Legacy inventory-sync timer:   DISABLED
HIMP VM 600:                   RUNNING
PostgreSQL VM 610:             RUNNING
PBS protection:                VERIFIED
PostgreSQL restore:            VERIFIED
Repository:                    CLEAN / SYNCHRONIZED
```

The latest production acceptance verified:

```text
20 HIMP database tables
2 users
46 inventory hosts
594 automation executions
10,982 host-health-history records
5 automation schedules
```

---

# 3. Critical Correction to Older Roadmaps

Several older documents still contain statements such as:

```text
Phase 9.4 — NEXT
Phase 9.6 — PLANNED
Phase 9.7 — PLANNED
Phase 9.8 — PLANNED
Phase 9.9 — PLANNED
Phase 9.10 — PLANNED
```

Those statements are **historical**.

The actual project state is:

```text
Phase 9.1   COMPLETE
Phase 9.2   COMPLETE
Phase 9.3   COMPLETE
Phase 9.4   COMPLETE / reliability work completed
Phase 9.5   COMPLETE / user management
Phase 9.6   COMPLETE / PDF and host exports
Phase 9.7   COMPLETE / log viewer and exports
Phase 9.8   COMPLETE / disaster recovery validation
Phase 9.9   COMPLETE / release and rollback process
Phase 9.10  COMPLETE / production gate and defect remediation
```

The project subsequently completed:

```text
Phase 10    COMPLETE
Phase 11    COMPLETE through production readiness
```

Therefore the old "remaining Phase 9" list must **not** be used to select
the next engineering task.

---

# 4. Completed Major Phases

## Phase 1 — Foundation

**STATUS: COMPLETE**

Established the HIMP application foundation, project structure, inventory,
automation, service architecture, and initial operational capabilities.

---

## Phase 2 — Plugin / Infrastructure Integration

**STATUS: COMPLETE**

Established the infrastructure-plugin model and integration with the
homelab infrastructure.

Key production integrations include:

- Proxmox
- Proxmox Backup Server
- Unbound
- Technitium DNS
- infrastructure inventory and health

---

## Phase 3 — Automation Foundation

**STATUS: COMPLETE**

Established the automation execution architecture used by later phases.

The architecture deliberately reuses one execution path rather than
creating separate execution frameworks for each feature.

---

## Phase 4 — Scheduler

**STATUS: COMPLETE**

Established scheduled automation execution, scheduler persistence,
locking, retry behavior, timeout behavior, execution history, and later
scheduler reliability improvements.

The scheduler architecture was subsequently hardened during Phase 11.6.

---

## Phase 5 — Production / Security Foundation

**STATUS: COMPLETE**

Production foundation includes:

- authentication
- authorization / RBAC
- password management
- server-side sessions
- protected dashboard/API
- service identity
- SSH identity
- security-event logging
- safe API error boundary
- deployment hardening
- systemd hardening
- deployment validation
- production service management

HIMP runs under:

```text
himp:himp
```

rather than as root.

---

# 5. Phase 6 — Orchestration

**STATUS: COMPLETE**

The workflow architecture was implemented using the existing automation
execution infrastructure.

Completed capabilities include:

- workflow model
- workflow tasks
- task dependencies
- workflow execution
- retry behavior
- timeout behavior
- workflow execution history
- workflow/task correlation
- workflow history API
- workflow dashboard integration

Architectural rule:

```text
Workflow
   ↓
Existing automation execution engine
   ↓
Existing execution / retry / timeout / dependency infrastructure
   ↓
Existing execution history
```

No second execution engine was created.

---

# 6. Phase 7 — Infrastructure Intelligence

**STATUS: COMPLETE**

Infrastructure intelligence capabilities were implemented around the
existing inventory and health data.

Completed scope includes:

- asset relationships
- infrastructure change detection
- health correlation
- inventory baselines
- inventory changes
- operational infrastructure visibility

The implementation remains deterministic and explainable.

---

# 7. Phase 8 — Automation Intelligence

**STATUS: COMPLETE**

Remediation intelligence is implemented through the existing automation
framework.

Completed scope includes:

- remediation policy evaluation
- remediation execution
- remediation proposals
- remediation workflow integration
- remediation audit history
- remediation API
- remediation verification
- safety / approval hardening
- remediation operationalization
- scheduled remediation routing
- remediation UI/dashboard integration

The lifecycle is:

```text
Infrastructure Evidence
        ↓
Remediation Proposal
        ↓
Policy Evaluation
        ↓
Approval / Confirmation
        ↓
Remediation Execution
        ↓
Verification
        ↓
Audit History
        ↓
API / Operational Visibility
```

Safety behavior is fail-closed.

No separate remediation execution, policy, audit, verification, or scheduler
framework was introduced.

---

# 8. Phase 9 — Operational Platform

**STATUS: COMPLETE**

The major operational platform capabilities are now production validated.

## 9.1 Unified Dashboard

COMPLETE.

Provides operational visibility across:

- infrastructure
- health
- plugins
- workflows
- automation
- remediation
- operational status
- recent activity
- attention-required conditions

## 9.2 Operational Reporting

COMPLETE.

Reporting reuses the existing reporting service and calculations.

## 9.3 HIMP Self-Health

COMPLETE.

Provides application/runtime/service/database/scheduler and infrastructure
health visibility.

## 9.4 Reliability

COMPLETE.

Inventory/update reliability work was implemented and validated, including
scheduler/update diagnostics and structured execution results.

## 9.5 User Management

COMPLETE / PRODUCTION VERIFIED.

Implemented:

- administrator-only user API
- user listing
- account creation
- role management
- active/disabled state
- display-name management
- password-state visibility
- `/users` web UI

Existing authentication/session infrastructure is reused.

## 9.6 PDF Reporting

COMPLETE / PRODUCTION VERIFIED.

Implemented:

- operational PDF reports
- authenticated PDF API
- Reports-page PDF download
- per-host PDF export
- per-host TXT export
- per-host CSV export

Existing `ReportService` is reused.

## 9.7 Log Viewer and Log Export

COMPLETE / PRODUCTION VERIFIED.

Implemented:

- normalized operational `LogService`
- authenticated `/history` viewer
- operational log filtering/history normalization
- JSON export
- TXT export
- CSV export
- web-safe serialization
- Excel-safe CSV handling

Raw filesystem log exposure was deliberately avoided.

The architecture is:

```text
Browser
   ↓
Authenticated API
   ↓
LogService
   ↓
Approved log sources
   ↓
Filtered result
```

## 9.8 Disaster Recovery

COMPLETE / RECOVERY VERIFIED.

HIMP production VMID 600 has scheduled PBS protection.

A real PBS snapshot was restored to isolated VMID 699 and the recovered
application/database state was validated.

## 9.9 Release / Upgrade Process

COMPLETE / PRODUCTION VERIFIED.

Implemented:

- Git-clean deployment-source enforcement
- exact deployed revision marker
- deployment regression coverage
- release/upgrade runbook
- rollback procedure
- history-preserving rollback policy
- runtime/database rollback safety boundaries

## 9.10 Production Gate

COMPLETE.

Production browser testing found and corrected real runtime issues that
were not visible in the automated suite.

This validated the principle that automated tests alone do not constitute
the production gate.

Scheduled Updates was subsequently run through the production execution
path successfully.

---

# 9. Phase 10 — Operations UX & Production Refinement

**STATUS: COMPLETE / PRODUCTION VALIDATED**

Phase 10 focused on improving operator visibility without replacing
proven production execution infrastructure.

Completed:

### 10.1 Automation Progress & Execution UX

- active execution visibility
- execution start time
- elapsed time
- active-state UI
- execution lock integration
- long-running execution validation

### 10.2 Python Deprecation / Warning Cleanup

- timestamp/deprecation cleanup
- regression warning cleanup

### 10.3 CMDB Security & Monitoring Completion

- security/monitoring refinement
- CMDB operational visibility

### 10.4 Recent Activity / History UX

- improved recent activity presentation
- dashboard history clarity

### 10.5 Production Refinement Gate

COMPLETE.

Phase 10 achieved its implementation and production-validation goals.

---

# 10. Phase 11 — Database Platform Modernization

**STATUS: COMPLETE / PRODUCTION VALIDATED**

Phase 11 modernized HIMP persistence from SQLite to PostgreSQL.

## 11.1 PostgreSQL Foundation

COMPLETE.

Dedicated PostgreSQL host:

```text
VMID:       610
Hostname:   himpdb01.server.arpa
IP:         10.10.37.57
Node:       pve02
Database:   himp
PostgreSQL: 18
```

A dedicated least-privilege application account is used.

Network access is restricted to the HIMP application host.

## 11.2 PostgreSQL Schema

COMPLETE.

PostgreSQL-compatible schema and persistence architecture were established.

## 11.3 Repository PostgreSQL Compatibility

COMPLETE.

Repositories were adapted for PostgreSQL behavior including:

- parameter syntax
- generated identifiers
- timestamp behavior
- transactions
- locking
- schema inspection
- Boolean handling
- PostgreSQL-specific connection behavior

## 11.4 PostgreSQL Infrastructure

COMPLETE.

The PostgreSQL service is operationally independent from the HIMP runtime.

## 11.5 SQLite → PostgreSQL Migration

COMPLETE.

The migration mechanism was developed and rehearsed before production
execution.

Migration preserved the required HIMP operational state.

## 11.6 Production Cutover

COMPLETE.

Production was migrated to PostgreSQL.

The scheduler was separately validated through a controlled cutover.

The scheduler command now explicitly closes PostgreSQL connection pools
when the command terminates.

Real systemd scheduler execution produced:

```text
successful execution
clean exit
no PostgreSQL pool shutdown warnings
```

## 11.7 Backup / Restore / Recovery

COMPLETE / RECOVERY VERIFIED.

Production PostgreSQL protection:

```text
VMID:       610
PBS:        10.10.37.52
Datastore:  PrimaryBackup
Namespace:  Blackwatch
```

A fresh recovery point was created:

```text
PBS:backup/ct/610/2026-08-16T22:01:26Z
```

That recovery point was restored to isolated VMID 699.

The restored PostgreSQL cluster came online.

The restored `himp` database contained:

```text
20 public tables
2 users
46 inventory hosts
594 automation executions
10,982 host-health-history records
5 automation schedules
```

The restore container was isolated from production networking and destroyed
after validation.

Production VMID 610 remained running throughout the test.

## 11.8 Production Readiness

COMPLETE / PRODUCTION ACCEPTANCE PASSED.

Phase 11.8 acceptance verified:

```text
HIMP service                 PASS
Scheduler timer              PASS
Scheduler cutover             PASS
PostgreSQL backend            PASS
PostgreSQL connectivity       PASS
Production data               PASS
HIMP VM protection            PASS
PostgreSQL VM protection     PASS
Legacy timers disabled       PASS
Git state                     PASS
```

No additional infrastructure validation is required merely to close
Phase 11.

---

# 11. Current Production Architecture

## Application

```text
VMID:       600
Hostname:   automation.server.arpa
IP:         10.10.37.56
Node:       pve01
Service:    himp.service
Port:       9347
Runtime:    /opt/himp
Identity:   himp:himp
```

## Database

```text
VMID:       610
Hostname:   himpdb01.server.arpa
IP:         10.10.37.57
Node:       pve02
Database:   himp
PostgreSQL: 18
```

## Backup

```text
PBS:        10.10.37.52
Datastore:  PrimaryBackup
Namespace:  Blackwatch
```

HIMP VMID 600 and PostgreSQL VMID 610 are independently protected.

This is intentional.

The existing Proxmox/PBS infrastructure is the authoritative backup system.
No second HIMP-specific backup framework is required.

---

# 12. Scheduler Architecture

The production scheduler is now:

```text
systemd timer
      ↓
himp-scheduler.service
      ↓
python -m himp.cli scheduler-run
      ↓
PostgreSQL-backed scheduler
      ↓
existing automation execution infrastructure
```

Production state:

```text
himp-scheduler.timer = enabled / active
himp-scheduler.service = oneshot / inactive between runs
cutover gate = ENABLED
```

The scheduler is expected to be inactive between successful oneshot
executions. This is normal.

The legacy scheduled-update timer is disabled.

The legacy inventory-sync timer is disabled.

---

# 13. Backup Architecture Decision

The project deliberately did **not** create a new backup subsystem.

Decision:

> Use the existing Proxmox/PBS architecture for HIMP production protection.

This provides:

- externalized backup storage
- existing retention mechanisms
- existing operational tooling
- independent protection of application and database hosts
- tested restore capability
- no additional HIMP backup daemon
- no additional backup credentials
- no additional storage path
- lower operational complexity

---

# 14. Database Architecture Decision

PostgreSQL is now the authoritative HIMP production database.

SQLite is no longer the production persistence backend.

The architectural relationship is:

```text
HIMP application
      ↓
PostgreSQL client/backend
      ↓
PostgreSQL VM
      ↓
PBS
```

The PostgreSQL service is independent of the HIMP application VM.

The application uses a dedicated least-privilege database identity.

---

# 15. Deployment Architecture Decision

Production deployment is controlled through:

```text
scripts/deploy/himp.sh
```

The deployment process requires:

```text
Git working tree clean
        ↓
source revision identified
        ↓
application synchronization
        ↓
dependency synchronization when required
        ↓
systemd synchronization
        ↓
service restart only when necessary
        ↓
service health validation
        ↓
deployed revision marker
```

Production deployment must not be performed from a dirty working tree.

The deployed revision is recorded in:

```text
/opt/himp/.himp-release
```

---

# 16. Security Architecture Decisions

The following are established and should not be casually redesigned.

## Authentication

Use the existing HIMP authentication/session system.

## Authorization

Use existing RBAC/session authorization.

## Service identity

HIMP runs as:

```text
himp:himp
```

## Systemd hardening

Retain the hardened service boundary and only change it when a concrete
runtime requirement is demonstrated.

## Logs

Never expose raw log files directly through an HTTP endpoint.

Use authenticated application APIs and `LogService`.

## Secrets

Do not place passwords, session tokens, reset tokens, or database secrets
in logs or ordinary application output.

## Remediation

Fail closed for unsafe or ambiguous remediation decisions.

---

# 17. Current Test / Validation Position

The project has repeatedly used full regression gates throughout development.

Historical full-suite counts progressed substantially as the platform grew.

The most recent Phase 11.8 production acceptance was performed against
commit:

```text
c71ad23
```

The repository was:

```text
LOCAL == REMOTE
working tree clean
```

The final production acceptance was green.

---

# 18. What Is Actually Left?

This is the most important section of this document.

## No previously planned Phase 9/10 feature remains outstanding.

The following are **not** future work:

```text
User management
PDF export
Log viewer
Log export
Disaster recovery
Release/upgrade process
Production gate
PostgreSQL migration
PostgreSQL backup
PostgreSQL restore
Scheduler cutover
Production readiness
```

They are complete.

## No additional Phase 11 infrastructure validation is currently required.

The production database migration, scheduler cutover, backup, restore, and
acceptance have all been demonstrated.

## The next work is therefore a NEW PRODUCT ROADMAP decision.

The project has reached a clean architectural boundary where the next phase
should be chosen based on desired product capability rather than unfinished
migration or production-hardening work.

---

# 19. Recommended Next Roadmap

The next roadmap should be treated as **new product development**, not as
unfinished Phase 9/10/11 work.

Recommended priority areas are:

## Track A — Operational Intelligence

Potential capabilities:

- richer infrastructure relationships
- topology views
- dependency visualization
- health correlation
- change impact analysis
- infrastructure drift detection
- baseline comparison
- historical trend analysis

## Track B — Automation Intelligence

Potential capabilities:

- richer remediation workflows
- approval queues
- remediation recommendations
- remediation scheduling
- remediation verification improvements
- operator feedback/history
- safer autonomous low-risk remediation

## Track C — Workflow / Orchestration UX

Potential capabilities:

- richer workflow designer
- workflow dependency visualization
- workflow execution timeline
- workflow failure analysis
- workflow replay/retry controls
- operator-oriented workflow dashboards

## Track D — Operational Administration

Potential capabilities:

- richer user administration
- role/permission management
- audit administration
- system configuration UI
- operational settings
- notification preferences

## Track E — Platform Lifecycle

Potential capabilities:

- formal release promotion workflow
- upgrade automation
- migration framework improvements
- environment/version compatibility
- automated backup verification
- disaster-recovery runbooks in the UI

These are **candidate directions**, not commitments.

The next numbered phase should be created only after the desired product
direction is selected.

---

# 20. Recommended Definition of "Project Complete"

HIMP should not be considered "complete" merely because every feature on an
old roadmap has been implemented.

A meaningful production definition is:

```text
SECURE
  ↓
RELIABLE
  ↓
OBSERVABLE
  ↓
RECOVERABLE
  ↓
MAINTAINABLE
  ↓
USEFUL
```

The first five are now substantially established.

The next development effort should therefore concentrate on:

```text
USEFULNESS
+
OPERATIONAL INTELLIGENCE
+
AUTOMATION VALUE
```

rather than repeatedly rebuilding infrastructure that has already passed
production validation.

---

# 21. Development Rules — Preserve These

The following working rules remain authoritative:

1. One subsystem per working slice.
2. Complete one feature end-to-end before moving on.
3. One completed working slice per commit.
4. Do not refactor production code without a concrete reason.
5. Avoid duplicate logic.
6. Reuse existing services, repositories, execution, authentication,
   authorization, and scheduling infrastructure.
7. Build the implementation slice first and consolidate testing at the
   end of the slice.
8. Run focused tests for the completed slice.
9. Run the full regression suite before checkpoints.
10. Run `compileall`.
11. Run `git diff --check`.
12. Inspect the final diff.
13. Keep Git clean and synchronized.
14. Do not deploy from a dirty working tree.
15. Push completed implementation commits.
16. Verify `LOCAL == REMOTE`.
17. Deploy through `scripts/deploy/himp.sh`.
18. Verify production runtime behavior for production-facing features.
19. Do not guess when repository/runtime evidence can establish the fact.
20. Prefer direct file replacements and command-by-command implementation.
21. Do not introduce a second execution framework where the existing one
    can be reused.
22. Do not introduce a second backup architecture where PBS already provides
    the required protection.
23. Do not continue infrastructure validation merely because an old
    checklist still contains unchecked historical text.

---

# 22. Current Git Checkpoint

```text
Branch:
feature/plugin-sdk

HEAD:
c71ad23

Commit:
fix: close postgres pools in scheduler command

Remote:
origin/feature/plugin-sdk

Synchronization:
LOCAL == REMOTE

Working tree:
CLEAN
```

---

# 23. Current Production Checkpoint

```text
HIMP:
ACTIVE

Database:
PostgreSQL

Scheduler:
ACTIVE TIMER

Scheduler cutover:
ENABLED

Legacy scheduled updates:
DISABLED

Legacy inventory sync:
DISABLED

HIMP VM 600:
RUNNING

PostgreSQL VM 610:
RUNNING

PBS:
ACTIVE

HIMP PBS protection:
VERIFIED

PostgreSQL PBS protection:
VERIFIED

PostgreSQL restore:
VERIFIED

Production acceptance:
PASSED
```

---

# 24. Exact Starting Point for the Next Development Session

Do **not** automatically start another numbered phase from an old roadmap.

Start the next session with:

```text
1. Confirm Git branch/status.
2. Confirm deployed revision.
3. Confirm HIMP service.
4. Confirm PostgreSQL.
5. Confirm scheduler.
6. Confirm PBS protection.
7. Review this document.
8. Select the next product capability.
9. Define one bounded implementation slice.
10. Implement end-to-end.
11. Run focused validation.
12. Run full regression at the end of the slice.
13. Run compileall.
14. Run git diff --check.
15. Commit.
16. Push.
17. Verify LOCAL == REMOTE.
18. Deploy when the slice is production-facing.
19. Perform production runtime validation.
20. Record the completed slice.
```

---

# 25. Bottom Line

HIMP is **not sitting in the middle of the old Phase 9 roadmap**.

It has progressed through:

```text
Production Foundation
        ↓
Orchestration
        ↓
Infrastructure Intelligence
        ↓
Automation Intelligence
        ↓
Operational Platform
        ↓
Operations UX Refinement
        ↓
PostgreSQL Modernization
        ↓
Production Cutover
        ↓
Backup / Restore Validation
        ↓
Production Acceptance
```

The infrastructure/platform foundation is now mature enough that the next
decision should be a **product capability decision**.

The project should not spend another development cycle rediscovering or
re-validating already completed work.

**Current state: PRODUCTION-READY PLATFORM.**

**Next state: SELECT THE NEXT PRODUCT CAPABILITY AND BUILD IT.**
