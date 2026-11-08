"""Security regression tests for the real Ansible callback."""

import json
import subprocess
import textwrap


def run_callback_test(script):
    result = subprocess.run(
        ["/usr/bin/python3", "-c", textwrap.dedent(script)],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, (
        result.stdout + result.stderr
    )

    return result.stdout


def test_callback_redacts_credentials():
    output = run_callback_test("""
        import json
        from unittest.mock import patch
        from himp.ansible_plugins.callback.himp_events import CallbackModule

        callback = CallbackModule()
        emitted = []

        with patch.object(
            callback._display,
            "display",
            side_effect=lambda message: emitted.append(message),
        ):
            callback._emit(
                "failed",
                host="synthetic-host",
                error=(
                    "password=synthetic-password "
                    "token=synthetic-token "
                    "Bearer synthetic-bearer"
                ),
            )

        assert len(emitted) == 1
        assert emitted[0].startswith("HIMP_EVENT:")

        payload = json.loads(
            emitted[0].removeprefix("HIMP_EVENT:")
        )

        assert payload["event"] == "failed"
        assert payload["host"] == "synthetic-host"

        serialized = json.dumps(payload)

        assert "synthetic-password" not in serialized
        assert "synthetic-token" not in serialized
        assert "synthetic-bearer" not in serialized
        assert "[REDACTED]" in serialized

        print("PASS")
    """)

    assert "PASS" in output


def test_callback_fails_closed():
    output = run_callback_test("""
        from unittest.mock import patch
        from himp.ansible_plugins.callback.himp_events import CallbackModule

        callback = CallbackModule()
        emitted = []

        with patch.object(
            callback._display,
            "display",
            side_effect=lambda message: emitted.append(message),
        ):
            with patch(
                "himp.ansible_plugins.callback.himp_events.sanitize_event",
                side_effect=RuntimeError("Synthetic sanitizer failure"),
            ):
                try:
                    callback._emit(
                        "failed",
                        error="password=synthetic-secret",
                    )
                except RuntimeError:
                    pass
                else:
                    raise AssertionError(
                        "Sanitizer failure was suppressed"
                    )

        assert emitted == []
        print("PASS")
    """)

    assert "PASS" in output


def test_callback_emits_valid_json():
    output = run_callback_test("""
        import json
        from unittest.mock import patch
        from himp.ansible_plugins.callback.himp_events import CallbackModule

        callback = CallbackModule()
        emitted = []

        with patch.object(
            callback._display,
            "display",
            side_effect=lambda message: emitted.append(message),
        ):
            callback._emit(
                "task_ok",
                host="synthetic-host",
                task="Synthetic task",
                changed=False,
            )

        assert len(emitted) == 1

        payload = json.loads(
            emitted[0].removeprefix("HIMP_EVENT:")
        )

        assert payload["event"] == "task_ok"
        assert payload["host"] == "synthetic-host"
        assert payload["task"] == "Synthetic task"
        assert payload["changed"] is False
        assert "timestamp" in payload

        print("PASS")
    """)

    assert "PASS" in output
