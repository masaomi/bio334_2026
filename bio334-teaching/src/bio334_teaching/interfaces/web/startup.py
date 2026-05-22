"""Web server startup for BIO334 Teaching Chain.

Handles port detection, browser opening, and uvicorn launch.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from typing import Optional


def _port_available(host: str, port: int) -> bool:
    """Check whether a TCP port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


def _find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from *start_port*.

    Tries up to *max_attempts* consecutive ports. Raises RuntimeError
    if none are available.
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if _port_available(host, port):
            return port
    raise RuntimeError(
        f"Could not find an available port in range "
        f"{start_port}-{start_port + max_attempts - 1}"
    )


def _open_browser_delayed(url: str, delay: float = 1.5) -> None:
    """Open the browser after a short delay (runs in a daemon thread)."""

    def _open():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass  # Non-critical; user can navigate manually

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def start_server(
    host: str = "127.0.0.1",
    port: int = 8334,
    open_browser: bool = True,
    api_key: Optional[str] = None,
    proxy: Optional[str] = None,
    progress_dir: Optional[str] = None,
    backend: str = "auto",
) -> None:
    """Start the BIO334 Teaching Chain web server.

    Parameters
    ----------
    host:
        Bind address (default ``127.0.0.1``).
    port:
        Preferred port (default ``8334``). Falls back to the next
        available port if occupied.
    open_browser:
        Whether to auto-open the browser on startup.
    api_key:
        Anthropic API key for the chat backend.
    proxy:
        Optional API proxy URL.
    progress_dir:
        Directory for storing student progress files.
    backend:
        Chat backend: ``"api"``, ``"claude-code"``, or ``"auto"``.
    """
    try:
        import uvicorn  # noqa: F811
    except ImportError:
        print(
            "Error: uvicorn is required. Install it with:\n"
            "  pip install uvicorn[standard]",
            file=sys.stderr,
        )
        sys.exit(1)

    # Find an available port
    try:
        actual_port = _find_available_port(host, port)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if actual_port != port:
        print(f"Port {port} is in use, using port {actual_port} instead.")

    url = f"http://{host}:{actual_port}"
    print(f"BIO334 Teaching Chain running at {url}")
    print("Press Ctrl+C to stop.\n")

    if open_browser:
        _open_browser_delayed(url)

    # Enable bio334 debug logging
    import logging
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
    logging.getLogger("bio334").setLevel(logging.DEBUG)

    # Create the app with the provided configuration
    from bio334_teaching.interfaces.web.app import create_app

    app = create_app(
        api_key=api_key,
        proxy_url=proxy,
        progress_dir=progress_dir,
        backend=backend,
    )

    # Run uvicorn
    try:
        uvicorn.run(
            app,
            host=host,
            port=actual_port,
            log_level="info",
            access_log=False,
        )
    except KeyboardInterrupt:
        print("\nShutting down.")
