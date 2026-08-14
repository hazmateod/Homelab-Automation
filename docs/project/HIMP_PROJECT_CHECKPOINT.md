# HIMP Project Checkpoint — Phase 6 Orchestration

**Checkpoint date:** 2026-08-14
**Branch:** `feature/plugin-sdk`
**Latest confirmed commit:** `97056fb` — `feat: correlate workflow execution history`
**Remote:** `origin/feature/plugin-sdk` synchronized to `97056fb`
**Working tree:** clean at last confirmed checkpoint
**Latest full regression:** `431 passed`
**Current phase:** Phase 6 — Orchestration
**Overall Phase 6 status:** IN PROGRESS

## 1. Purpose

This is the authoritative working checkpoint for the current HIMP development state. It records completed work, remaining work, architectural decisions, regression status, and the exact next-session starting point.

Older roadmap statements saying Phase 6 should wait for Phase 5.20 are historical. Phase 5.20 production hardening was completed and Phase 6 is already in progress.

## 2. Production Foundation

**Status: COMPLETE**

Completed foundation includes:

- Authentication and authorization foundation
- Password policy and password management
- Server-side sessions
- Protected API/dashboard surfaces
- HIMP service identity `himp:himp`
- Dedicated HIMP SSH identity
- Centralized API error handling
- Security event logging
- Git-managed deployment
- Git-managed systemd units
- Production hardening
- Deployment/release validation
- Runtime database validation
- Deployment idempotence validation
- Full regression validation

## 3. Phase 6 — Orchestration

**Status: IN PROGRESS**
**Original estimate: 18–28 hours**

### Architectural rule

> Do not create a second execution framework.

Workflow orchestration must reuse the existing automation execution engine, including execution, retry behavior, timeout behavior, dependency handling, execution history, and failure handling.

## 4. Phase 6.1 — Workflow Model

**Status: COMPLETE**

Completed:

- Workflow repository
- Workflow service
- Workflow CRUD API
- Workflow task definitions
- Task ordering
- Workflow dependencies
- Dependency validation
- Dependency-cycle detection
- Execution ordering
- Workflow API validation
- Workflow execution service foundation

Conceptually:

```text
Workflow
   |
   +-- Task A
   |
   +-- Task B
   |
   +-- Task C
          |
          +-- dependencies
```

## 5. Phase 6.2 — Workflow Execution

**Status: COMPLETE**

### 6.2.1 — Execution service

Commit:

```text
c5f89fb
feat: add workflow execution service
```

The service:

- Resolves workflow execution order
- Executes tasks through `AutomationService`
- Passes execution limits
- Passes confirmation state
- Reuses the existing automation execution engine
- Returns individual task execution results
- Preserves existing automation behavior

No second retry/timeout engine was created.

### 6.2.2 — Execution failure contract

Commit:

```text
7f866b8
feat: handle workflow execution failures
```

The workflow engine explicitly handles successful tasks, failed tasks, execution exceptions, direct and transitive failed dependencies, independent branches, skipped tasks, and failure reporting.

Expected behavior:

```text
Task A fails
    |
    +-- Task B depends on A
    |      └── SKIP
    |
    +-- Task C depends on B
           └── SKIP

Task D is independent
    └── CONTINUE
```

### 6.2.3 — Workflow execution API

Commit:

```text
65146fb
feat: add workflow execution API
```

Added:

```text
POST /api/workflows/{workflow_id}/execute
```

Supports:

- `limit`
- `confirmed`
- Workflow execution results
- Failed tasks
- Skipped tasks
- Individual execution results
- Not-found handling
- Invalid execution handling

The API test suite reached 32 tests and the full regression reached 422 passing tests at that checkpoint.

## 6.3 — Workflow History

**Status: IN PROGRESS — correlation foundation COMPLETE**

The original history requirement includes workflow execution, task execution, success/failure, failed tasks, timing, history, and reuse of existing execution records.

### 6.3.4 — Execution correlation

Commit:

```text
97056fb
feat: correlate workflow execution history
```

Every workflow execution receives one unique:

```text
workflow_execution_id
```

The ID is generated once at workflow execution start, and every task in that workflow receives the same correlation ID.

Example:

```text
Workflow Run
    ID = 7c1...abc

       |
       +-- inventory_refresh
       |      workflow_execution_id = 7c1...abc
       |
       +-- generate_reports
       |      workflow_execution_id = 7c1...abc
       |
       +-- health_check
              workflow_execution_id = 7c1...abc
```

### Database support

`automation_executions` now supports `workflow_execution_id`.

Existing databases are upgraded automatically when the column does not exist. This is a lightweight schema migration and does not require a destructive database rebuild.

### Repository support

Implemented:

- Correlation-aware `save()`
- Correlation filtering
- `workflow_history()`
- Existing task-history preservation
- Optional correlation ID for standalone automation executions

### Retry support

Retry attempts preserve the same workflow correlation ID.

```text
Workflow
   |
   +-- Task A
        |
        +-- attempt 1
        +-- attempt 2
        +-- attempt 3
```

All attempts remain associated with the same workflow execution.

### Validation

The correlation slice reached:

**431 tests passing**

with:

- compile: PASS
- `git diff --check`: PASS
- clean repository
- local/remote synchronization: PASS

## 7. Remaining Phase 6.3 Work

### 6.3.5 — Workflow history service/API

Expose a coherent workflow-level history model and reuse `workflow_execution_id`.

Required information:

- Workflow execution ID
- Workflow
- Execution timestamp
- Overall success/failure
- Task count
- Executed tasks
- Failed tasks
- Skipped tasks
- Individual task executions
- Attempt information
- Elapsed time
- Error information

### 6.3.6 — History API

Provide a stable API for retrieving workflow execution history.

### 6.3.7 — History tests

Cover:

- Successful workflow history
- Failed workflow history
- Skipped dependent tasks
- Independent branches
- Multiple workflow runs
- Multiple retries
- Workflow/task correlation
- Empty history
- History ordering
- Limits/filtering

**Estimated remaining effort: approximately 2–3 hours.**

## 8. Phase 6.4 — Workflow Dashboard

**Status: NOT STARTED**
**Original estimate: 4–6 hours**

Expose:

- Workflow
- Current state
- Current task
- Failed task
- Execution history

The dashboard must consume workflow execution/history services and must not implement its own execution or history logic.

## 9. Phase 6 Summary

| Area | Status | Original Effort | Remaining |
|---|---|---:|---:|
| 6.1 Workflow Model | COMPLETE | 4–6h | — |
| 6.2 Workflow Execution | COMPLETE | 5–8h | — |
| 6.3 Workflow History | IN PROGRESS | 3–4h | ~2–3h |
| 6.4 Workflow Dashboard | NOT STARTED | 4–6h | 4–6h |
| **Phase 6** | **IN PROGRESS** | **18–28h** | **~6–9h** |

## 10. Future Roadmap

### Phase 7 — Infrastructure Intelligence

**18–28 hours**

1. Asset relationships
2. Infrastructure change detection
3. Health correlation
4. Drift/baselines

Keep the first version deterministic and explainable.

### Phase 8 — Automation Intelligence

**18–28 hours**

1. Remediation policies
2. Low-risk remediation
3. Approval controls
4. Verification
5. Remediation history

Reuse the existing automation policy/execution framework.

### Phase 9 — Operational Platform

**20–30 hours**

1. Unified dashboard
2. Operational reports
3. HIMP self-health
4. Disaster recovery documentation
5. Release/upgrade process

## 11. Current Remaining Effort

| Work | Remaining |
|---|---:|
| Phase 6.3 | 2–3h |
| Phase 6.4 | 4–6h |
| Phase 6 total | 6–9h |
| Phase 7 | 18–28h |
| Phase 8 | 18–28h |
| Phase 9 | 20–30h |
| **Overall remaining** | **62–95h** |

At approximately 8 hours/week: **~8–12 weeks**. This is a planning estimate, not a commitment.

## 12. Development Rules

1. Complete one subsystem end-to-end before moving on.
2. One completed working slice per commit.
3. Avoid duplicate logic.
4. Reuse existing execution infrastructure.
5. Do not create a second retry/timeout engine.
6. Use focused tests during development.
7. Run the full regression suite before checkpoints.
8. Run Python compile checks on changed modules.
9. Run `git diff --check`.
10. Inspect the final diff before committing.
11. Keep the working tree clean at checkpoints.
12. Push completed commits to origin.
13. Verify local and remote commit hashes match.
14. Do not guess when repository output can establish the fact.
15. Prefer direct replacements and command-by-command implementation.
16. Do not move to the next subsystem while the current subsystem is failing.

## 13. Current Git Checkpoint

```text
Branch:
feature/plugin-sdk

Latest confirmed commit:
97056fb

Commit:
feat: correlate workflow execution history

Remote:
origin/feature/plugin-sdk

Last confirmed:
LOCAL == REMOTE

Working tree:
clean

Latest confirmed full regression:
431 passed
```

## 14. Exact Next-Session Starting Point

Do not begin Phase 6.4 yet.

Complete the remaining workflow-history slice first:

```text
1. Inspect existing workflow history/repository APIs
2. Define the workflow-history response contract
3. Add focused repository/service tests
4. Implement workflow history service
5. Add workflow history API
6. Add API tests
7. Run focused workflow-history tests
8. Run full regression
9. Compile changed modules
10. Run git diff --check
11. Review diff
12. Commit the completed slice
13. Push to origin
14. Verify local == remote
```

Immediate target:

> Finish Phase 6.3 Workflow History without creating duplicate history infrastructure.

Then:

```text
6.4 Workflow Dashboard
        ↓
Phase 6 COMPLETE
        ↓
Phase 7 Infrastructure Intelligence
```

## 15. Documentation Policy

This document should be maintained in the HIMP repository as the authoritative current checkpoint.

Do not create competing checkpoint documents for the same project state.

When a major phase or working slice closes:

1. Update this document.
2. Record the actual commit.
3. Record the actual regression count.
4. Record remaining work.
5. Record the next-session starting point.
6. Commit the documentation separately when appropriate.
7. Push it to the project remote.

The purpose is continuity: a future session should be able to resume HIMP from this document without reconstructing the project state from conversation history.
