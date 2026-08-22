from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_notifications_page_uses_canonical_layout():
    source = (
        ROOT / "templates/notifications.html"
    ).read_text()

    assert '{% extends "base.html" %}' in source
    assert "Notification History" in source
    assert "Visible Notifications" in source
    assert "Delivery Failures" in source
    assert "Acknowledge" in source


def test_notifications_page_exposes_filters():
    source = (
        ROOT / "templates/notifications.html"
    ).read_text()

    assert 'name="lifecycle_status"' in source
    assert 'name="severity"' in source
    assert 'action="/notifications"' in source


def test_sidebar_exposes_notifications():
    source = (
        ROOT / "templates/layout/sidebar.html"
    ).read_text()

    assert 'href="/notifications"' in source
    assert "Notifications" in source


def test_notification_page_requires_authenticated_session():
    source = (
        ROOT / "himp/api/server.py"
    ).read_text()

    start = source.index(
        'def notifications('
    )
    section = source[
        start:start + 2500
    ]

    assert (
        "Depends(require_page_session)"
        in section
    )


def test_acknowledgement_requires_admin():
    source = (
        ROOT / "himp/api/server.py"
    ).read_text()

    start = source.index(
        "def acknowledge_notification("
    )

    section = source[
        start:start + 900
    ]

    assert "Depends(require_admin)" in section
    assert "admin.username" in section


def test_notification_ui_does_not_reference_webhook_secret():
    source = (
        ROOT / "templates/notifications.html"
    ).read_text()

    assert "HIMP_DISCORD_WEBHOOK_URL" not in source
    assert "notifications.env" not in source
    assert "webhook_url" not in source


def test_notification_page_displays_delivery_audit():
    source = (
        ROOT / "templates/notifications.html"
    ).read_text()

    assert "latest_delivery" in source
    assert "destination_type" in source
    assert "status_code" in source
