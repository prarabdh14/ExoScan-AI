"""Logging helpers for ExoScan-AI."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logging(level: str = "INFO", log_format: str | None = None) -> logging.Logger:
    """Configure root logger and return the ExoScan-AI logger."""
    fmt = log_format or "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logger = logging.getLogger("exoscan")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
