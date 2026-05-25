"""Project logger with Rich-aware handler."""

from __future__ import annotations

import logging
import os

from rich.logging import RichHandler

_INITIALIZED = False


def get_logger(name: str = "codesentinel") -> logging.Logger:
    global _INITIALIZED
    if not _INITIALIZED:
        level_name = os.environ.get("CODESENTINEL_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_time=False, show_path=False)],
        )
        _INITIALIZED = True
    return logging.getLogger(name)
