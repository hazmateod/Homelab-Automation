import os
import stat
import subprocess
from pathlib import Path


INSTALLER = Path(
    "scripts/database/install-config.sh"
)


def _clean_environment():
    env = os.environ.copy()

    for name in (
        "HIMP_DATABASE_CONFIG_TARGET",
        "HIMP_DATABASE_BACKEND",
        "HIMP_DATABASE_HOST",
        "HIMP_DATABASE_PORT",
        "HIMP_DATABASE_NAME",
        "HIMP_DATABASE_USER",
        "HIMP_DATABASE_PASSWORD",
        "HIMP_DATABASE_PASSWORD_FILE",
    ):
        env.pop(
            name,
            None,
        )

    return env


def _run_installer(
    tmp_path,
    *,
    password="database-secret",
    extra_env=None,
    check=True,
):
    password_file = (
        tmp_path / "postgresql-password"
    )

    password_file.write_text(
        f"{password}\n"
    )

    password_file.chmod(0o600)

    target = (
        tmp_path
        / "etc"
        / "himp"
        / "database.env"
    )

    env = _clean_environment()

    env.update(
        {
            "HIMP_DATABASE_CONFIG_TARGET": str(target),
            "HIMP_DATABASE_PASSWORD_FILE": str(password_file),
        }
    )

    if extra_env:
        env.update(
            extra_env
        )

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )

    return (
        result,
        target,
        password_file,
    )


def _run_remove(
    target,
    *,
    check=True,
):
    env = _clean_environment()

    env[
        "HIMP_DATABASE_CONFIG_TARGET"
    ] = str(target)

    return subprocess.run(
        [
            "bash",
            str(INSTALLER),
            "--remove",
        ],
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def _mode(path):
    return stat.S_IMODE(
        path.stat().st_mode
    )


def test_installer_creates_postgresql_configuration(
    tmp_path,
):
    result, target, _ = _run_installer(
        tmp_path
    )

    assert target.exists()

    assert target.read_text() == (
        'HIMP_DATABASE_BACKEND="postgresql"\n'
        'HIMP_DATABASE_HOST="himpdb01.server.arpa"\n'
        'HIMP_DATABASE_PORT="5432"\n'
        'HIMP_DATABASE_NAME="himp"\n'
        'HIMP_DATABASE_USER="himp_app"\n'
        'HIMP_DATABASE_PASSWORD="database-secret"\n'
    )

    assert _mode(target) == 0o600

    assert (
        "credentials=REDACTED"
        in result.stdout
    )

    assert (
        "database-secret"
        not in result.stdout
    )

    assert (
        "database-secret"
        not in result.stderr
    )


def test_installer_quotes_special_password_characters(
    tmp_path,
):
    password = (
        'Space # dollar$ quote" '
        r'backslash\ semicolon; value'
    )

    result, target, _ = _run_installer(
        tmp_path,
        password=password,
    )

    assert result.returncode == 0

    contents = target.read_text()

    assert (
        'HIMP_DATABASE_PASSWORD="'
        in contents
    )

    assert r'quote\"' in contents
    assert r'backslash\\' in contents

    assert password not in result.stdout
    assert password not in result.stderr


def test_installer_accepts_database_overrides(
    tmp_path,
):
    _, target, _ = _run_installer(
        tmp_path,
        password="override-secret",
        extra_env={
            "HIMP_DATABASE_HOST": "db.example.invalid",
            "HIMP_DATABASE_PORT": "6543",
            "HIMP_DATABASE_NAME": "himp_test",
            "HIMP_DATABASE_USER": "himp_test_user",
        },
    )

    contents = target.read_text()

    assert (
        'HIMP_DATABASE_HOST="db.example.invalid"\n'
        in contents
    )

    assert (
        'HIMP_DATABASE_PORT="6543"\n'
        in contents
    )

    assert (
        'HIMP_DATABASE_NAME="himp_test"\n'
        in contents
    )

    assert (
        'HIMP_DATABASE_USER="himp_test_user"\n'
        in contents
    )

    assert (
        'HIMP_DATABASE_PASSWORD="override-secret"\n'
        in contents
    )


def test_installer_rejects_direct_password_environment(
    tmp_path,
):
    result, target, _ = _run_installer(
        tmp_path,
        extra_env={
            "HIMP_DATABASE_PASSWORD": "forbidden-secret",
        },
        check=False,
    )

    assert result.returncode != 0
    assert not target.exists()

    assert (
        "use HIMP_DATABASE_PASSWORD_FILE"
        in result.stderr
    )

    assert (
        "forbidden-secret"
        not in result.stdout
    )

    assert (
        "forbidden-secret"
        not in result.stderr
    )


def test_installer_requires_password_file(
    tmp_path,
):
    target = (
        tmp_path
        / "etc"
        / "himp"
        / "database.env"
    )

    env = _clean_environment()

    env[
        "HIMP_DATABASE_CONFIG_TARGET"
    ] = str(target)

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not target.exists()

    assert (
        "HIMP_DATABASE_PASSWORD_FILE is required"
        in result.stderr
    )


def test_installer_rejects_missing_password_file(
    tmp_path,
):
    target = (
        tmp_path
        / "etc"
        / "himp"
        / "database.env"
    )

    missing = (
        tmp_path / "missing-secret"
    )

    env = _clean_environment()

    env.update(
        {
            "HIMP_DATABASE_CONFIG_TARGET": str(target),
            "HIMP_DATABASE_PASSWORD_FILE": str(missing),
        }
    )

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not target.exists()


def test_installer_rejects_symbolic_link_password_file(
    tmp_path,
):
    real_secret = (
        tmp_path / "real-secret"
    )

    real_secret.write_text(
        "secret\n"
    )

    link = (
        tmp_path / "secret-link"
    )

    link.symlink_to(
        real_secret
    )

    target = (
        tmp_path
        / "etc"
        / "himp"
        / "database.env"
    )

    env = _clean_environment()

    env.update(
        {
            "HIMP_DATABASE_CONFIG_TARGET": str(target),
            "HIMP_DATABASE_PASSWORD_FILE": str(link),
        }
    )

    result = subprocess.run(
        [
            "bash",
            str(INSTALLER),
        ],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not target.exists()

    assert (
        "must not be a symbolic link"
        in result.stderr
    )


def test_installer_rejects_invalid_port(
    tmp_path,
):
    result, target, _ = _run_installer(
        tmp_path,
        extra_env={
            "HIMP_DATABASE_PORT": "invalid",
        },
        check=False,
    )

    assert result.returncode != 0
    assert not target.exists()

    assert (
        "HIMP_DATABASE_PORT must be numeric"
        in result.stderr
    )


def test_installer_replaces_existing_configuration_atomically(
    tmp_path,
):
    _, target, _ = _run_installer(
        tmp_path,
        password="first-secret",
    )

    inode_before = (
        target.stat().st_ino
    )

    result, target, _ = _run_installer(
        tmp_path,
        password="second-secret",
    )

    assert result.returncode == 0

    contents = target.read_text()

    assert "second-secret" in contents
    assert "first-secret" not in contents
    assert _mode(target) == 0o600

    inode_after = (
        target.stat().st_ino
    )

    assert inode_after != inode_before

    temporary_files = list(
        target.parent.glob(
            ".database.env.tmp.*"
        )
    )

    assert temporary_files == []


def test_remove_deletes_external_configuration(
    tmp_path,
):
    _, target, _ = _run_installer(
        tmp_path
    )

    assert target.exists()

    result = _run_remove(
        target
    )

    assert result.returncode == 0
    assert not target.exists()

    assert (
        "effective_default_backend=sqlite"
        in result.stdout
    )

    assert (
        "No HIMP services were restarted."
        in result.stdout
    )


def test_remove_is_idempotent(
    tmp_path,
):
    target = (
        tmp_path
        / "etc"
        / "himp"
        / "database.env"
    )

    first = _run_remove(
        target
    )

    second = _run_remove(
        target
    )

    assert first.returncode == 0
    assert second.returncode == 0

    assert (
        "already absent"
        in second.stdout
    )


def test_installer_does_not_manage_services(
    tmp_path,
):
    result, _, _ = _run_installer(
        tmp_path
    )

    assert (
        "systemctl"
        not in INSTALLER.read_text()
    )

    assert (
        "No HIMP services were restarted."
        in result.stdout
    )


def test_installer_does_not_write_production_path_during_test(
    tmp_path,
):
    _, target, _ = _run_installer(
        tmp_path
    )

    assert str(target).startswith(
        str(tmp_path)
    )

    assert (
        target
        != Path("/etc/himp/database.env")
    )


def test_example_configuration_contains_no_real_secret():
    example = Path(
        "config/database.env.example"
    ).read_text()

    assert (
        "HIMP_DATABASE_BACKEND=postgresql"
        in example
    )

    assert (
        "HIMP_DATABASE_PASSWORD="
        "REPLACE_WITH_EXTERNAL_SECRET"
        in example
    )
