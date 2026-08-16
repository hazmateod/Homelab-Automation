# HIMP Phase 11.6.2 --- Migration CLI and Isolated Rehearsal Completion

**Project:** Homelab Infrastructure Management Platform (HIMP)\
**Repository:** `Homelab-Automation`\
**Branch:** `feature/plugin-sdk`\
**Phase:** 11.6.2\
**Status:** COMPLETE / ISOLATED REHEARSAL VALIDATED / COMMITTED\
**Date:** 2026-08-16\
**Commit:** `cb85d35` --- `feat: add isolated PostgreSQL migration CLI`

## 1. Objective

Phase 11.6.2 added the operator-facing SQLite-to-PostgreSQL migration
command and completed a real isolated rehearsal of the migration engine.

Objectives:

-   Provide a controlled CLI entry point for SQLite-to-PostgreSQL
    migration.
-   Make rehearsal the safe default.
-   Require explicit `--execute` for a real migration.
-   Preserve SQLite as the rollback source.
-   Prevent accidental writes to the production PostgreSQL schema during
    rehearsal.
-   Support an isolated PostgreSQL schema for controlled migration
    testing.
-   Validate the complete migration path using the real CLI.
-   Ensure the CLI uses the same virtual environment as the production
    HIMP runtime.
-   Release process-local PostgreSQL pools when the CLI exits.

Production PostgreSQL cutover was intentionally **not** performed during
this phase.

## 2. Migration CLI

New commands:

``` text
./bin/himp migration
./bin/himp migration --execute
```

Behavior:

-   Without `--execute`, migration runs in **REHEARSAL** mode.
-   With `--execute`, migration performs the actual migration.
-   The command requires PostgreSQL as the configured target backend.
-   Migration failures return a non-zero exit status.
-   Database and PostgreSQL pool cleanup occurs during command shutdown.

Successful rehearsal:

``` text
Starting SQLite to PostgreSQL migration REHEARSAL...

Migration mode     : REHEARSAL
Tables processed    : 20
Rows processed      : 11742
Migration rehearsal completed successfully. PostgreSQL changes were rolled back.
```

## 3. CLI Runtime Correction

The first real CLI attempt exposed an environment mismatch: `bin/himp`
invoked system `python3`, while PostgreSQL dependencies existed only in
the project virtual environment.

Observed:

``` text
system psycopg=NOT AVAILABLE
venv psycopg=AVAILABLE
PSYCGOPG=3.3.4
```

`bin/himp` was corrected to explicitly use:

``` text
/root/Homelab-Automation/.venv/bin/python
```

The launcher now verifies that the interpreter exists and executes
`himp.cli` through it.

This aligns the CLI with the Python runtime already used by the HIMP
systemd services.

## 4. PostgreSQL Schema Isolation

Database configuration now supports:

``` text
HIMP_DATABASE_SCHEMA
```

Default:

``` text
public
```

The configured schema is included in the PostgreSQL pool key, preventing
different schemas from accidentally sharing a pool.

PostgreSQL connections use the configured schema through `search_path`,
and schema names are validated before pool creation.

Custom-schema configuration and invalid schema handling have regression
coverage.

## 5. Isolated Rehearsal Environment

A dedicated PostgreSQL schema was created:

``` text
phase_11_6_2_rehearsal_1786912573
```

The expected 20 HIMP tables were created in that schema:

``` text
asset_relationships
automation_dependencies
automation_executions
automation_locks
automation_schedules
discovery
executions
health_history
host_health_history
inventory_baselines
inventory_changes
inventory_hosts
remediation_audit
remediation_operations
sessions
users
workflow_dependencies
workflow_executions
workflow_tasks
workflows
```

Initial validation:

``` text
total_rows=0
target_schema_validation=PASS
target_empty_validation=PASS
```

## 6. Production PostgreSQL Protection

Production counts before rehearsal:

``` text
inventory_hosts=46
automation_executions=594
host_health_history=10982
inventory_changes=55
sessions=10
users=2
```

The same production counts were verified after rehearsal:

``` text
inventory_hosts=46
automation_executions=594
host_health_history=10982
inventory_changes=55
sessions=10
users=2
```

Therefore the rehearsal did not modify the production `public` schema.

## 7. Real CLI Isolated Rehearsal

The actual CLI was used:

``` text
./bin/himp migration
```

against the isolated schema.

Results:

``` text
Tables processed : 20
Rows processed   : 11742
```

The migration transaction was successfully rolled back.

Post-rehearsal isolated counts remained:

``` text
inventory_hosts=0
automation_executions=0
host_health_history=0
inventory_changes=0
sessions=0
users=0
```

Result:

``` text
isolated rehearsal transaction rollback = PASS
```

## 8. SQLite Rollback Source Protection

SQLite source:

``` text
/opt/himp/data/himp.db
```

SHA-256 before rehearsal:

``` text
8487f0250086ec65b3795228d51d50331f07a6b4fd92e89bdab5e9aab7a2d2e6
```

SHA-256 after rehearsal:

``` text
8487f0250086ec65b3795228d51d50331f07a6b4fd92e89bdab5e9aab7a2d2e6
```

Result:

``` text
SQLite rollback source unchanged = PASS
```

## 9. PostgreSQL Pool Lifecycle Correction

The first real rehearsal exposed PostgreSQL pool worker-thread shutdown
warnings.

The migration command was corrected to explicitly call:

``` text
PostgreSQLDatabase.close_pools()
```

during cleanup.

Regression coverage was added to verify shared PostgreSQL pools are
closed when the migration command exits.

The final isolated rehearsal completed without the earlier pool-thread
shutdown warnings.

## 10. Final Regression

Migration CLI tests:

``` text
6 passed
```

Database configuration, factory, pool, migration, and schema tests:

``` text
61 passed
```

Deployment tests:

``` text
26 passed
```

Combined focused regression:

``` text
93 passed
```

Static validation:

``` text
bash -n bin/himp       PASS
py_compile             PASS
compileall             PASS
git diff --check       PASS
```

Service safety:

``` text
HIMP=active
SCHEDULER_TIMER=inactive
SCHEDULER=inactive
```

The scheduler remained intentionally stopped throughout this work.

## 11. Files Changed

The committed implementation contains:

``` text
bin/himp
himp/cli.py
himp/commands/migration.py
himp/database/config.py
himp/database/postgresql.py
tests/commands/test_migration.py
tests/database/test_database_config.py
tests/database/test_database_factory.py
tests/database/test_postgresql_pool.py
tests/deployment/test_himp_deployment.py
```

Commit statistics:

``` text
10 files changed
629 insertions
1 deletion
```

## 12. Git Commit

Phase 11.6.2 was committed as:

``` text
cb85d35 feat: add isolated PostgreSQL migration CLI
```

The commit contains the complete implementation and regression coverage.

The next repository action is to push `cb85d35` to:

``` text
origin/feature/plugin-sdk
```

and verify synchronization.

## 13. Documentation Handling

This completion document is intentionally being kept outside the
repository commit for now.

The document should be uploaded back into the project workflow and
committed during the next repository commit, rather than being added
through a long-running interactive document-edit operation.

This avoids the document-write/hang behavior encountered during Phase
11.6.2.

## 14. Current Phase State

Phase 11.6.2 implementation and isolated live rehearsal are complete.

Validated:

-   Migration CLI exists.
-   Rehearsal is the safe default.
-   Explicit `--execute` is required for migration execution.
-   CLI uses the project `.venv`.
-   PostgreSQL schema isolation works.
-   PostgreSQL pools are schema-aware.
-   Migration rehearsal succeeds.
-   20 tables and 11,742 rows were processed.
-   Isolated target remained empty after rollback.
-   Production PostgreSQL remained unchanged.
-   SQLite rollback source remained unchanged.
-   PostgreSQL pool cleanup works during CLI shutdown.
-   Focused regression passes.
-   Deployment regression passes.
-   Static validation passes.
-   HIMP remains active.
-   Scheduler remains stopped.

## 15. Production Cutover Status

**Production SQLite-to-PostgreSQL migration has NOT been executed.**

The following remain unchanged:

-   Production PostgreSQL `public` schema.
-   Production SQLite database.
-   HIMP production service state.
-   Scheduler state.

The isolated rehearsal demonstrates that the migration mechanism is
operational, but it does not authorize production cutover.

## 16. Next Step

Immediate repository tasks:

1.  Push commit `cb85d35`.
2.  Verify local and remote synchronization.
3.  Upload this completion document.
4.  Commit the completion documentation with the next appropriate
    repository change.

After that, determine the next Phase 11 database action from the broader
cutover plan.

The scheduler should remain stopped until production database cutover
has been explicitly planned, executed, and validated.
