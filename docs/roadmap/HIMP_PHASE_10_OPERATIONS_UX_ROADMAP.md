# HIMP Phase 10 — Operations & UX Refinement Roadmap

**Document date:** 2026-08-16
**Project:** Homelab Infrastructure Management Platform (HIMP)
**Repository:** `Homelab-Automation`
**Branch:** `feature/plugin-sdk`
**Phase 9 final documentation checkpoint:** `0706926` — `docs: record phase 9.10 production validation`
**Production-validated application release:** `52edd9f5f34c9356de09091115c773d7d4da9984`
**Phase 9 status:** COMPLETE
**Phase 10 status:** PLANNED
**Estimated Phase 10 effort:** 14–25 hours

---

# 1. Purpose

Phase 10 begins after successful completion of the Phase 9 production gate.

Phase 9 established and production-validated the major HIMP platform
capabilities, including:

- authentication and authorization
- user management
- infrastructure inventory
- infrastructure health
- automation execution
- scheduler reliability
- operational reporting
- PDF/TXT/CSV report exports
- operational log viewing/export
- application self-health
- remediation safety
- disaster-recovery validation
- release/upgrade/rollback procedures
- production deployment traceability
- browser-driven host updates
- production Scheduled Updates across the complete 43-host inventory

Phase 10 is intentionally different from the earlier feature-heavy phases.

Its purpose is to improve operational usability, eliminate known technical
debt, improve visibility into long-running work, and refine production
operator experience without destabilizing the now-working automation and
scheduler subsystems.

The guiding principle is:

```text
Preserve proven production behavior.
Improve visibility, maintainability, and operator experience around it.
```

---

# 2. Phase 10 Development Rules

The following implementation rules continue to apply.

## 2.1 One subsystem per subphase

Each Phase 10 subphase should have a clearly bounded purpose.

Avoid combining unrelated cleanup, UX, scheduler, reporting, and CMDB
changes into a single implementation slice.

## 2.2 Complete the implementation slice before testing

Build each coherent slice end-to-end first.

Then run:

```text
focused regression
full regression
compileall
git diff --check
```

Do not repeatedly interrupt implementation with unnecessary test cycles.

## 2.3 One completed subphase per commit where practical

Each completed Phase 10 subphase should produce a clear Git checkpoint.

Example:

```text
Phase 10.1 implementation
        ↓
regression
        ↓
production validation
        ↓
commit
        ↓
push
```

## 2.4 Production validation remains mandatory

Phase 9 demonstrated that automated tests can pass while a real systemd
sandbox or privilege context still exposes a production defect.

Any Phase 10 work affecting runtime behavior must therefore include an
appropriate production smoke test.

## 2.5 Avoid unnecessary refactors

Do not refactor production code merely because a different structure might
look cleaner.

Refactor when:

- duplication is real
- maintenance risk is reduced
- a test exposes a genuine defect
- the new Phase 10 feature requires a clean shared boundary

## 2.6 Preserve scheduler/update reliability

The Scheduled Updates production path is now proven.

Do not redesign or substantially modify that execution path unless a
specific Phase 10 requirement demands it.

---

# 3. Phase 10 Overview

```text
Phase 10.1  Automation Progress & Execution UX       4–7h
Phase 10.2  Python Deprecation / Warning Cleanup     2–4h
Phase 10.3  CMDB Security & Monitoring Completion    3–6h
Phase 10.4  Recent Activity / History UX             3–5h
Phase 10.5  Production Refinement Gate               2–3h
                                                    -----
Estimated total                                    14–25h
```

Recommended execution order:

```text
10.1
 ↓
10.2
 ↓
10.3
 ↓
10.4
 ↓
10.5
```

---

# 4. Phase 10.1 — Automation Progress & Execution UX

## Status: NEXT

**Estimated effort:** 4–7 hours
**Priority:** HIGH
**Risk:** MEDIUM
**Production value:** HIGH

## 4.1 Problem

The production Scheduled Updates validation proved that the automation
works correctly, but it can run for roughly 20–30 minutes.

During execution, the operator receives insufficient feedback.

This can make a healthy long-running automation appear hung.

The operator should not have to inspect systemd journals to determine
whether an automation is still progressing.

## 4.2 Goal

Improve execution visibility without redesigning the working automation
engine.

The HIMP UI should clearly distinguish:

```text
Queued
Running
Successful
Failed
```

and provide useful runtime information while work is in progress.

## 4.3 Proposed Capabilities

### 10.1.1 Running-State Visibility

Show a clear running state immediately after execution begins.

Possible UI:

```text
Scheduled Updates
Status: Running
Started: 10:02:14
Elapsed: 08m 42s
```

The Run button should be disabled or replaced while the same automation is
actively executing.

### 10.1.2 Elapsed Time

Expose:

```text
started_at
elapsed_seconds
```

or derive elapsed time safely from existing execution data.

The UI should update elapsed time while an execution is active.

### 10.1.3 Execution Stage / Progress Message

Where the existing execution engine can provide meaningful state without
major redesign, expose a current or last-known stage.

Examples:

```text
Starting automation
Running host maintenance
Generating host reports
Generating dashboard
Finalizing execution
```

This does not require an artificial percentage if the backend cannot
accurately calculate one.

Prefer truthful stage information over a misleading progress bar.

### 10.1.4 Completion Feedback

When the execution completes, show:

```text
Successful
Completed: <timestamp>
Duration: <elapsed>
```

or:

```text
Failed
Completed: <timestamp>
Duration: <elapsed>
Error: <safe summarized error>
```

### 10.1.5 Duplicate Execution Protection UX

If occurrence/locking protection already rejects duplicate execution, make
that state understandable in the UI.

Do not allow operators to accidentally launch multiple copies merely
because the first execution appears inactive.

### 10.1.6 Execution Detail Link

Where practical, allow the operator to open the associated execution
record/history entry from the automation card.

## 4.4 Initial Reconnaissance

Before implementation, inspect:

- automation database schema
- automation execution repository
- automation service
- scheduler service
- `/api/automation` endpoints
- Automation page HTML/templates
- dashboard JavaScript
- existing polling behavior
- existing execution status fields
- execution lock/occurrence behavior

The design should reuse existing persisted execution data wherever
possible.

## 4.5 Expected Tests

Coverage should include:

- running execution serialization
- completed execution serialization
- failed execution serialization
- elapsed-time handling
- active execution API behavior
- duplicate-run behavior
- automation page state
- safe error display
- backward compatibility with historical execution records

## 4.6 Production Validation

Production smoke test:

1. Launch Scheduled Updates once.
2. Confirm immediate Running state.
3. Confirm duplicate Run action is unavailable or safely rejected.
4. Confirm elapsed time advances.
5. Confirm useful execution stage/status is displayed.
6. Allow the automation to complete.
7. Confirm Successful state.
8. Confirm execution history is preserved.
9. Confirm dashboard remains PASS.

## 4.7 Definition of Done

```text
[ ] Running state visible
[ ] Start time visible
[ ] Elapsed time visible
[ ] Useful progress/stage information available where supportable
[ ] Duplicate execution UX safe
[ ] Completion state visible
[ ] Failure state visible
[ ] Existing scheduler behavior preserved
[ ] Focused tests pass
[ ] Full regression passes
[ ] compileall passes
[ ] git diff --check passes
[ ] Production smoke test passes
[ ] Documentation updated
[ ] Commit pushed
```

---

# 5. Phase 10.2 — Python Deprecation / Warning Cleanup

## Status: PLANNED

**Estimated effort:** 2–4 hours
**Priority:** MEDIUM
**Risk:** LOW
**Production value:** MEDIUM

## 5.1 Problem

The Phase 9.10 regression completed with:

```text
674 passed
11 warnings
```

The warnings originate from use of:

```python
datetime.utcnow()
```

in:

```text
himp/database/inventory.py
```

Python warns that `datetime.utcnow()` is deprecated and scheduled for
future removal.

## 5.2 Goal

Move affected timestamp handling to timezone-aware UTC values without
changing HIMP's persistence semantics or breaking existing records.

## 5.3 Proposed Work

Inspect all uses of:

```text
datetime.utcnow
datetime.now
UTC timestamp conversion
ISO timestamp serialization
SQLite timestamp persistence
```

Do not blindly replace calls.

First determine how timestamps are stored and consumed across:

- inventory changes
- health history
- automation executions
- scheduler history
- workflow history
- reports
- API serialization

Then update the affected implementation consistently.

## 5.4 Compatibility Requirement

Existing database records must remain readable.

If existing timestamps are naive UTC strings, migration behavior must be
explicitly understood before changing serialization.

Avoid introducing a schema migration solely for cosmetic cleanup unless
required for correctness.

## 5.5 Expected Tests

Tests should verify:

- new timestamps represent UTC
- serialization remains stable
- existing stored timestamps remain readable
- ordering remains correct
- inventory-change history remains correct
- restored-host history remains correct
- no new timezone comparison exceptions occur

## 5.6 Definition of Done

Target:

```text
Full regression:
all tests passed

datetime.utcnow deprecation warnings:
0
```

Checklist:

```text
[ ] Timestamp usage inventoried
[ ] Compatibility reviewed
[ ] Deprecated calls removed
[ ] Existing database compatibility preserved
[ ] Focused timestamp/history tests pass
[ ] Full regression passes
[ ] compileall passes
[ ] git diff --check passes
[ ] Documentation updated
[ ] Commit pushed
```

---

# 6. Phase 10.3 — CMDB Security & Monitoring Completion

## Status: PLANNED

**Estimated effort:** 3–6 hours
**Priority:** MEDIUM
**Risk:** MEDIUM
**Production value:** MEDIUM

## 6.1 Problem

Production Scheduled Updates completes successfully but Ansible currently
reports warnings that these task files are empty:

```text
roles/cmdb/tasks/security.yml
roles/cmdb/tasks/monitoring.yml
```

The warnings do not cause execution failure.

However, permanently empty task files create ambiguity:

- are the files intentional placeholders?
- are security/monitoring capabilities incomplete?
- should they be removed?
- should meaningful CMDB data be collected?

## 6.2 Goal

Resolve the ambiguity intentionally.

Do not merely suppress the warnings.

Determine whether the existing CMDB/report model expects security and
monitoring information.

## 6.3 Reconnaissance

Inspect:

- `roles/cmdb`
- CMDB templates
- report JSON schema
- current Markdown reports
- dashboard host model
- health plugins
- inventory variables
- existing security data sources
- existing monitoring data sources

## 6.4 Decision Point

After reconnaissance choose one of two supported paths.

### Path A — Implement the intended data

If the HIMP data model already expects these sections, implement safe,
portable collection.

Possible security information could include:

```text
firewall availability/state
automatic update state
SSH service state
failed systemd services
security update counts
```

Possible monitoring information could include:

```text
monitoring agent presence
HIMP health status
uptime
load
service health
```

Only collect data that is reliable across the supported hosts.

### Path B — Remove unused placeholders

If no production consumer expects these sections, remove the empty
includes/files cleanly and document that they are not currently part of
the CMDB contract.

## 6.5 Safety

This phase is primarily observational.

CMDB collection must not change host configuration.

## 6.6 Definition of Done

```text
[ ] Empty-file intent determined
[ ] Security CMDB behavior explicit
[ ] Monitoring CMDB behavior explicit
[ ] Empty task warnings eliminated
[ ] No host configuration changed by collection
[ ] Report compatibility preserved
[ ] Focused tests pass
[ ] Full regression passes
[ ] compileall passes
[ ] git diff --check passes
[ ] Production report generation passes
[ ] Documentation updated
[ ] Commit pushed
```

---

# 7. Phase 10.4 — Recent Activity / History UX

## Status: PLANNED

**Estimated effort:** 3–5 hours
**Priority:** MEDIUM
**Risk:** LOW–MEDIUM
**Production value:** MEDIUM–HIGH

## 7.1 Problem

The production dashboard correctly reports current Operational Status as
PASS while Recent Activity can still display old failed executions.

That behavior is technically correct but can be confusing.

An operator may interpret a historical failure as evidence of a current
platform problem.

## 7.2 Goal

Make the distinction between:

```text
current health
```

and:

```text
historical execution result
```

immediately obvious.

## 7.3 Proposed Improvements

### 10.4.1 Clear Historical Context

Recent Activity should clearly communicate that records are historical.

Possible labels:

```text
Recent Activity
Historical Executions
Last Executions
```

### 10.4.2 Relative and Absolute Time

Where useful, display:

```text
18 minutes ago
Aug 16, 2026 10:13
```

without losing the exact timestamp.

### 10.4.3 Filtering

Consider filters such as:

```text
All
Failures
Successful
Automation
Workflow
Plugin
Remediation
```

Keep the first implementation small if the current API does not support
efficient filtering.

### 10.4.4 Current-Failure Emphasis

If an execution failure is currently relevant to operational health, make
that relationship explicit.

Do not visually elevate an old resolved failure to the same severity as a
current active problem.

### 10.4.5 Execution Detail

Where existing APIs support it, allow operators to inspect:

- execution type
- status
- start/completion time
- duration
- return code
- safe error summary

## 7.4 Data Retention

This phase should not delete historical records merely to make the
dashboard look cleaner.

Historical failures are operationally valuable.

Improve presentation rather than erasing evidence.

## 7.5 Definition of Done

```text
[ ] Historical activity clearly identified
[ ] Current health remains distinct
[ ] Failure presentation is understandable
[ ] Useful timestamps shown
[ ] Filtering implemented where justified
[ ] Historical records preserved
[ ] Focused tests pass
[ ] Full regression passes
[ ] compileall passes
[ ] git diff --check passes
[ ] Production UI smoke test passes
[ ] Documentation updated
[ ] Commit pushed
```

---

# 8. Phase 10.5 — Production Refinement Gate

## Status: PLANNED

**Estimated effort:** 2–3 hours
**Priority:** HIGH
**Risk:** LOW
**Production value:** HIGH

Phase 10.5 is the final Phase 10 production checkpoint.

It should not introduce a major feature.

## 8.1 Automated Gate

Run:

```text
full regression
compileall
git diff --check
deployment regression
```

Confirm no unexpected warning regressions.

## 8.2 Repository Gate

Verify:

```text
working tree clean
LOCAL == REMOTE
expected deployed release recorded
```

## 8.3 Runtime Gate

Verify:

```text
himp.service active
listener active
scheduler timer active
application health PASS
```

## 8.4 Functional Smoke Tests

Validate:

- login/logout
- dashboard
- inventory
- host update
- Automation page
- automation execution progress UX
- reports
- PDF/TXT/CSV export
- logs
- user management
- application health
- scheduler status
- Recent Activity/history behavior

A complete 43-host Scheduled Updates run is only required if Phase 10
changes affect that path materially. Otherwise use a smaller safe
production execution to avoid unnecessary maintenance churn.

## 8.5 Recovery / Release Review

Confirm Phase 9 artifacts remain valid:

```text
Phase 9.8 disaster recovery
Phase 9.9 release/upgrade/rollback runbook
```

No new restore test is required unless Phase 10 changes the recovery
contract.

## 8.6 Final Documentation

Create the next versioned completion checkpoint recording:

- Phase 10 changes
- test count
- warning count
- production validation
- commits
- deployed release
- deferred work
- next roadmap

## 8.7 Definition of Done

```text
[ ] Full regression passes
[ ] compileall passes
[ ] git diff --check passes
[ ] Deployment regression passes
[ ] Warning state reviewed
[ ] Repository clean
[ ] LOCAL == REMOTE
[ ] Deployment identity verified
[ ] HIMP active
[ ] Scheduler active
[ ] Application health PASS
[ ] Critical UI smoke tests pass
[ ] Phase 10.1 behavior production verified
[ ] Phase 10.2 behavior verified
[ ] Phase 10.3 behavior verified
[ ] Phase 10.4 behavior verified
[ ] DR documentation still valid
[ ] Release runbook still valid
[ ] Final checkpoint committed
[ ] Final checkpoint pushed
```

---

# 9. Effort Summary

| Phase | Scope | Estimate | Priority | Risk |
|---|---|---:|---|---|
| 10.1 | Automation Progress & Execution UX | 4–7h | High | Medium |
| 10.2 | Python Deprecation / Warning Cleanup | 2–4h | Medium | Low |
| 10.3 | CMDB Security & Monitoring Completion | 3–6h | Medium | Medium |
| 10.4 | Recent Activity / History UX | 3–5h | Medium | Low–Medium |
| 10.5 | Production Refinement Gate | 2–3h | High | Low |
| **Total** | **Phase 10** | **14–25h** |  |  |

The estimates assume the existing architecture can be reused and that
Phase 10 does not uncover another production-only defect comparable to the
Phase 9.10 systemd/Ansible issues.

---

# 10. Suggested Session Breakdown

For practical working sessions:

```text
Session 1
Phase 10.1 reconnaissance + backend execution-state work
2–4h

Session 2
Phase 10.1 UI/polling + tests + production validation
2–3h

Session 3
Phase 10.2 timestamp/deprecation cleanup
2–4h

Session 4
Phase 10.3 CMDB reconnaissance + implementation
3–6h

Session 5
Phase 10.4 activity/history UX
3–5h

Session 6
Phase 10.5 final gate + documentation
2–3h
```

Sessions may be combined if work proceeds cleanly.

---

# 11. Deferred / Future Candidates

The following are reasonable candidates for Phase 11 or later and should
not automatically expand Phase 10:

- notification integrations
- email notifications
- Slack/Teams notifications
- richer alert routing
- advanced maintenance windows
- host grouping/tag management
- richer role-based UI permissions
- API tokens/service accounts
- external identity provider integration
- multi-user audit dashboards
- richer charts/trending
- backup orchestration beyond the validated DR documentation
- additional infrastructure plugins
- mobile-focused UI
- WebSocket/SSE execution streaming if polling proves insufficient
- database migration framework if schema evolution becomes significant
- HA HIMP application deployment

These should be prioritized only after Phase 10 refinement is complete.

---

# 12. Exact Phase 10 Starting Point

Start Phase 10 from the Phase 9 completion checkpoint:

```text
0706926 — docs: record phase 9.10 production validation
```

The production-validated application release remains:

```text
52edd9f5f34c9356de09091115c773d7d4da9984
```

Because `0706926` is documentation-only, it is correct for the deployed
release marker to remain at `52edd9f`.

Before Phase 10.1 implementation begins:

```bash
cd /root/Homelab-Automation

git status --short --branch
git fetch origin

echo "LOCAL=$(git rev-parse HEAD)"
echo "REMOTE=$(git rev-parse origin/feature/plugin-sdk)"
echo "DEPLOYED=$(cat /opt/himp/.himp-release)"

systemctl is-active himp.service
systemctl is-active himp-scheduler.timer
```

Expected starting contract:

```text
LOCAL == REMOTE
working tree clean
himp.service active
himp-scheduler.timer active
production dashboard PASS
```

Then begin Phase 10.1 with read-only reconnaissance of the existing
automation execution state and UI.

---

# 13. Phase 10 Tracking Checklist

```text
PHASE 10 — OPERATIONS & UX REFINEMENT

10.1 Automation Progress & Execution UX
[ ] Reconnaissance
[ ] Design
[ ] Backend
[ ] API
[ ] UI
[ ] Regression
[ ] Production validation
[ ] Commit/push

10.2 Python Deprecation / Warning Cleanup
[ ] Timestamp inventory
[ ] Compatibility review
[ ] Implementation
[ ] Regression
[ ] Warning verification
[ ] Commit/push

10.3 CMDB Security & Monitoring Completion
[ ] Reconnaissance
[ ] Implementation/removal decision
[ ] Implementation
[ ] Report validation
[ ] Regression
[ ] Production validation
[ ] Commit/push

10.4 Recent Activity / History UX
[ ] Reconnaissance
[ ] Design
[ ] Implementation
[ ] Regression
[ ] Production UI validation
[ ] Commit/push

10.5 Production Refinement Gate
[ ] Full regression
[ ] compileall
[ ] git diff --check
[ ] Deployment regression
[ ] Repository gate
[ ] Runtime gate
[ ] UI smoke tests
[ ] Recovery/release review
[ ] Final documentation
[ ] Commit/push

PHASE 10
[ ] COMPLETE
```

---

# 14. Closing Recommendation

The immediate next target is:

```text
Phase 10.1 — Automation Progress & Execution UX
```

Do not begin by changing the scheduler or Scheduled Updates implementation.

First inspect the existing execution persistence, APIs, and Automation page
to determine what progress information already exists.

The preferred Phase 10.1 design should add visibility around the proven
execution engine rather than replace it.

This preserves the strongest outcome from Phase 9:

```text
The automation works.
Phase 10 should make it obvious that it is working.
```
