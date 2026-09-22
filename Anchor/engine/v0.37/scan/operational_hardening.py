from __future__ import annotations

"""Operational hardening primitives for scanner-owned output directories.

The lease is deliberately small and mechanical. It prevents two SCAN writers from
mutating the same output tree concurrently, recovers a dead same-host writer, and
fails closed when ownership cannot be established safely.
"""

import errno
import json
import os
from pathlib import Path
import platform
import time
from typing import Any

OUTPUT_LEASE_SCHEMA = "scan-output-lease/0.1"
OUTPUT_LEASE_NAME = ".scan-write.lock"


class OutputBusyError(RuntimeError):
    """Raised when another writer may still own the output directory."""


class UnsafeOutputPathError(ValueError):
    """Raised when the requested output root itself is a symlink or non-directory."""


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False

    # On Windows, os.kill(pid, 0) is not a harmless POSIX-style liveness
    # probe: signal 0 maps to CTRL_C_EVENT and can interrupt the runner.
    # Query the process handle instead and keep ambiguous failures blocking.
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            open_process = kernel32.OpenProcess
            open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            open_process.restype = wintypes.HANDLE
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = (wintypes.HANDLE,)
            close_handle.restype = wintypes.BOOL

            process_query_limited_information = 0x1000
            handle = open_process(process_query_limited_information, False, pid)
            if handle:
                close_handle(handle)
                return True

            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: no such PID
                return False
            if error == 5:   # ERROR_ACCESS_DENIED: process exists but is protected
                return True
            return True
        except Exception:
            # Liveness uncertainty must not be turned into permission to
            # discard another writer's lease.
            return True

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        return True
    return True


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


class OutputLease:
    """Exclusive, crash-recoverable lease for one scanner-owned output tree.

    Same-host leases owned by a live PID are refused. A same-host lease whose PID
    no longer exists is stale and may be removed. Unknown/corrupt or foreign-host
    leases are not guessed about: they remain BLOCKING until an operator resolves
    them.
    """

    def __init__(self, output: Path, *, engine_version: str):
        self.requested_output = Path(output)
        self.engine_version = str(engine_version)
        self.output: Path | None = None
        self.lock_path: Path | None = None
        self._token: dict[str, Any] | None = None

    def _prepare_output(self) -> Path:
        raw = self.requested_output
        if raw.exists() and raw.is_symlink():
            raise UnsafeOutputPathError(f"scan output root must not be a symlink: {raw}")
        raw.mkdir(parents=True, exist_ok=True)
        if raw.is_symlink():
            raise UnsafeOutputPathError(f"scan output root must not be a symlink: {raw}")
        resolved = raw.resolve(strict=True)
        if not resolved.is_dir():
            raise UnsafeOutputPathError(f"scan output root is not a directory: {raw}")
        return resolved

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": OUTPUT_LEASE_SCHEMA,
            "engine_version": self.engine_version,
            "pid": os.getpid(),
            "host": platform.node() or "UNKNOWN_HOST",
            "started_ns": time.time_ns(),
        }

    def _existing_is_stale(self, lock_path: Path) -> bool:
        existing = _read_json(lock_path)
        if not existing:
            return False
        if existing.get("schema_version") != OUTPUT_LEASE_SCHEMA:
            return False
        host = str(existing.get("host") or "")
        current_host = platform.node() or "UNKNOWN_HOST"
        if host != current_host:
            return False
        try:
            pid = int(existing.get("pid"))
        except (TypeError, ValueError):
            return False
        return not _pid_alive(pid)

    def acquire(self) -> "OutputLease":
        if self._token is not None:
            raise OutputBusyError("output lease is already held by this object")
        output = self._prepare_output()
        lock_path = output / OUTPUT_LEASE_NAME

        for attempt in range(2):
            token = self._payload()
            try:
                fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if attempt == 0 and self._existing_is_stale(lock_path):
                    try:
                        lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                existing = _read_json(lock_path)
                detail = existing or {"state": "UNREADABLE_OR_FOREIGN"}
                raise OutputBusyError(
                    f"scan output is already leased: {output}; owner={json.dumps(detail, sort_keys=True)}"
                )
            try:
                data = (json.dumps(token, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
                os.write(fd, data)
                try:
                    os.fsync(fd)
                except OSError:
                    pass
            finally:
                os.close(fd)
            self.output = output
            self.lock_path = lock_path
            self._token = token
            return self

        raise OutputBusyError(f"unable to acquire scan output lease: {output}")

    def release(self) -> None:
        if self._token is None or self.lock_path is None:
            return
        current = _read_json(self.lock_path)
        if current is not None:
            owned = (
                current.get("schema_version") == self._token.get("schema_version")
                and current.get("pid") == self._token.get("pid")
                and current.get("host") == self._token.get("host")
                and current.get("started_ns") == self._token.get("started_ns")
            )
            if not owned:
                raise OutputBusyError(
                    f"refusing to remove an output lease whose ownership changed: {self.lock_path}"
                )
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        self._token = None

    def __enter__(self) -> "OutputLease":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.release()
        return False


def inspect_output_lease(output: Path) -> dict[str, Any]:
    """Read-only operational state for diagnostics and qualification."""
    root = Path(output)
    lock_path = root / OUTPUT_LEASE_NAME
    if not lock_path.exists():
        return {"state": "FREE", "path": str(lock_path)}
    payload = _read_json(lock_path)
    if not payload:
        return {"state": "BLOCKED_UNKNOWN", "path": str(lock_path)}
    same_host = payload.get("host") == (platform.node() or "UNKNOWN_HOST")
    try:
        pid = int(payload.get("pid"))
    except (TypeError, ValueError):
        pid = -1
    if same_host and not _pid_alive(pid):
        state = "STALE_SAME_HOST"
    elif same_host:
        state = "ACTIVE_SAME_HOST"
    else:
        state = "ACTIVE_OR_UNKNOWN_FOREIGN_HOST"
    return {"state": state, "path": str(lock_path), "lease": payload}
