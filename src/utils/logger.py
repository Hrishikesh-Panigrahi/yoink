from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str, log_file: str | None = None, level: int = logging.INFO
) -> logging.Logger:
    """Set up the logger on the first call for `name`.

    Later calls return it as is and ignore `log_file` and `level`.
    """
    logger = logging.getLogger(name)
    # hasHandlers() is also True when only a parent logger has handlers, so check
    # this logger's own list.
    if logger.handlers:
        return logger

    # Every logger gets its own handler, so letting "bridge.search" propagate to
    # "bridge" would print each line twice.
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
