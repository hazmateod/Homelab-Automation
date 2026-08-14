# HIMP Project Checkpoint

**Last Updated:** 2026-08-14
**Current Release:** 5.20.6
**Current Branch:** `feature/plugin-sdk`
**Implementation Baseline:** `d2d76e4`
**Repository:** Clean and synchronized with `origin/feature/plugin-sdk`

---

## Purpose

This document is the authoritative current-state checkpoint for HIMP.
It exists so development can resume from a known, verified state.

## Current State

HIMP 5.20.6 production hardening is complete.

Validated areas:
- Configuration validation
- Full automated regression testing
- Deployment regression testing
- Production deployment synchronization
- Production deployment idempotence
- Python compilation
- Git diff validation
- Production service validation

### Repository

```text
Branch:          feature/plugin-sdk
Commit:          d2d76e4
Remote:          origin/feature/plugin-sdk
Working tree:    CLEAN
Local/remote:    SYNCHRONIZED
```

### Test State

```text
Full regression suite:       324 passed
Deployment regression:        6 passed
Configuration tests:          7 passed
compileall:                  PASS
git diff --check:             PASS
Shell syntax validation:      PASS
```

The increase from the previous 318-test baseline to 324 tests consists of the six deployment regression tests added during 5.20.6 closure.

## Production Runtime

Production HIMP is deployed at:

```text
/opt/himp
```

The service runs as:

```text
User:             himp
Group:            himp
WorkingDirectory: /opt/himp
```

The application listens on:

```text
0.0.0.0:9347
```

The final verified HIMP process ID was `646378`.

The final production idempotence test confirmed that the PID remained unchanged across an unchanged deployment.

## Configuration Validation

Existing configuration validation was reviewed rather than replaced.

`himp/config.py` provides `Config.validate()` and validates the required runtime paths:

- inventory
- dashboard
- maintenance playbook
- report playbook
- dashboard playbook

Final configuration validation results:

```text
Repository context:       PASS
Production context:       PASS
Configuration tests:      7 passed
compileall:               PASS
```

No additional configuration-validation subsystem was added because the existing implementation already satisfies the current requirement.

### Configuration Design Note

`config/config.yml` currently contains Proxmox, Technitium, and UniFi configuration values, while the runtime `Config` dataclass currently manages application paths.

These are not currently unified into one configuration model.

This was intentionally left outside 5.20.6 scope to avoid unnecessary configuration architecture changes.

## Deployment Hardening

The deployment mechanism is `scripts/deploy/himp.sh`.
The systemd installer is `scripts/systemd/install.sh`.

The deployment mechanism compares Git-managed application content with `/opt/himp` before deciding whether HIMP needs to restart.
The systemd installer compares Git-managed systemd units with the installed units before reinstalling them.

### Deployment Regression Coverage

Permanent automated deployment regression coverage was added in `tests/deployment/test_himp_deployment.py`.

The six tests verify:

1. Unchanged deployment does not restart HIMP.
2. Application changes restart HIMP.
3. `himp.service` changes restart HIMP.
4. Runtime data outside the deployment-managed application tree is preserved.
5. Reports outside the deployment-managed application tree are preserved.
6. Git-managed systemd units are installed into the configured systemd target.

The deployment scripts support test-specific target directories while retaining these production defaults:

```text
DEPLOY_ROOT=/opt/himp
SYSTEMD_TARGET_ROOT=/etc/systemd/system
```

No additional test framework or dependency was introduced.

## Production Deployment Validation

The first real production deployment detected pre-existing application drift:

```text
Application changed: true
HIMP service changed: false
```

The deployment synchronized `/opt/himp` with the Git source and restarted HIMP as designed.

A subsequent source/deployment comparison confirmed the deployment-managed application directories and files were synchronized.

The final production idempotence test was then performed against the synchronized production installation.

Verified results:

```text
SOURCE_DEPLOYMENT_SYNC=PASS

Application changed: false
HIMP service changed: false

No HIMP changes detected; restart not required.

HIMP_PID_BEFORE=646378
HIMP_PID_AFTER=646378

PID_UNCHANGED=PASS
APPLICATION_UNCHANGED=PASS
SERVICE_UNCHANGED=PASS
NO_RESTART_DECISION=PASS

production_config_validation=PASS
```

This is the authoritative production proof that an unchanged deployment does not unnecessarily restart HIMP.

## Runtime Data

The production database was verified at `/opt/himp/data/himp.db`.

The database observed during validation was approximately 3,768,320 bytes.

The deployment regression suite protects runtime data outside the Git-managed deployment directories.

Reports were also verified as present under `/opt/himp/reports`.

The deployment process does not treat the entire `/opt/himp` tree as disposable application content.

## Systemd State

The primary HIMP application service is `himp.service`.

It runs as `himp:himp` from `/opt/himp`.

The service includes the production hardening controls established during 5.20, including:

- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=true`
- Explicit `ReadWritePaths`
- Dedicated `himp` service account

The scheduler timer is `himp-scheduler.timer`.

Git-managed systemd units are validated and installed by `scripts/systemd/install.sh`.

## Known Architectural Follow-Up

During deployment review, the following runtime distinction was confirmed.

### Web Application

```text
/opt/himp
User=himp
Group=himp
```

### Privileged Scheduled Automation

The following services currently execute from the Git working tree and run as root:

- `himp-inventory-sync.service`
- `himp-scheduled-updates.service`
- `himp-scheduler.service`

Their current working directory is `/root/Homelab-Automation`.

This was intentionally NOT changed during 5.20.6.

It should be reviewed as a future architecture/security task to determine whether these privileged automation services should eventually execute from `/opt/himp` or whether the current separation is intentional and required.

This is not a 5.20.6 production-hardening blocker.

## 5.20.6 Completion Criteria

The following 5.20.6 closure requirements are complete:

- Configuration validation — COMPLETE
- Production configuration validation — COMPLETE
- Deployment synchronization — COMPLETE
- Deployment idempotence — COMPLETE
- Automated deployment regression — COMPLETE
- Runtime data preservation validation — COMPLETE
- Systemd deployment validation — COMPLETE
- Full regression suite — COMPLETE
- Python compile validation — COMPLETE
- Git diff validation — COMPLETE
- Production service validation — COMPLETE
- Clean Git working tree — COMPLETE
- Remote synchronization — COMPLETE

### Release Commit

```text
d2d76e4 test: add deployment idempotence regression coverage
```

Pushed successfully to `origin/feature/plugin-sdk`.

## Next Development Phase

**5.20.6 production hardening is closed.**

The next development work should begin only after reviewing the current roadmap and selecting the next explicitly approved HIMP phase.

Do not reopen completed 5.20.6 work unless a new defect, regression, or security finding is discovered.

The known scheduler runtime-path issue should remain a tracked architectural follow-up rather than being silently folded into the next feature.

## Next-Session Starting Point

When resuming HIMP:

```bash
cd /root/Homelab-Automation
git status
git fetch origin
git rev-parse HEAD
git rev-parse origin/feature/plugin-sdk
```

Confirm:

```text
Branch: feature/plugin-sdk
HEAD: d2d76e4
Origin: d2d76e4
Working tree: clean
```

Then verify the production service:

```bash
systemctl is-active himp
systemctl show himp -p MainPID -p User -p Group -p WorkingDirectory
```

Before beginning new feature work:

```bash
/opt/himp/.venv/bin/python -m pytest -q
```

Expected baseline: 324 passed.
