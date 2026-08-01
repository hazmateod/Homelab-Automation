# ADR-0001 – Plugin-Based Discovery Architecture

**Status:** Accepted

**Date:** 2026-07-31

---

# Context

The Homelab Infrastructure Management Platform (HIMP) is intended to discover,
inventory, document, monitor, and automate every server in the homelab.

Originally, application discovery was implemented in a single Ansible task file.
As additional applications were added, this approach became difficult to
maintain, test, and extend.

A modular architecture was required.

---

# Decision

Application discovery will use a plugin architecture.

The discovery pipeline is organized as:

```
Generate Reports
        │
        ▼
Report Role
        │
        ▼
Discovery Role
        │
        ▼
applications.yml
        │
        ▼
Application Plugin
```

Each application owns its own discovery plugin.

Example:

```
roles/discovery/tasks/applications/

technitium.yml
unbound.yml
docker.yml
pbs.yml
```

Each application plugin acts as an orchestrator.

Example:

```
technitium.yml

├── service.yml
├── version.yml
├── process.yml
├── ports.yml
├── configuration.yml
└── statistics.yml
```

Each module is responsible for discovering one aspect of the application.

---

# Design Goals

The plugin architecture should provide:

- Small focused task files
- Independent testing
- Easier debugging
- Consistent CMDB structure
- Simple future expansion
- Minimal merge conflicts
- Clean Git history

---

# Development Workflow

Every discovery enhancement follows the same workflow.

1. Create a new discovery module.
2. Wire the module into the orchestrator.
3. Run syntax validation.
4. Test against a single host.
5. Verify generated reports.
6. Commit changes.

The full inventory is never executed until the single-host validation succeeds.

---

# Discovery Philosophy

The preferred discovery order is:

1. Operating System
2. Application API
3. Configuration Files
4. Runtime Information
5. Binary Inspection

The operating system should always be considered the source of truth whenever
possible.

---

# Benefits

This architecture allows every application to follow the same pattern while
remaining independent.

Future applications such as:

- Technitium
- Unbound
- Pi-hole
- Docker
- Proxmox
- PBS
- Uptime Kuma
- WireGuard

can all implement discovery without changing the overall framework.

---

# Consequences

Advantages

- Highly modular
- Easier maintenance
- Predictable layout
- Better testing
- Easier onboarding

Tradeoffs

- More files
- Slightly more orchestration
- Requires documentation

The tradeoffs are considered acceptable because maintainability is a primary
goal of the project.
