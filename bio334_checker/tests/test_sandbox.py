"""Smoke tests for the vendored Python sandbox."""

from __future__ import annotations

from bio334_checker.core.sandbox import PythonSandbox


def test_sandbox_hello_world() -> None:
    sb = PythonSandbox()
    res = sb.execute("print('hello')")
    assert res.return_code == 0
    assert res.stdout.strip() == "hello"
    assert res.stderr == ""
    assert not res.truncated


def test_sandbox_nonzero_exit() -> None:
    sb = PythonSandbox()
    res = sb.execute("import sys; sys.exit(2)")
    assert res.return_code == 2


def test_sandbox_timeout() -> None:
    sb = PythonSandbox(timeout=1)
    res = sb.execute("import time; time.sleep(5)")
    assert res.return_code == -1
    assert "timed out" in res.stderr


def test_sandbox_argv_passthrough() -> None:
    sb = PythonSandbox()
    res = sb.execute(
        "import sys; print(' '.join(sys.argv[1:]))",
        args=["alpha", "beta", "gamma"],
    )
    assert res.return_code == 0
    assert res.stdout.strip() == "alpha beta gamma"


def test_sandbox_env_scrubbed() -> None:
    """API keys must not leak into the subprocess (ARCHITECTURE.md §6.4)."""
    sb = PythonSandbox()
    res = sb.execute(
        "import os; print('LEAK' if os.environ.get('ANTHROPIC_API_KEY') else 'OK')"
    )
    assert res.return_code == 0
    assert res.stdout.strip() == "OK"
