# HIMP Phase 11 - Database Platform Modernization Checkpoint

**Project:** Homelab Infrastructure Management Platform (HIMP)\
**Branch:** `feature/plugin-sdk`\
**Checkpoint date:** 2026-08-16\
**Current source/deployed revision:**
`0a94b67811f1c6ecd44fbfd1bcc982c07890e97e`\
**Production database backend:** SQLite\
**PostgreSQL status:** Provisioned, secured, connectivity validated,
Python backend foundation available; application cutover has **not**
occurred.

------------------------------------------------------------------------

## 1. Executive Summary

Phase 11 modernizes HIMP persistence from its current SQLite
implementation toward PostgreSQL while preserving production safety and
rollback capability.

The work completed through this checkpoint establishes the PostgreSQL
infrastructure, introduces explicit database-backend configuration, adds
the Psycopg-backed PostgreSQL connection implementation, and hardens
HIMP deployment so runtime Python dependencies are synchronized
deterministically.

Production remains intentionally on SQLite. No `HIMP_DATABASE_*`
environment variables have been introduced into the production service
environment, and the deployed application continues to open
`data/himp.db`. PostgreSQL is therefore a prepared migration target
rather than the active production system.

The current code, remote branch, deployed release, runtime dependencies,
and service state were validated before beginning the Phase 11.2
schema/repository compatibility work.

------------------------------------------------------------------------

## 2. Phase 11 Objectives

Phase 11 is intended to:

1.  Introduce a supported PostgreSQL persistence backend.
2.  Preserve SQLite operation throughout the migration.
3.  Remove repository assumptions that are specific to SQLite.
4.  Create a PostgreSQL-compatible HIMP schema.
5.  Provide deterministic migration of existing HIMP production data.
6.  Validate functional and data parity before cutover.
7.  Cut production over only after explicit verification.
8.  Preserve a practical SQLite rollback path until PostgreSQL
    production operation is proven stable.

The migration is deliberately incremental. Merely adding PostgreSQL
connectivity does not authorize production cutover.

------------------------------------------------------------------------

## 3. PostgreSQL Platform Foundation

A dedicated PostgreSQL host has been prepared for HIMP:

  Item                    Value
  ----------------------- ------------------------
  Hostname                `himpdb01.server.arpa`
  Address                 `10.10.37.57`
  Platform                Debian 13 LXC
  CPU                     2 vCPU
  Memory                  2 GiB
  Storage                 20 GiB
  PostgreSQL              18.6
  HIMP application host   `10.10.37.56`
  Database                `himp`
  Application role        `himp_app`

The PostgreSQL service was configured with restricted network exposure
rather than broad LAN access.

Authentication uses SCRAM-SHA-256. HBA access for the HIMP application
role/database is restricted to the HIMP automation/application host.
Host-level firewall controls provide an additional network restriction.

The `himp_app` account is intended to be the least-privilege application
identity rather than a PostgreSQL administrative account.

DNS resolution and authenticated network connectivity from HIMP to
PostgreSQL were validated.

------------------------------------------------------------------------

## 4. PostgreSQL Connectivity Validation

A live Phase 11.1.3 backend smoke test successfully connected through
the new HIMP PostgreSQL backend.

Validated results included:

-   database: `himp`
-   authenticated role: `himp_app`
-   PostgreSQL server: `10.10.37.57/32`
-   HIMP client: `10.10.37.56/32`
-   SQLite-style placeholder normalization: PASS
-   dictionary row behavior: PASS
-   temporary PostgreSQL write: PASS
-   backend smoke test: PASS
-   persistent test table remaining afterward: NONE

This demonstrated real application-host-to-database-host connectivity
and basic transactional/write capability without migrating the HIMP
production schema or data.

------------------------------------------------------------------------

## 5. Phase 11.1.2 - Database Backend Configuration

**Commit:** `8432597` - `feat: add database backend configuration`

A centralized database configuration module was added at:

`himp/database/config.py`

The configuration supports:

-   `sqlite`
-   `postgresql`

Supported environment variables are:

-   `HIMP_DATABASE_BACKEND`
-   `HIMP_DATABASE_PATH`
-   `HIMP_DATABASE_HOST`
-   `HIMP_DATABASE_PORT`
-   `HIMP_DATABASE_NAME`
-   `HIMP_DATABASE_USER`
-   `HIMP_DATABASE_PASSWORD`

### Safety behavior

SQLite remains the default backend.

With no database environment configuration, HIMP continues to use:

`data/himp.db`

PostgreSQL configuration validates required host, database, user,
password, and port values. Invalid backend names and invalid port values
fail explicitly.

The existing SQLite `Database` class was integrated with
`DatabaseConfig` while refusing PostgreSQL operation until the
PostgreSQL implementation existed. This prevented configuration work
from accidentally changing the active persistence engine.

### Validation

Focused Phase 11.1.2 testing passed:

-   29 focused tests passed
-   708 full regression tests passed
-   `compileall`: PASS
-   `git diff --check`: PASS

The release was deployed and SQLite production operation remained
healthy.

------------------------------------------------------------------------

## 6. Phase 11.1.3 - PostgreSQL Python Backend

**Commit:** `7891f32` - `feat: add postgresql database backend`

A PostgreSQL backend was added at:

`himp/database/postgresql.py`

Runtime dependency added:

`psycopg[binary]>=3.2`

The development environment installed Psycopg 3.3.4.

### PostgreSQL backend capabilities

The initial backend provides:

-   configuration validation
-   Psycopg connection creation
-   dictionary row results
-   SQL execution
-   SQL queries
-   explicit transaction context
-   connection close
-   compatibility normalization from SQLite `?` placeholders to Psycopg
    `%s` placeholders

Connections use Psycopg autocommit for ordinary operations while the
backend exposes driver-managed transaction blocks when atomic work is
required.

### Validation

Backend unit tests passed:

-   6 PostgreSQL backend unit tests passed
-   29 Phase 11.1.3 focused tests passed
-   714 full regression tests passed
-   `compileall`: PASS
-   `git diff --check`: PASS

A live PostgreSQL smoke test also passed as described above.

Production remained on SQLite.

------------------------------------------------------------------------

## 7. Phase 11.1.4 - Deterministic Runtime Dependency Synchronization

**Commit:** `0a94b67` -
`fix: synchronize runtime dependencies during deployment`

Adding Psycopg exposed an important deployment concern: updating
`requirements.txt` in Git did not guarantee that the deployed
`/opt/himp/.venv` contained the new dependency.

The deployment process was therefore hardened before any
PostgreSQL-dependent production code could rely on Psycopg.

### Deployment behavior added

`scripts/deploy/himp.sh` now:

1.  Calculates the SHA-256 hash of source `requirements.txt`.
2.  Compares it with the deployed requirements marker.
3.  Tracks dependency changes independently from application/service
    changes.
4.  Installs runtime requirements when the dependency hash changes.
5.  Records the synchronized hash in:

`/opt/himp/.requirements.sha256`

6.  Leaves dependencies alone on later deployments when the hash is
    unchanged.

This makes runtime dependency synchronization deterministic and
idempotent.

### Regression coverage

Deployment regression tests were expanded substantially to validate the
new behavior.

Validation results:

-   17 deployment tests passed
-   718 full regression tests passed
-   `compileall`: PASS
-   shell syntax: PASS
-   `git diff --check`: PASS

------------------------------------------------------------------------

## 8. Phase 11.1.4 Production Deployment Verification

Revision `0a94b67811f1c6ecd44fbfd1bcc982c07890e97e` was deployed
successfully.

### Release identity

The following matched:

-   local Git revision
-   remote `origin/feature/plugin-sdk`
-   `/opt/himp/.himp-release`

### Dependency identity

The SHA-256 of source `requirements.txt` matched:

`/opt/himp/.requirements.sha256`

Runtime Psycopg version:

`3.3.4`

### Production backend safety

Production continued to report:

-   backend: `sqlite`
-   filename: `data/himp.db`
-   inventory hosts: 46

No `HIMP_DATABASE_*` production environment configuration was present.

### Runtime verification

-   `himp.service`: active
-   `himp-scheduler.timer`: active
-   Uvicorn listening on `0.0.0.0:9347`
-   local HTTP request returned `303`, consistent with the protected
    application redirect behavior
-   HIMP errors since deployment: none
-   repository clean and synchronized

This establishes revision `0a94b67` as the Phase 11.1 production
checkpoint.

------------------------------------------------------------------------

## 9. Phase 11.2 SQLite Compatibility Reconnaissance

Before implementing PostgreSQL schema compatibility, the codebase was
scanned for SQLite-specific assumptions.

The reconnaissance identified several concrete compatibility classes.

### 9.1 SQLite PRAGMA dependencies

`PRAGMA table_info(...)` is used for runtime schema inspection in:

-   `himp/database/inventory.py`
-   `himp/database/database.py`
-   `himp/database/automation_executions.py`
-   `himp/database/scheduler.py`
-   `himp/database/workflow_executions.py`

PostgreSQL cannot use SQLite PRAGMA statements. These schema-inspection
operations require a backend-neutral abstraction or PostgreSQL-specific
implementation.

### 9.2 AUTOINCREMENT schema dependencies

Numerous tables use:

`INTEGER PRIMARY KEY AUTOINCREMENT`

The scan found this pattern across repositories including:

-   inventory hosts
-   inventory changes
-   inventory baselines
-   workflows
-   workflow tasks
-   workflow dependencies
-   automation dependencies
-   executions
-   health history
-   asset relationships
-   automation executions
-   automation schedules
-   remediation audit
-   sessions
-   discovery
-   workflow executions
-   host health history

PostgreSQL identity/sequence semantics must replace this SQLite syntax
when creating the PostgreSQL schema.

### 9.3 SQLite transaction semantics

`himp/database/automation_locks.py` explicitly issues:

`BEGIN IMMEDIATE`

inside the database transaction context.

This is SQLite-specific concurrency behavior. PostgreSQL locking must
provide equivalent scheduler/automation safety using PostgreSQL
transaction and locking semantics rather than translating this SQL
literally.

This area is migration-critical because automation occurrence protection
must not regress.

### 9.4 Insert-ID dependencies

Repositories currently depend on cursor `lastrowid` behavior.

Detected uses include:

-   workflow creation
-   workflow task creation
-   workflow dependency creation
-   automation execution creation
-   remediation audit creation

Psycopg does not provide SQLite `lastrowid` semantics as a portable
repository contract. PostgreSQL-compatible inserts will need an explicit
returned identifier mechanism, normally based on `RETURNING`.

### 9.5 SQLite exception coupling

The production repository scan did not show the listed SQLite exception
classes in application code, but tests explicitly assert
`sqlite3.IntegrityError` in several repository suites.

Affected tests include repository coverage for:

-   workflow executions
-   users
-   workflows
-   sessions

A backend-neutral integrity/constraint error contract may therefore be
required if the same repository behavior is to be tested across both
engines.

### 9.6 Boolean representation

Several schemas store logical values as SQLite integers, including
fields such as:

-   `inventory_hosts.active`
-   `workflows.enabled`
-   `automation_schedules.enabled`
-   `users.active`
-   `users.password_change_required`
-   `remediation_operations.enabled`

Other integer fields, such as failed-login counters and change limits,
are numeric rather than booleans and must not be mechanically converted.

The PostgreSQL schema design must distinguish true logical fields from
ordinary integer fields while preserving repository/API behavior.

------------------------------------------------------------------------

## 10. Current SQLite Production Data Baseline

At the Phase 11.2 reconnaissance checkpoint, the SQLite database
contained 20 application tables.

  Table                         Rows
  ------------------------- --------
  asset_relationships              1
  automation_dependencies          0
  automation_executions        1,156
  automation_locks                 0
  automation_schedules             5
  discovery                        1
  executions                      20
  health_history                  26
  host_health_history         11,020
  inventory_baselines              0
  inventory_changes               55
  inventory_hosts                 46
  remediation_audit              456
  remediation_operations           0
  sessions                         0
  users                            0
  workflow_dependencies            0
  workflow_executions              3
  workflow_tasks                   0
  workflows                        0

These counts form an important pre-migration baseline for later
export/import and parity validation.

The largest current dataset is `host_health_history` with 11,020 rows,
followed by `automation_executions` with 1,156 rows and
`remediation_audit` with 456 rows.

------------------------------------------------------------------------

## 11. Phase 11.2 Migration Surface

The reconnaissance establishes that Phase 11.2 is not simply a matter of
changing SQL placeholders.

The compatibility layer must address at least:

1.  backend-neutral schema metadata inspection
2.  backend-specific primary-key/identity DDL
3.  backend-safe generated-ID retrieval
4.  SQLite `BEGIN IMMEDIATE` replacement for PostgreSQL lock acquisition
5.  integrity/constraint exception behavior
6.  boolean representation
7.  existing repository DDL ownership
8.  schema initialization order and foreign keys
9.  preservation of SQLite behavior throughout transition
10. eventual data migration and sequence synchronization

The current PostgreSQL `_normalize_sql()` placeholder shim is useful for
ordinary parameterized SQL, but it is not sufficient for schema and
concurrency compatibility.

------------------------------------------------------------------------

## 12. Recommended Phase 11.2 Implementation Order

### Phase 11.2.1 - Database Capability Boundary

Introduce backend-neutral primitives for operations that repositories
currently implement with SQLite-specific behavior.

Likely capabilities include:

-   backend identity
-   table-column inspection
-   generated-ID insert support
-   integrity/constraint error classification
-   transaction/locking capability appropriate to automation locks

Goal: repositories should ask the database abstraction for capabilities
rather than detect SQLite/PostgreSQL themselves.

**Estimated effort:** Medium.

### Phase 11.2.2 - PostgreSQL Schema Definition

Create a deterministic PostgreSQL schema representing all 20 current
application tables.

The schema must account for:

-   identity columns/sequences
-   foreign keys
-   unique constraints
-   check constraints
-   timestamps
-   boolean mappings
-   indexes where required
-   creation order

SQLite production initialization must remain untouched unless
compatibility changes are deliberately introduced.

**Estimated effort:** Medium to high.

### Phase 11.2.3 - Repository Compatibility

Migrate repositories away from SQLite-specific constructs.

Priority targets should include:

1.  workflows/generated IDs
2.  automation executions/generated IDs
3.  remediation audit/generated IDs
4.  PRAGMA-dependent repositories
5.  automation locks and concurrency semantics
6.  repositories with integrity-error tests

Build repository compatibility end-to-end, then run testing at the end
of the implementation slice.

**Estimated effort:** High.

### Phase 11.2.4 - PostgreSQL Repository Integration Testing

Run repository behavior against a real PostgreSQL test database rather
than relying only on mocked Psycopg connections.

Validate:

-   CRUD behavior
-   unique constraints
-   foreign keys
-   generated IDs
-   transaction rollback
-   automation locking
-   timestamp handling
-   row mappings
-   scheduler persistence

SQLite tests must continue to pass.

**Estimated effort:** High.

------------------------------------------------------------------------

## 13. Later Phase 11 Work

After repository/schema compatibility, the remaining migration work
should include:

### Data Migration Tooling

Create repeatable SQLite-to-PostgreSQL migration tooling with:

-   preflight checks
-   controlled table ordering
-   explicit transaction boundaries
-   row-count verification
-   sequence/identity synchronization
-   failure rollback
-   migration logging

### Migration Rehearsal

Perform at least one non-production migration rehearsal using a current
copy of the SQLite database.

Compare:

-   table counts
-   important records
-   relationships
-   scheduler definitions/history
-   automation execution history
-   health history
-   remediation audit history

### Application Validation on PostgreSQL

Run HIMP against PostgreSQL in a controlled validation mode and exercise
major application surfaces before production cutover.

### Production Cutover

Only after explicit approval:

1.  stop or quiesce HIMP writers
2.  take a final SQLite backup
3.  migrate final data
4.  validate PostgreSQL parity
5.  configure production `HIMP_DATABASE_*`
6.  restart HIMP
7.  run production smoke tests
8.  monitor logs/services/scheduler
9.  retain SQLite rollback artifacts

------------------------------------------------------------------------

## 14. Rollback and Safety Principles

Until PostgreSQL cutover is explicitly completed:

-   SQLite remains the production source of truth.
-   PostgreSQL development must not modify production backend selection
    implicitly.
-   Database credentials must not be committed to Git.
-   The existing PostgreSQL password file remains external to the
    repository.
-   Migration tooling must be repeatable and observable.
-   Production data should not be destructively transformed as part of
    compatibility development.
-   The SQLite database must be backed up immediately before final
    migration.
-   PostgreSQL cutover and SQLite retirement are separate decisions.

------------------------------------------------------------------------

## 15. Current Quality Baseline

Current verified regression baseline:

**718 tests passed**

Additional verified gates:

-   `compileall`: PASS
-   deployment shell syntax: PASS
-   `git diff --check`: PASS
-   HIMP production service: active
-   scheduler timer: active
-   HTTP listener: healthy
-   no HIMP errors after current deployment
-   local/remote/deployed release identity synchronized
-   production database: SQLite
-   PostgreSQL runtime driver: Psycopg 3.3.4

Any Phase 11.2 implementation should preserve this baseline except for
intentional test additions.

------------------------------------------------------------------------

## 16. Current Git / Deployment Checkpoint

**Branch**

`feature/plugin-sdk`

**Important Phase 11 commits**

-   `8432597` - `feat: add database backend configuration`
-   `7891f32` - `feat: add postgresql database backend`
-   `0a94b67` -
    `fix: synchronize runtime dependencies during deployment`

**Current full revision**

`0a94b67811f1c6ecd44fbfd1bcc982c07890e97e`

At the end of the checkpoint:

-   local repository matches remote
-   deployed release matches source
-   worktree is clean
-   HIMP remains operational on SQLite

------------------------------------------------------------------------

## 17. Next Start Point

The next development target is:

**Phase 11.2.1 - Database Capability Boundary**

The first implementation slice should use the reconnaissance findings to
introduce the smallest backend-neutral interfaces needed to eliminate
direct repository dependence on:

-   `PRAGMA table_info`
-   `cursor.lastrowid`
-   SQLite-specific transaction acquisition
-   backend-specific integrity exceptions

Do not cut production over to PostgreSQL during this slice.

The implementation should be completed end-to-end before running the
relevant focused tests and full regression suite, consistent with the
established HIMP development workflow.

------------------------------------------------------------------------

## 18. Checkpoint Status

**Phase 11.1 foundation:** COMPLETE\
**PostgreSQL infrastructure:** COMPLETE\
**PostgreSQL authenticated connectivity:** COMPLETE\
**Database backend configuration:** COMPLETE\
**Psycopg backend foundation:** COMPLETE\
**Runtime dependency deployment synchronization:** COMPLETE\
**Production PostgreSQL cutover:** NOT STARTED\
**Phase 11.2 compatibility reconnaissance:** COMPLETE\
**Next target:** Phase 11.2.1 Database Capability Boundary

This document is the recovery and continuation checkpoint for Phase 11
database modernization as of 2026-08-16.
