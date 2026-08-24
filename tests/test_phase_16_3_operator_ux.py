from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ssh_setup_uses_actual_himp_service_identity():
    javascript = (
        ROOT / "static/js/dashboard.js"
    ).read_text()

    assert "sudo -u himp" in javascript
    assert "/var/lib/himp/.ssh/id_ed25519.pub" in javascript
    assert "/var/lib/himp/.ssh/id_ed25519" in javascript
    assert "StrictHostKeyChecking=accept-new" in javascript
    assert "PasswordAuthentication=no" in javascript
    assert "IdentitiesOnly=yes" in javascript


def test_ssh_setup_supports_legacy_and_dedicated_paths():
    template = (
        ROOT / "templates/inventory.html"
    ).read_text()

    assert "Existing / Legacy Account" in template
    assert "Dedicated HIMP Automation Account" in template
    assert "sshSetupModeExisting" in template
    assert "sshSetupModeDedicated" in template
    assert "Run on the HIMP server" in template
    assert "Run on the TARGET HOST as root" in template


def test_dedicated_himp_identity_contract_is_explicit():
    javascript = (
        ROOT / "static/js/dashboard.js"
    ).read_text()

    assert "himp-automation" in javascript
    assert "passwd -l himp-automation" in javascript
    assert "NOPASSWD: ALL" in javascript
    assert "sudo -n id" in javascript
    assert "ansible.builtin.command" in javascript
    assert "Recommended settings applied" in javascript


def test_existing_account_path_uses_form_identity_and_become():
    javascript = (
        ROOT / "static/js/dashboard.js"
    ).read_text()

    assert "addHostUser" in javascript
    assert "editHostUser" in javascript
    assert "addHostBecome" in javascript
    assert "editHostBecome" in javascript
    assert "sshExistingBecomeStep" in javascript


def test_add_host_explains_legacy_and_new_host_onboarding():
    template = (
        ROOT / "templates/inventory.html"
    ).read_text()

    assert (
        "Existing hosts may use their current"
        in template
    )

    assert (
        "For new Linux hosts"
        in template
    )

    assert "himp-automation" in template
    assert "SSH Setup" in template


def test_vulnerability_scanner_is_safe_external_launcher():
    sidebar = (
        ROOT / "templates/layout/sidebar.html"
    ).read_text()

    assert (
        'href="https://vulnscanner.server.arpa"'
        in sidebar
    )

    assert 'target="_blank"' in sidebar
    assert 'rel="noopener noreferrer"' in sidebar
    assert "Vulnerability Scanner" in sidebar
