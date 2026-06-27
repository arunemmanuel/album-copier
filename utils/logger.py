"""Application logging configuration."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: Path = Path("logs/application.log")) -> logging.Logger:
    """Configure and return the application logger."""

    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("file_copy_utility")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
