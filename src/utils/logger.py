"""Logger setup shared across the app."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str, log_file: str | None = None, level: int = logging.INFO
) -> logging.Logger:
    """Return a logger configured once per name with console + optional file output."""
    logger = logging.getLogger(name)
    # `hasHandlers()` also answers True when only an *ancestor* has handlers, so
    # it cannot distinguish "already set up" from "the parent is set up". Check
    # this logger's own handlers instead.
    if logger.handlers:
        return logger

    # Dotted names are a hierarchy: a record on "bridge.search" is handled here
    # and then propagates to "bridge" and to root. With a handler on each, one
    # log call printed the same line twice - which reads exactly like the code
    # ran twice, and cost an afternoon of chasing a search that had only ever
    # been dispatched once.
    logger.propagate = False

    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
