# HIMP Release, Upgrade, and Rollback Runbook

## Purpose

This runbook defines the controlled production release process for the Homelab Infrastructure Management Platform (HIMP).

It establishes the required path for:

- normal production upgrades
- release validation
- deployment verification
- production smoke testing
- failed deployment decisions
- rollback to known-good application state
- release checkpoint recording

The production deployment script is:

```text
scripts/deploy/himp.sh
```

The deployed Git revision is recorded in:

```text
/opt/himp/.himp-release
```

A production release is valid only when the repository, remote branch, deployment marker, and production runtime can be reconciled.

---

# 1. Release Principles

HIMP production releases follow these rules:

1. Production deployment must originate from a Git working tree.
2. The deployment working tree must be clean.
3. Implementation validation occurs before the release commit.
4. The release commit must be pushed before production deployment.
5. Local and remote branch revisions must match before deployment.
6. Deployment must use `scripts/deploy/himp.sh`.
7. Successful deployment must record the source Git SHA in `/opt/himp/.himp-release`.
8. Production runtime must be validated after deployment.
9. A failed production release must not be repaired by making uncommitted changes directly in the deployment tree.
10. Rollback must return production to a known-good application state while preserving Git history and release traceability.

---

# 2. Production Release Identity

The following three revisions should normally agree:

```bash
git rev-parse HEAD
git rev-parse origin/feature/plugin-sdk
cat /opt/himp/.himp-release
```

Interpretation:

```text
LOCAL = REMOTE = DEPLOYED
```

If these values differ, determine why before beginning another production release.

The deployment marker identifies the Git revision processed by the deployment script. It does not by itself prove application health; runtime validation is still required.

---

# 3. Normal Upgrade Procedure

## 3.1 Pre-Release Repository Gate

Confirm the expected branch and repository state:

```bash
cd /root/Homelab-Automation
git status --short --branch
git fetch origin
git log -5 --oneline
```

Before release:

```text
working tree = clean
branch = feature/plugin-sdk
LOCAL = origin/feature/plugin-sdk
```

Do not deploy from an uncommitted working tree.

## 3.2 Implementation Validation

Complete the relevant end-of-slice validation before committing.

The standard release gate includes:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q himp tests
git diff --check
```

Any additional focused tests required by the changed subsystem must also pass.

Warnings must be reviewed. Known existing warnings may be accepted when they are unrelated to the release, but new unexpected warnings require investigation.

## 3.3 Commit

Review the final diff before committing:

```bash
git diff
git diff --check
git status --short
```

Stage only the intended release files and create a descriptive commit.

```bash
git add <intended-files>
git diff --cached --check
git diff --cached --stat
git commit -m "<release description>"
```

## 3.4 Push and Synchronization

Push the completed release:

```bash
git push origin feature/plugin-sdk
git fetch origin
```

Verify:

```bash
echo "LOCAL=$(git rev-parse HEAD)"
echo "REMOTE=$(git rev-parse origin/feature/plugin-sdk)"
```

Required condition:

```text
LOCAL == REMOTE
```

Do not deploy if synchronization cannot be demonstrated.

## 3.5 Production Deployment

Deploy only from the clean synchronized repository:

```bash
bash scripts/deploy/himp.sh
```

## 3.6 Release Identity Verification

Immediately verify:

```bash
echo "SOURCE=$(git rev-parse HEAD)"
echo "REMOTE=$(git rev-parse origin/feature/plugin-sdk)"
echo "DEPLOYED=$(cat /opt/himp/.himp-release)"
```

Required condition:

```text
SOURCE == REMOTE == DEPLOYED
```

## 3.7 Runtime Verification

```bash
systemctl is-active himp.service
systemctl show himp.service \
  -p User \
  -p Group \
  -p WorkingDirectory \
  -p MainPID \
  --no-pager
ss -lntp | grep ':9347'
```

Expected production identity:

```text
service: active
User: himp
Group: himp
WorkingDirectory: /opt/himp
listener: 0.0.0.0:9347
```

## 3.8 Production Smoke Test

After deployment, validate the application at the functional level. At minimum confirm:

- login succeeds
- authenticated dashboard loads
- application health endpoint/UI is healthy
- inventory is accessible
- reports are accessible
- automation page is accessible
- scheduler remains operational
- no new unexpected application errors appear in the service journal

Use the release-specific feature as an additional smoke test when the release changes user-visible or operational behavior.

---

# 4. Failed Deployment Decision Process

A release is considered unsuccessful when any required deployment or production validation gate fails.

Examples include deployment script failure, service startup failure, missing listener, authentication failure, critical API/UI regression, scheduler or automation regression, database incompatibility, revision mismatch, or severe new application errors.

When a failure occurs:

```text
STOP
  |
  +--> preserve failure evidence
  |
  +--> determine whether production is still healthy
  |
  +--> determine whether forward repair is low risk
  |
  +--> forward fix OR rollback
```

Do not repeatedly redeploy speculative changes into production.

Capture relevant evidence before changing state:

```bash
git rev-parse HEAD
cat /opt/himp/.himp-release
systemctl status himp.service --no-pager -l
journalctl -u himp.service -n 200 --no-pager
git status --short --branch
```

---

# 5. Rollback Decision

Rollback is preferred when production is unavailable, authentication or authorization is broken, a critical workflow is broken, data integrity is at risk, the cause is not immediately understood, or a forward fix cannot be safely validated quickly.

A forward repair may be appropriate when production remains healthy, the defect is non-critical, the cause is clearly understood, and the correction can pass the normal validation gate before deployment.

---

# 6. Application Rollback Procedure

## 6.1 Identify the Known-Good Revision

Record the failed release revision:

```bash
git rev-parse HEAD
cat /opt/himp/.himp-release
```

Identify the previous known-good commit:

```bash
git log --oneline --decorate -10
```

Do not guess the rollback target. The target must be a revision known to have passed production validation.

## 6.2 Preserve Git History

The normal HIMP rollback strategy is a Git revert, not a destructive branch reset.

For a single bad release commit:

```bash
git revert <bad-release-sha>
```

For multiple commits, determine the exact release range before reverting. Do not blindly revert an arbitrary range. Resolve conflicts deliberately if Git reports them.

## 6.3 Validate the Rollback Commit

Before deployment:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q himp tests
git diff --check
git status --short --branch
```

The rollback commit must pass the same engineering validation expected of a forward release.

## 6.4 Push the Rollback

```bash
git push origin feature/plugin-sdk
git fetch origin
echo "LOCAL=$(git rev-parse HEAD)"
echo "REMOTE=$(git rev-parse origin/feature/plugin-sdk)"
```

Required:

```text
LOCAL == REMOTE
```

## 6.5 Deploy the Rollback Commit

```bash
bash scripts/deploy/himp.sh
```

Then verify:

```bash
echo "SOURCE=$(git rev-parse HEAD)"
echo "DEPLOYED=$(cat /opt/himp/.himp-release)"
systemctl is-active himp.service
ss -lntp | grep ':9347'
```

The `.himp-release` marker will contain the new rollback commit SHA. This is intentional: the rollback commit represents the Git state that restores the known-good application content while preserving repository history.

## 6.6 Repeat Production Smoke Tests

Repeat the normal production smoke-test gate. Rollback is complete only when the restored application state has been validated in production.

---

# 7. Database and Runtime Data Safety

Git rollback and disaster recovery are different operations.

The normal application deployment process preserves runtime data, including HIMP's production data directories and reports.

Do not delete, replace, or restore the production SQLite database merely because application code is being rolled back.

Before rolling back a release that changes database schema, migration behavior, stored data format, authentication/session persistence, scheduler persistence, or automation execution persistence, stop and determine whether the older application revision is compatible with the current production database.

If database compatibility cannot be established, application rollback alone is not sufficient. Use the Phase 9.8 disaster recovery procedure when actual production data restoration is required.

---

# 8. Systemd and Configuration Rollback

`scripts/deploy/himp.sh` manages Git-controlled HIMP application and systemd content.

A rollback commit that restores previous Git-managed service configuration will cause the deployment process to install the restored unit content.

After any systemd-related rollback verify:

```bash
systemctl daemon-reload
systemctl is-active himp.service
systemctl is-active himp-scheduler.timer
systemctl list-timers --all | grep himp
```

Do not manually maintain a second production copy of Git-managed HIMP service definitions.

---

# 9. Emergency Restrictions

Do not use these as the normal HIMP release or rollback process:

```text
editing /opt/himp application files directly
deploying from a dirty Git tree
force-pushing the production branch
git reset --hard followed by force push
copying arbitrary old source trees into /opt/himp
replacing the SQLite database during an application-only rollback
disabling authentication or authorization to recover access
```

Emergency actions outside the documented process must be recorded and reconciled back into Git before the next normal release.

---

# 10. Release Checkpoint

A completed production release should record:

```text
phase/subphase
release purpose
release commit SHA
remote synchronization result
full regression result
focused test result when applicable
compileall result
git diff check result
deployment result
deployed .himp-release SHA
service state
production smoke-test result
known warnings
rollback decision/result if applicable
final repository state
```

The release is complete when:

```text
[ ] implementation validated
[ ] release committed
[ ] release pushed
[ ] LOCAL == REMOTE
[ ] clean deployment source verified
[ ] deployment successful
[ ] SOURCE == REMOTE == DEPLOYED
[ ] himp.service active
[ ] expected production listener active
[ ] authenticated production smoke test passed
[ ] release-specific smoke test passed
[ ] no unacceptable new runtime errors
[ ] documentation checkpoint recorded
[ ] working tree clean
```

---

# 11. Relationship to Disaster Recovery

Release rollback restores application code/configuration to a known-good Git-managed state.

Disaster recovery restores production infrastructure and persistent data from backup.

Use release rollback for a bad application release. Use the Phase 9.8 disaster recovery procedure for lost/corrupted infrastructure or persistent production data.

These procedures complement each other and must not be treated as interchangeable recovery mechanisms.

---

# 12. Phase 9.9 Release Flow

```text
Git change
    |
    v
end-of-slice validation
    |
    v
commit
    |
    v
push
    |
    v
LOCAL == REMOTE
    |
    v
clean deployment source
    |
    v
scripts/deploy/himp.sh
    |
    v
SOURCE == REMOTE == DEPLOYED
    |
    v
service/runtime validation
    |
    v
authenticated production smoke test
    |
    +--------------------+
    |                    |
   PASS                 FAIL
    |                    |
    v                    v
checkpoint        preserve evidence
                         |
                         v
                 forward fix or rollback
                         |
                         v
                 full validation gate
                         |
                         v
                      deploy
                         |
                         v
                 production validation
```
