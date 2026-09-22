from __future__ import annotations

"""Opt-in, evidence-bound runtime validation.

Ordinary SCAN never imports or calls this module. Runtime execution is available
only through the explicit downstream CLI command and requires the operator to
supply the exact SHA-256 of the plan being authorized.
"""

from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

RUNTIME_PLAN_SCHEMA = "scan-runtime-validation-plan/0.1"
RUNTIME_REPORT_SCHEMA = "scan-authorized-runtime-validation/0.1"
SUPPORTED_ASSERTIONS = {
    "EXIT_CODE_EQUALS",
    "STDOUT_CONTAINS",
    "STDERR_CONTAINS",
    "FILE_EXISTS",
    "FILE_SHA256_EQUALS",
    "JSON_POINTER_EQUALS",
    "DURATION_MS_MAX",
}


class RuntimePlanError(ValueError):
    pass


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _hash_file(path: Path) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_rel(value: str, *, allow_dot: bool = False) -> str:
    raw = str(value)
    if allow_dot and raw in {"", "."}:
        return "."
    p = PurePosixPath(raw.replace("\\", "/"))
    if not raw or p.is_absolute() or ".." in p.parts:
        raise RuntimePlanError(f"unsafe relative path: {value!r}")
    return p.as_posix()


def _tree_records(root: Path) -> list[dict[str, Any]]:
    root = Path(root).resolve(strict=True)
    records = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path.is_symlink():
            raise RuntimePlanError(f"runtime target contains symlink: {path.relative_to(root)}")
        rel = path.relative_to(root).as_posix()
        records.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": _hash_file(path),
        })
    return records


def _tree_digest(root: Path) -> tuple[int, str]:
    records = _tree_records(root)
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return len(records), _hash_bytes(canonical.encode("utf-8"))


def plan_sha256(plan_path: Path) -> str:
    return _hash_file(Path(plan_path).resolve(strict=True))


def load_runtime_plan(plan_path: Path) -> dict[str, Any]:
    path = Path(plan_path).resolve(strict=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimePlanError("runtime plan must be a JSON object")
    if payload.get("schema_version") != RUNTIME_PLAN_SCHEMA:
        raise RuntimePlanError(
            f"unsupported runtime plan schema: {payload.get('schema_version')!r}"
        )
    if not str(payload.get("plan_id") or "").strip():
        raise RuntimePlanError("runtime plan requires plan_id")

    command = payload.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise RuntimePlanError("command must be a non-empty string array")
    first = command[0].replace("\\", "/")
    if "/" in first:
        _safe_rel(first)

    cwd = _safe_rel(str(payload.get("cwd") or "."), allow_dot=True)
    network = str(payload.get("network") or "DENY").upper()
    if network != "DENY":
        raise RuntimePlanError("v0.36 runtime validation supports network=DENY only")

    timeout = float(payload.get("timeout_seconds", 10.0))
    if timeout <= 0 or timeout > 120:
        raise RuntimePlanError("timeout_seconds must be >0 and <=120")

    max_output = int(payload.get("max_output_bytes", 131072))
    if max_output <= 0 or max_output > 1048576:
        raise RuntimePlanError("max_output_bytes must be >0 and <=1048576")

    assertions = payload.get("assertions") or []
    if not isinstance(assertions, list):
        raise RuntimePlanError("assertions must be a list")
    seen = set()
    normalized = []
    for raw in assertions:
        if not isinstance(raw, dict):
            raise RuntimePlanError("each assertion must be an object")
        assertion_id = str(raw.get("id") or "").strip()
        kind = str(raw.get("kind") or "").upper()
        if not assertion_id or assertion_id in seen:
            raise RuntimePlanError("assertion ids must be non-empty and unique")
        if kind not in SUPPORTED_ASSERTIONS:
            raise RuntimePlanError(f"unsupported runtime assertion kind: {kind!r}")
        seen.add(assertion_id)
        item = dict(raw)
        item["id"] = assertion_id
        item["kind"] = kind
        if kind in {"FILE_EXISTS", "FILE_SHA256_EQUALS", "JSON_POINTER_EQUALS"}:
            item["path"] = _safe_rel(str(item.get("path") or ""))
        if kind == "DURATION_MS_MAX":
            max_ms = float(item.get("max"))
            if max_ms < 0:
                raise RuntimePlanError("DURATION_MS_MAX max must be non-negative")
        normalized.append(item)

    result = dict(payload)
    result["cwd"] = cwd
    result["network"] = network
    result["timeout_seconds"] = timeout
    result["max_output_bytes"] = max_output
    result["assertions"] = normalized
    result["source_refs"] = [str(x) for x in payload.get("source_refs") or []]
    return result


def _json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise RuntimePlanError("JSON pointer must be empty or begin with '/'")
    current = document
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as exc:
                raise KeyError(pointer) from exc
        elif isinstance(current, dict):
            if token not in current:
                raise KeyError(pointer)
            current = current[token]
        else:
            raise KeyError(pointer)
    return current


def _sanitize_env(workspace: Path, plan_id: str) -> dict[str, str]:
    tmp = workspace / ".scan-runtime-tmp"
    tmp.mkdir(exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(workspace),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONUNBUFFERED": "1",
        "SCAN_RUNTIME_WORKSPACE": str(workspace),
        "SCAN_RUNTIME_PLAN_ID": plan_id,
    }
    return env


def _network_prefix() -> tuple[list[str] | None, dict[str, Any]]:
    if sys.platform != "linux":
        return None, {
            "state": "BLOCKED",
            "reason": "NETWORK_ISOLATION_UNAVAILABLE",
            "detail": f"network-denied executor is currently implemented only for Linux; platform={sys.platform}",
        }
    unshare = shutil.which("unshare")
    if not unshare:
        return None, {
            "state": "BLOCKED",
            "reason": "NETWORK_ISOLATION_UNAVAILABLE",
            "detail": "unshare executable not found",
        }

    probe = [
        unshare, "--net", "--",
        sys.executable, "-c",
        "import json,socket; print(json.dumps(sorted(n for _,n in socket.if_nameindex())))",
    ]
    try:
        check = subprocess.run(
            probe,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
            check=False,
        )
    except Exception as exc:
        return None, {
            "state": "BLOCKED",
            "reason": "NETWORK_ISOLATION_UNAVAILABLE",
            "detail": f"network namespace preflight failed: {type(exc).__name__}: {exc}",
        }
    if check.returncode != 0:
        return None, {
            "state": "BLOCKED",
            "reason": "NETWORK_ISOLATION_UNAVAILABLE",
            "detail": check.stderr.decode("utf-8", "replace")[:1000],
        }
    try:
        interfaces = json.loads(check.stdout.decode("utf-8"))
    except Exception:
        interfaces = []
    if interfaces != ["lo"]:
        return None, {
            "state": "BLOCKED",
            "reason": "NETWORK_ISOLATION_UNVERIFIED",
            "detail": f"namespace interface view was {interfaces!r}, expected ['lo']",
        }
    return [unshare, "--net", "--"], {
        "state": "PASS",
        "mechanism": "LINUX_NETWORK_NAMESPACE",
        "interfaces": interfaces,
    }


def _copy_target(source: Path, target: Path) -> None:
    source = Path(source)
    if source.is_symlink():
        raise RuntimePlanError("runtime target root must not be a symlink")
    source = source.resolve(strict=True)
    for path in source.rglob("*"):
        if path.is_symlink():
            raise RuntimePlanError(f"runtime target contains symlink: {path.relative_to(source)}")

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", ".scan", "__pycache__"}}

    shutil.copytree(source, target, ignore=ignore)


def _read_capped(path: Path, max_bytes: int) -> tuple[str, int, bool, str]:
    total = path.stat().st_size if path.exists() else 0
    with path.open("rb") as fh:
        data = fh.read(max_bytes)
    return (
        data.decode("utf-8", "replace"),
        total,
        total > max_bytes,
        _hash_file(path),
    )


def _evaluate_assertion(
    assertion: dict[str, Any],
    *,
    workspace: Path,
    returncode: int | None,
    duration_ms: float,
    stdout: str,
    stderr: str,
    timed_out: bool,
) -> dict[str, Any]:
    kind = assertion["kind"]
    result: dict[str, Any] = {
        "id": assertion["id"],
        "kind": kind,
        "source_refs": [str(x) for x in assertion.get("source_refs") or []],
    }
    try:
        if kind == "EXIT_CODE_EQUALS":
            expected = int(assertion.get("equals"))
            actual = returncode
            passed = (not timed_out) and actual == expected
            result.update({"expected": expected, "actual": actual})
        elif kind == "STDOUT_CONTAINS":
            expected = str(assertion.get("value") or "")
            passed = expected in stdout
            result.update({"expected_substring": expected, "observed": passed})
        elif kind == "STDERR_CONTAINS":
            expected = str(assertion.get("value") or "")
            passed = expected in stderr
            result.update({"expected_substring": expected, "observed": passed})
        elif kind == "FILE_EXISTS":
            rel = assertion["path"]
            actual = workspace.joinpath(*PurePosixPath(rel).parts).is_file()
            passed = actual
            result.update({"path": rel, "actual": actual})
        elif kind == "FILE_SHA256_EQUALS":
            rel = assertion["path"]
            path = workspace.joinpath(*PurePosixPath(rel).parts)
            actual = _hash_file(path) if path.is_file() else None
            expected = str(assertion.get("equals") or "")
            passed = actual == expected
            result.update({"path": rel, "expected": expected, "actual": actual})
        elif kind == "JSON_POINTER_EQUALS":
            rel = assertion["path"]
            path = workspace.joinpath(*PurePosixPath(rel).parts)
            pointer = str(assertion.get("pointer") or "")
            document = json.loads(path.read_text(encoding="utf-8"))
            actual = _json_pointer(document, pointer)
            expected = assertion.get("equals")
            passed = actual == expected
            result.update({"path": rel, "pointer": pointer, "expected": expected, "actual": actual})
        elif kind == "DURATION_MS_MAX":
            expected = float(assertion.get("max"))
            actual = duration_ms
            passed = actual <= expected
            result.update({"expected_max_ms": expected, "actual_ms": actual})
        else:
            raise RuntimePlanError(f"unsupported assertion kind: {kind}")
    except Exception as exc:
        passed = False
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["state"] = "PASS" if passed else "FAIL"
    return result


def render_runtime_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Authorized Runtime Validation",
        "",
        f"**State:** `{report.get('state')}`",
        f"**Plan:** `{report.get('plan_id')}`",
        f"**Plan SHA-256:** `{report.get('plan_sha256')}`",
        "",
        "Runtime validation is a separate opt-in observation layer. It does not mutate or promote static SCAN evidence.",
        "",
        "| Assertion | Kind | State |",
        "|---|---|---|",
    ]
    for row in report.get("assertions") or []:
        lines.append(f"| `{row.get('id')}` | `{row.get('kind')}` | `{row.get('state')}` |")
    lines += [
        "",
        f"Network isolation: `{(report.get('isolation') or {}).get('network', {}).get('mechanism') or (report.get('isolation') or {}).get('network', {}).get('state')}`",
        f"Source tree unchanged: `{(report.get('source_integrity') or {}).get('unchanged')}`",
        "",
    ]
    return "\n".join(lines)


def run_authorized_runtime_validation(
    target_root: Path,
    plan_path: Path,
    output_dir: Path,
    *,
    authorized_plan_sha256: str,
) -> dict[str, Any]:
    target_root = Path(target_root).resolve(strict=True)
    plan_path = Path(plan_path).resolve(strict=True)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_plan_sha = plan_sha256(plan_path)
    auth = str(authorized_plan_sha256 or "").removeprefix("sha256:")
    if auth != raw_plan_sha:
        report = {
            "schema_version": RUNTIME_REPORT_SCHEMA,
            "state": "BLOCKED",
            "reason": "PLAN_NOT_AUTHORIZED",
            "plan_sha256": raw_plan_sha,
            "authorization": {
                "required": "exact plan SHA-256",
                "provided": auth or None,
                "matched": False,
            },
            "authority": {
                "runtime_observation_only": True,
                "static_store_mutated": False,
                "automatic_promotion": False,
            },
        }
        (output_dir / "runtime_validation.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "runtime_validation.md").write_text(render_runtime_markdown(report), encoding="utf-8")
        return report

    try:
        plan = load_runtime_plan(plan_path)
    except Exception as exc:
        report = {
            "schema_version": RUNTIME_REPORT_SCHEMA,
            "state": "BLOCKED",
            "reason": "INVALID_PLAN",
            "plan_sha256": raw_plan_sha,
            "error": f"{type(exc).__name__}: {exc}",
            "authority": {
                "runtime_observation_only": True,
                "static_store_mutated": False,
                "automatic_promotion": False,
            },
        }
        (output_dir / "runtime_validation.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "runtime_validation.md").write_text(render_runtime_markdown(report), encoding="utf-8")
        return report

    network_prefix, network = _network_prefix()
    if network_prefix is None:
        report = {
            "schema_version": RUNTIME_REPORT_SCHEMA,
            "state": "BLOCKED",
            "reason": network.get("reason"),
            "plan_id": plan["plan_id"],
            "plan_sha256": raw_plan_sha,
            "authorization": {"required": "exact plan SHA-256", "provided": auth, "matched": True},
            "isolation": {"network": network, "shell": False, "working_copy": "NOT_EXECUTED"},
            "authority": {
                "runtime_observation_only": True,
                "static_store_mutated": False,
                "automatic_promotion": False,
            },
        }
        (output_dir / "runtime_validation.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / "runtime_validation.md").write_text(render_runtime_markdown(report), encoding="utf-8")
        return report

    source_count, source_before = _tree_digest(target_root)
    with tempfile.TemporaryDirectory(prefix="scan-runtime-") as temp:
        workspace = Path(temp) / "workspace"
        _copy_target(target_root, workspace)
        workspace_count_before, workspace_before = _tree_digest(workspace)

        cwd_rel = plan["cwd"]
        cwd = workspace if cwd_rel == "." else workspace.joinpath(*PurePosixPath(cwd_rel).parts)
        if not cwd.is_dir():
            raise RuntimePlanError(f"plan cwd does not exist in working copy: {cwd_rel}")

        command = list(plan["command"])
        first = command[0].replace("\\", "/")
        if "/" in first:
            command[0] = str(workspace.joinpath(*PurePosixPath(first).parts))

        env = _sanitize_env(workspace, str(plan["plan_id"]))
        stdout_path = Path(temp) / "stdout.bin"
        stderr_path = Path(temp) / "stderr.bin"
        start = time.monotonic()
        timed_out = False
        returncode: int | None = None
        with stdout_path.open("wb") as out_fh, stderr_path.open("wb") as err_fh:
            proc = subprocess.Popen(
                [*network_prefix, *command],
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out_fh,
                stderr=err_fh,
                shell=False,
                start_new_session=True,
            )
            try:
                returncode = proc.wait(timeout=float(plan["timeout_seconds"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
                returncode = proc.returncode
        duration_ms = (time.monotonic() - start) * 1000.0

        stdout, stdout_total, stdout_truncated, stdout_sha = _read_capped(
            stdout_path, int(plan["max_output_bytes"])
        )
        stderr, stderr_total, stderr_truncated, stderr_sha = _read_capped(
            stderr_path, int(plan["max_output_bytes"])
        )
        workspace_count_after, workspace_after = _tree_digest(workspace)

        assertions = [
            _evaluate_assertion(
                assertion,
                workspace=workspace,
                returncode=returncode,
                duration_ms=duration_ms,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
            )
            for assertion in plan["assertions"]
        ]
        assertion_failures = sum(1 for row in assertions if row["state"] != "PASS")

        source_count_after, source_after = _tree_digest(target_root)
        source_unchanged = source_before == source_after and source_count == source_count_after

        state = "PASS" if not timed_out and not assertion_failures and source_unchanged else "FAIL"
        report = {
            "schema_version": RUNTIME_REPORT_SCHEMA,
            "state": state,
            "plan_id": plan["plan_id"],
            "plan_sha256": raw_plan_sha,
            "source_refs": plan.get("source_refs") or [],
            "authorization": {
                "required": "exact plan SHA-256",
                "provided": auth,
                "matched": True,
            },
            "isolation": {
                "working_copy": "TEMPORARY_COPY",
                "source_execution": False,
                "shell": False,
                "environment": "SANITIZED",
                "forwarded_environment_keys": ["PATH"],
                "network": network,
                "timeout_seconds": plan["timeout_seconds"],
                "max_output_bytes": plan["max_output_bytes"],
            },
            "source_integrity": {
                "file_count_before": source_count,
                "file_count_after": source_count_after,
                "tree_sha256_before": source_before,
                "tree_sha256_after": source_after,
                "unchanged": source_unchanged,
            },
            "workspace": {
                "file_count_before": workspace_count_before,
                "file_count_after": workspace_count_after,
                "tree_sha256_before": workspace_before,
                "tree_sha256_after": workspace_after,
                "changed": workspace_before != workspace_after,
                "retained": False,
            },
            "process": {
                "command": command,
                "cwd": cwd_rel,
                "returncode": returncode,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_bytes": stdout_total,
                "stderr_bytes": stderr_total,
                "stdout_sha256": stdout_sha,
                "stderr_sha256": stderr_sha,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            },
            "assertion_count": len(assertions),
            "assertion_failures": assertion_failures,
            "assertions": assertions,
            "authority": {
                "runtime_observation_only": True,
                "static_store_mutated": False,
                "automatic_promotion": False,
                "ordinary_scan_execution_changed": False,
                "runtime_result_may_override_static_uncertainty": False,
            },
            "limits": [
                "A runtime PASS establishes only the assertions in this authorized plan.",
                "The Linux network namespace prevents ordinary external network access but is not a hostile-code security sandbox.",
                "No runtime observation is automatically promoted into scan_index.sqlite.",
                "Visual/pixel equivalence is not established unless an explicit authorized observer emits and asserts such evidence.",
            ],
        }

    (output_dir / "runtime_validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "runtime_validation.md").write_text(render_runtime_markdown(report), encoding="utf-8")
    return report
