#!/usr/bin/env bash
###############################################################################
# HIMP Documentation Scaffold
###############################################################################

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo
echo "========================================="
echo " HIMP Documentation Scaffold"
echo "========================================="
echo

created=0
existing=0

create_dir() {
    if [[ -d "$1" ]]; then
        echo "[=] Directory exists : $1"
        ((++existing))
    else
        mkdir -p "$1"
        echo "[+] Created directory: $1"
        ((++created))
    fi
}

create_file() {
    if [[ -f "$1" ]]; then
        echo "[=] File exists      : $1"
        ((++existing))
    else
        touch "$1"
        echo "[+] Created file     : $1"
        ((++created))
    fi
}

echo "Creating documentation structure..."
echo

create_dir docs
create_dir docs/architecture
create_dir docs/developer
create_dir docs/decisions
create_dir docs/user

create_file docs/README.md

create_file docs/architecture/01-system-overview.md
create_file docs/architecture/02-discovery-engine.md
create_file docs/architecture/03-cmdb-engine.md
create_file docs/architecture/04-report-engine.md
create_file docs/architecture/05-dashboard.md

create_file docs/developer/getting-started.md
create_file docs/developer/coding-standards.md
create_file docs/developer/plugin-development.md
create_file docs/developer/testing.md
create_file docs/developer/git-workflow.md

create_file docs/decisions/ADR-0001-plugin-architecture.md
create_file docs/decisions/ADR-0002-cmdb-schema.md
create_file docs/decisions/ADR-0003-discovery-strategy.md
create_file docs/decisions/ADR-0004-report-pipeline.md

create_file docs/user/installation.md
create_file docs/user/configuration.md
create_file docs/user/reporting.md

echo
echo "-----------------------------------------"
echo "Created : $created"
echo "Existing: $existing"
echo "-----------------------------------------"
echo
echo "Documentation scaffold complete."
echo
