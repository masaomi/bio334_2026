"""Courtesy-level Python sandbox for BIO334 student code execution.

Vendored verbatim from bio334-teaching/src/bio334_teaching/core/sandbox.py
(see ARCHITECTURE.md §3.1 for the vendoring decision). No changes; if the
upstream sandbox is improved, re-vendor.

Per ARCHITECTURE.md §6.4: this is a courtesy boundary, not a security
boundary. The server is instructor-controlled, all data is the
instructor's, and a determined student executing arbitrary Python on
the box can cause local mischief. The sandbox prevents accidents and
limits exfil of process-level secrets.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


TIMEOUT_SECONDS = 10
MAX_OUTPUT_BYTES = 64_000  # 64 KB per ARCHITECTURE.md §6.4
MAX_MEMORY_MB = 256

# Minimal PATH so python3 can be found in the subprocess
SAFE_PATH = "/usr/bin:/usr/local/bin:/opt/homebrew/bin"


@dataclass
class ExecutionResult:
    """Result of a sandboxed Python execution."""

    stdout: str
    stderr: str
    return_code: int
    execution_time_ms: int
    truncated: bool


def _truncate(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> tuple[str, bool]:
    """Truncate text to max_bytes. Returns (text, was_truncated)."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
    return truncated + f"\n... [output truncated at {max_bytes} bytes]", True


def _make_preexec_fn():
    """Set memory limits on Unix. Returns None on Windows."""
    if platform.system() == "Windows":
        return None

    def _set_limits() -> None:
        import resource  # Unix only

        mem_bytes = MAX_MEMORY_MB * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, resource.error):
            try:
                resource.setrlimit(resource.RLIMIT_DATA, (mem_bytes, mem_bytes))
            except (ValueError, resource.error):
                pass  # Best effort

    return _set_limits


class PythonSandbox:
    """Execute student Python code in a sandboxed subprocess."""

    def __init__(
        self,
        timeout: int = TIMEOUT_SECONDS,
        max_output_bytes: int = MAX_OUTPUT_BYTES,
    ) -> None:
        self._timeout = timeout
        self._max_output = max_output_bytes

    def execute(
        self,
        code: str,
        data_dir: Optional[Path] = None,
        workspace_dir: Optional[Path] = None,
        args: Optional[list[str]] = None,
    ) -> ExecutionResult:
        tmp_dir = tempfile.mkdtemp(prefix="bio334_sandbox_")
        try:
            return self._run(code, tmp_dir, data_dir, workspace_dir, args)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _run(
        self,
        code: str,
        tmp_dir: str,
        data_dir: Optional[Path],
        workspace_dir: Optional[Path] = None,
        args: Optional[list[str]] = None,
    ) -> ExecutionResult:
        tmp_path = Path(tmp_dir)

        if data_dir is not None:
            data_path = Path(data_dir)
            if data_path.is_dir():
                for item in data_path.iterdir():
                    link = tmp_path / item.name
                    try:
                        link.symlink_to(item.resolve())
                    except OSError:
                        if item.is_file():
                            shutil.copy2(str(item), str(link))
                        elif item.is_dir():
                            shutil.copytree(str(item), str(link))

        if workspace_dir is not None:
            ws_path = Path(workspace_dir)
            if ws_path.is_dir():
                for item in ws_path.iterdir():
                    if item.is_file():
                        link = tmp_path / item.name
                        if not link.exists():
                            try:
                                link.symlink_to(item.resolve())
                            except OSError:
                                shutil.copy2(str(item), str(link))

        script_file = tmp_path / "student_code.py"
        script_file.write_text(code, encoding="utf-8")

        env = {"PATH": SAFE_PATH, "LANG": "C.UTF-8", "HOME": str(tmp_path)}

        preexec = _make_preexec_fn()
        kwargs: dict = {
            "capture_output": True,
            "timeout": self._timeout,
            "cwd": str(tmp_path),
            "env": env,
        }
        if preexec is not None:
            kwargs["preexec_fn"] = preexec

        cmd = ["python3", str(script_file)]
        if args:
            cmd.extend(args)

        start = time.monotonic()
        try:
            result = subprocess.run(cmd, **kwargs)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            stdout_raw = result.stdout.decode("utf-8", errors="replace")
            stderr_raw = result.stderr.decode("utf-8", errors="replace")

            stdout, trunc_out = _truncate(stdout_raw, self._max_output)
            stderr, trunc_err = _truncate(stderr_raw, self._max_output)

            return ExecutionResult(
                stdout=stdout,
                stderr=stderr,
                return_code=result.returncode,
                execution_time_ms=elapsed_ms,
                truncated=trunc_out or trunc_err,
            )

        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {self._timeout} seconds.",
                return_code=-1,
                execution_time_ms=elapsed_ms,
                truncated=False,
            )
        except FileNotFoundError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ExecutionResult(
                stdout="",
                stderr="python3 not found. Please ensure Python 3 is installed.",
                return_code=-1,
                execution_time_ms=elapsed_ms,
                truncated=False,
            )
