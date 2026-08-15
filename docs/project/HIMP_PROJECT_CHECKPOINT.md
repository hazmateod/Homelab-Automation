# HIMP Project Checkpoint — Phase 6 Orchestration

**Checkpoint date:** 2026-08-14
**Branch:** `feature/plugin-sdk`
**Latest confirmed commit:** `93283e6` — `feat: add workflow execution history`
**Remote:** `origin/feature/plugin-sdk` synchronized to `93283e6`
**Working tree:** clean at last confirmed checkpoint
**Latest full regression:** `460 passed`
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

## 7. Phase 6.3 — Workflow History

**Status: COMPLETE**

Completed the workflow history vertical slice without creating duplicate execution infrastructure.

### 6.3.5 — Workflow History Service

Implemented `WorkflowHistoryService` as a read-only composition layer over the existing workflow, workflow-execution, and automation-execution repositories.

The service exposes workflow-run metadata together with correlated task execution history using `workflow_execution_id`.

### 6.3.6 — History API

Added:

```text
GET /workflows/{workflow_id}/history
GET /workflows/{workflow_id}/history/{workflow_execution_id}
```

The API returns workflow-run metadata and the existing correlated task execution records.

### 6.3.7 — History Tests

Added repository, service, API, and workflow-execution failure-path coverage.

Final full regression:

```text
460 passed in 2.29s
```

The workflow execution lifecycle now persists the workflow run at start, completes it on normal execution, and marks it failed before re-raising orchestration exceptions.

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
| 6.3 Workflow History | COMPLETE | 3–4h | — |
| 6.4 Workflow Dashboard | NOT STARTED | 4–6h | 4–6h |
| **Phase 6** | **IN PROGRESS** | **18–28h** | **4–6h** |

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
| Phase 6.3 | — |
| Phase 6.4 | 4–6h |
| Phase 6 total | 4–6h |
| Phase 7 | 18–28h |
| Phase 8 | 18–28h |
| Phase 9 | 20–30h |
| **Overall remaining** | **60–92h** |

At approximately 8 hours/week: **~7.5–11.5 weeks**. This is a planning estimate, not a commitment.

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
93283e6

Commit:
feat: add workflow execution history

Remote:
origin/feature/plugin-sdk

Last confirmed:
LOCAL == REMOTE

Working tree:
clean

Latest confirmed full regression:
460 passed
```

## 14. Exact Next-Session Starting Point

Begin Phase 6.4 — Workflow Dashboard.

Phase 6.3 Workflow History is complete, committed, pushed, and synchronized with origin.

Immediate target:

> Review the existing dashboard architecture and define the dashboard view that consumes the completed workflow execution/history services.

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
