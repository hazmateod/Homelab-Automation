# HIMP Phase 10.2 — Python Deprecation / Warning Cleanup Completion Checkpoint

**Document date:** 2026-08-16
**Project:** Homelab Infrastructure Management Platform (HIMP)
**Repository:** `Homelab-Automation`
**Branch:** `feature/plugin-sdk`
**Phase:** 10.2 — Python Deprecation / Warning Cleanup
**Status:** COMPLETE / PRODUCTION VALIDATED
**Implementation commit:** `f03adf6` — `fix: replace deprecated utcnow usage`
**Production release:** `f03adf6245cdfb9b938202feab487b16dc5390f3`
**Latest full regression:** 682 passed, 0 warnings
**Next phase:** Phase 10.3 — CMDB Security & Monitoring Completion
**Estimated next-phase effort:** 3–6 hours

---

# 1. Executive Summary

Phase 10.2 is complete.

The purpose of this phase was to remove Python deprecation warnings caused
by `datetime.utcnow()` without changing HIMP's existing timestamp
persistence semantics.

The Phase 10 roadmap required compatibility with existing database records
and explicitly cautioned against blindly converting database timestamps to
timezone-aware values.

The final implementation removed all six production
`datetime.utcnow()` calls while preserving HIMP's existing naive-UTC
SQLite timestamp representation.

The replacement pattern is:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

This obtains current UTC time using the supported timezone-aware Python API
and then removes timezone metadata at the database boundary so existing
SQLite timestamp behavior remains unchanged.

Final validation:

```text
Focused tests:       28 passed
Full regression:     682 passed
Warnings:            0
compileall:          PASS
utcnow source scan:  NONE
git diff --check:    PASS
Production smoke:    PASS
```

---

# 2. Starting State

Phase 10.2 began after Phase 10.1 was completed, production validated, and
documented.

Starting documentation checkpoint:

```text
5a7dd77 — docs: record phase 10.1 automation execution ux
```

Starting production application release:

```text
af101a683fec8ed6e8f0eb25647bd8ff0d1ca413
```

The repository was clean and synchronized.

The known regression state entering Phase 10.2 was:

```text
681 passed
11 warnings
```

The warnings were Python deprecation warnings involving
`datetime.utcnow()`.

---

# 3. Reconnaissance Findings

A repository-wide source scan identified six production calls to
`datetime.utcnow()`.

They were located in:

```text
himp/database/inventory.py     2 occurrences
himp/database/scheduler.py     3 occurrences
himp/database/discovery.py     1 occurrence
```

Total:

```text
6 deprecated utcnow calls
```

The codebase already used a compatible pattern in other repository modules:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

Examples of existing areas already following this approach included user,
session, and automation-lock persistence.

This established the appropriate compatibility boundary for Phase 10.2.

---

# 4. Timestamp Compatibility Decision

Phase 10.2 intentionally did not introduce a database migration.

HIMP uses SQLite `TIMESTAMP` columns extensively, including:

```text
inventory_hosts.first_seen
inventory_hosts.last_seen
inventory_changes.changed_at
scheduler.last_run
scheduler.created_at
scheduler.updated_at
discovery.discovered_at
automation execution timestamps
workflow execution timestamps
user/session timestamps
```

Many schemas also rely on:

```sql
CURRENT_TIMESTAMP
```

which represents UTC without timezone metadata.

Therefore, converting only selected Python-generated values into
timezone-aware SQLite values would have created an inconsistent mixed
timestamp contract.

The Phase 10.2 compatibility decision was:

```text
Use timezone-aware Python UTC generation.
Preserve naive UTC at the SQLite persistence boundary.
```

Implementation pattern:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

This removes the deprecated Python call without altering stored timestamp
semantics.

---

# 5. Production Code Changes

## 5.1 Inventory Repository

File:

```text
himp/database/inventory.py
```

Import changed from:

```python
from datetime import datetime
```

to:

```python
from datetime import datetime, timezone
```

The two deprecated calls used for `last_seen` updates were replaced with:

```python
datetime.now(timezone.utc).replace(tzinfo=None)
```

Affected paths include:

- normal inventory host save/update
- restored host timestamp update

## 5.2 Scheduler Repository

File:

```text
himp/database/scheduler.py
```

Import changed to include `timezone`.

Three deprecated calls were replaced.

The existing scheduler timestamp representation and database schema were
preserved.

## 5.3 Discovery Repository

File:

```text
himp/database/discovery.py
```

Import changed to include `timezone`.

The single deprecated discovery timestamp call was replaced using the same
naive-UTC persistence pattern.

---

# 6. Regression Guard

A new deployment regression guard was added to:

```text
tests/deployment/test_himp_deployment.py
```

The test scans production Python sources under:

```text
himp/
```

and fails if any production source file contains:

```python
datetime.utcnow()
```

The intent is to prevent the deprecated call from being reintroduced in
future development.

This is a source-level compatibility guard rather than a test limited to the
three files changed in Phase 10.2.

---

# 7. Validation

## 7.1 Focused Regression

Focused Phase 10.2 tests covered inventory, scheduler, and deployment
contracts.

Result:

```text
28 passed
```

## 7.2 Full Regression

Final full suite:

```text
682 passed
```

No warnings summary was emitted.

This improved the prior baseline from:

```text
681 passed
11 warnings
```

to:

```text
682 passed
0 warnings
```

The additional test is the new deprecated-API regression guard.

## 7.3 Compile Validation

```text
compileall: PASS
```

## 7.4 Source Scan

Repository scan of production Python:

```text
utcnow references: NONE
```

## 7.5 Diff Validation

```text
git diff --check: PASS
```

---

# 8. Git Checkpoint

Phase 10.2 was committed as:

```text
f03adf6 — fix: replace deprecated utcnow usage
```

The commit changed:

```text
himp/database/discovery.py
himp/database/inventory.py
himp/database/scheduler.py
tests/deployment/test_himp_deployment.py
```

Synchronization was verified:

```text
LOCAL=f03adf6245cdfb9b938202feab487b16dc5390f3
REMOTE=f03adf6245cdfb9b938202feab487b16dc5390f3
```

---

# 9. Production Deployment

The release was deployed using:

```text
scripts/deploy/himp.sh
```

Deployment detected:

```text
Application changed: true
HIMP service changed: false
```

The HIMP application was restarted normally.

Release identity after deployment:

```text
SOURCE=f03adf6245cdfb9b938202feab487b16dc5390f3
DEPLOYED=f03adf6245cdfb9b938202feab487b16dc5390f3
```

Runtime state:

```text
HIMP=active
SCHEDULER=active
listener=0.0.0.0:9347
```

The repository remained clean and synchronized.

---

# 10. Production Smoke Validation

A direct production smoke check instantiated and read the three affected
repository areas.

Observed results:

```text
inventory_hosts=46
scheduler_records=5
discovery_records=1
```

The inventory count used:

```python
all_hosts(include_inactive=True)
```

so the value includes inactive historical inventory records.

The smoke test demonstrated that all three repository paths remained
operational after the timestamp changes.

Production journal validation since deployment:

```text
HIMP errors: none
```

Final repository state:

```text
feature/plugin-sdk...origin/feature/plugin-sdk
working tree clean
```

---

# 11. Phase 10.2 Definition of Done

```text
PHASE 10.2 — PYTHON DEPRECATION / WARNING CLEANUP

[x] Timestamp usage inventoried
[x] Compatibility reviewed
[x] Deprecated datetime.utcnow() calls removed
[x] Existing naive-UTC SQLite contract preserved
[x] Inventory timestamp paths validated
[x] Scheduler timestamp paths validated
[x] Discovery timestamp path validated
[x] Source regression guard added
[x] Focused tests pass — 28 passed
[x] Full regression passes — 682 passed
[x] Deprecation warnings eliminated — 0 warnings
[x] utcnow production source scan — NONE
[x] compileall passes
[x] git diff --check passes
[x] Implementation committed
[x] Implementation pushed
[x] LOCAL == REMOTE
[x] Production deployed
[x] SOURCE == DEPLOYED
[x] HIMP active
[x] Scheduler active
[x] Production repository smoke test passes
[x] No HIMP errors since deployment

PHASE 10.2: COMPLETE
```

---

# 12. Updated Phase 10 Roadmap

| Phase | Scope | Estimate | Status |
|---|---|---:|---|
| 10.1 | Automation Progress & Execution UX | 4–7h | **COMPLETE** |
| 10.2 | Python Deprecation / Warning Cleanup | 2–4h | **COMPLETE** |
| 10.3 | CMDB Security & Monitoring Completion | 3–6h | **NEXT** |
| 10.4 | Recent Activity / History UX | 3–5h | PLANNED |
| 10.5 | Production Refinement Gate | 2–3h | PLANNED |

Remaining planned effort:

```text
Phase 10.3     3–6 hours
Phase 10.4     3–5 hours
Phase 10.5     2–3 hours
--------------------------------
Remaining      8–14 hours
```

---

# 13. Phase 10 Tracking Checklist

```text
PHASE 10 — OPERATIONS & UX REFINEMENT

10.1 Automation Progress & Execution UX
[x] COMPLETE

10.2 Python Deprecation / Warning Cleanup
[x] Timestamp inventory
[x] Compatibility review
[x] Implementation
[x] Regression
[x] Warning verification
[x] Production validation
[x] Commit/push
STATUS: COMPLETE

10.3 CMDB Security & Monitoring Completion
[ ] Reconnaissance
[ ] Implementation/removal decision
[ ] Implementation
[ ] Report validation
[ ] Regression
[ ] Production validation
[ ] Commit/push
STATUS: NEXT

10.4 Recent Activity / History UX
[ ] Reconnaissance
[ ] Design
[ ] Implementation
[ ] Regression
[ ] Production UI validation
[ ] Commit/push
STATUS: PLANNED

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
STATUS: PLANNED

PHASE 10
[ ] COMPLETE
```

---

# 14. Next Phase — 10.3 CMDB Security & Monitoring Completion

## Status: NEXT

**Estimated effort:** 3–6 hours

Phase 10.3 addresses the two empty CMDB task files that currently generate
Ansible warnings during production reporting:

```text
roles/cmdb/tasks/security.yml
roles/cmdb/tasks/monitoring.yml
```

The objective is not merely to suppress the warnings.

Phase 10.3 must determine whether these files represent:

```text
intentional future placeholders
```

or:

```text
incomplete CMDB functionality that existing report consumers expect
```

The phase should begin with read-only reconnaissance of:

- `roles/cmdb`
- CMDB task includes
- report templates
- generated JSON schema
- generated Markdown reports
- dashboard host model
- health/plugin data already available
- inventory variables
- current security/monitoring data consumers

After reconnaissance, choose one intentional path:

```text
A. Implement meaningful read-only security/monitoring collection
```

or:

```text
B. Remove unused placeholders and their includes cleanly
```

Do not change host configuration as part of CMDB collection.

---

# 15. Exact Next Starting Point

Phase 10.3 should begin from the implementation checkpoint:

```text
f03adf6 — fix: replace deprecated utcnow usage
```

Current production application release:

```text
f03adf6245cdfb9b938202feab487b16dc5390f3
```

Before Phase 10.3 implementation:

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

After this completion document is committed, Git will advance to a
documentation-only checkpoint while the deployed release should remain at
`f03adf6`.

Do not redeploy HIMP solely for the documentation commit.

---

# 16. Final Checkpoint

Phase 10.2 achieved its intended maintenance goal without expanding into a
timestamp migration.

Before Phase 10.2:

```text
681 passed
11 deprecation warnings
6 production datetime.utcnow() calls
```

After Phase 10.2:

```text
682 passed
0 warnings
0 production datetime.utcnow() calls
```

Production repository reads remain healthy:

```text
inventory_hosts=46
scheduler_records=5
discovery_records=1
```

No HIMP service errors were recorded after deployment.

```text
Phase 9     COMPLETE
Phase 10    IN PROGRESS

Phase 10.1  COMPLETE
Phase 10.2  COMPLETE
Phase 10.3  NEXT
```
