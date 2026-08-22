from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (
    ROOT
    / "scripts/notifications/install-config.sh"
)


def source():
    return INSTALLER.read_text()


def test_installer_requires_webhook_file_not_environment_secret():
    text = source()

    assert "HIMP_DISCORD_WEBHOOK_FILE" in text
    assert (
        "HIMP_DISCORD_WEBHOOK_URL must not be supplied directly"
        in text
    )


def test_installer_redacts_webhook_output():
    text = source()

    assert "discord_webhook=REDACTED" in text


def test_systemd_units_load_notifications_environment():
    for filename in (
        ROOT / "systemd/himp.service",
        ROOT / "systemd/himp-scheduler.service",
    ):
        assert (
            "EnvironmentFile=-/etc/himp/notifications.env"
            in filename.read_text()
        )
