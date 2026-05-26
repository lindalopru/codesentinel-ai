"""Native desktop wrapper around the Gradio web UI.

This module gives CodeSentinel a real macOS/Linux/Windows window — no browser
tab, no address bar. Underneath, it's still the same Gradio app served on
127.0.0.1:7860; we just wrap it in a WKWebView (macOS) or QtWebEngine (Linux)
window using `pywebview`, so it behaves like a native application.

Usage:
    python -m web.desktop          # from the project venv
    make desktop                   # via Makefile
    open Launch_CodeSentinel.command   # double-click from Finder
"""

from __future__ import annotations

import os
import socket
import threading
import time

import httpx
import webview

from web.app import build_ui

HOST = "127.0.0.1"
PORT = int(os.environ.get("CODESENTINEL_WEB_PORT", "7860"))
URL = f"http://{HOST}:{PORT}"

WINDOW_TITLE = "CodeSentinel AI"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860
WINDOW_MIN = (960, 640)
SERVER_READY_TIMEOUT_S = 45.0


def _port_already_open(host: str, port: int) -> bool:
    """True if something is already listening on (host, port)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect((host, port))
            return True
        except (ConnectionRefusedError, OSError):
            return False


def _wait_for_url(url: str, timeout: float = SERVER_READY_TIMEOUT_S) -> bool:
    """Poll until the Gradio server responds 200/302/401."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.head(url, timeout=2.0)
            if r.status_code in (200, 302, 401):
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.4)
    return False


def _start_server_in_background() -> None:
    """Launch Gradio without blocking the main thread."""
    # Quiet Gradio's own analytics + HF tracking before importing components.
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    # Make sure ~/Downloads exists and Gradio is allowed to serve from it.
    from pathlib import Path as _P
    downloads = _P.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    demo = build_ui()
    demo.queue(default_concurrency_limit=1).launch(
        server_name=HOST,
        server_port=PORT,
        inbrowser=False,
        share=False,
        prevent_thread_lock=True,
        quiet=True,
        show_api=False,
        allowed_paths=[str(downloads)],
    )


def main() -> None:
    if not _port_already_open(HOST, PORT):
        thread = threading.Thread(target=_start_server_in_background, daemon=True)
        thread.start()
        if not _wait_for_url(URL):
            raise RuntimeError(
                f"Gradio did not come up at {URL} within {SERVER_READY_TIMEOUT_S:.0f} s. "
                "Run `make doctor` to diagnose."
            )
    else:
        # Server already running (e.g. `make web` is also open) — reuse it.
        pass

    webview.create_window(
        title=WINDOW_TITLE,
        url=URL,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=WINDOW_MIN,
        text_select=True,
        confirm_close=False,
    )
    # gui=None lets pywebview pick the best backend per OS
    # (cocoa on macOS, qt on Linux, edgechromium on Windows).
    webview.start()


if __name__ == "__main__":
    main()
