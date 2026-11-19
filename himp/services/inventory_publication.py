"""Serialize inventory edits and reconcile a durable, validated publication."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
from tempfile import NamedTemporaryFile

from himp.database.host_identity import HostIdentityRepository
from himp.services.inventory_writer import InventoryFileWriter


def _sync_directory(directory):
    fd = os.open(directory, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(path, content, mode):
    with NamedTemporaryFile(dir=path.parent, prefix=".himp-publish-", delete=False) as output:
        temporary = Path(output.name)
        try:
            os.fchmod(output.fileno(), mode)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
            os.replace(temporary, path)
            _sync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)


def _digest(content):
    return hashlib.sha256(content).hexdigest()


class InventoryPublication:
    def __init__(self, filename, repository):
        self.filename = Path(filename).resolve()
        self.repository = repository
        self.journal = self.filename.with_name(f".{self.filename.name}.pending")
        self.lock = self.filename.with_name(f".{self.filename.name}.lock")

    @contextmanager
    def locked(self):
        with self.lock.open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            self.recover()
            yield

    def recover(self):
        if not self.journal.exists():
            return
        pending = json.loads(self.journal.read_text())
        candidate = pending["candidate"].encode("utf-8")
        current = _digest(self.filename.read_bytes())
        if current == pending["original"] and current != _digest(candidate):
            mode = stat.S_IMODE(self.filename.stat().st_mode)
            _write_atomic(self.filename, candidate, mode)
        elif current != _digest(candidate):
            raise RuntimeError("Inventory changed outside HIMP during a pending publication")
        actions = {
            "save_host": self.repository.save_host,
            "mark_removed": self.repository.mark_removed,
            "restore_host": self.repository.restore_host,
            "rename_group": self.repository.rename_group,
            "rename_host": lambda *args: HostIdentityRepository(self.repository).rename(*args),
        }
        operation = pending["operation"]
        if operation not in {"save_host", "rename_host"}:
            self.reconcile_identities()
        actions[operation](*pending["arguments"])
        if operation == "save_host":
            self.reconcile_identities()
        self.journal.unlink()
        _sync_directory(self.journal.parent)

    def reconcile_identities(self):
        return HostIdentityRepository(self.repository).backfill()

    @contextmanager
    def stage(self):
        original = self.filename.read_bytes()
        with NamedTemporaryFile(
            dir=self.filename.parent, prefix=".himp-stage-", suffix=".yml", delete=False
        ) as output:
            candidate = Path(output.name)
            output.write(original)
        try:
            yield InventoryFileWriter(candidate), _digest(original)
        finally:
            candidate.unlink(missing_ok=True)

    def publish(self, writer, original, operation, *arguments):
        if _digest(self.filename.read_bytes()) != original:
            raise RuntimeError("Inventory changed while the edit was being validated")
        pending = json.dumps({
            "candidate": writer.filename.read_text(encoding="utf-8"),
            "original": original,
            "operation": operation,
            "arguments": arguments,
        }).encode("utf-8")
        _write_atomic(self.journal, pending, 0o600)
        self.recover()
