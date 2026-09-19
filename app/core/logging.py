"""Central logging configuration."""

from __future__ import annotations

import logging
import logging.config
import sys

from app.core.config import Settings, get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(settings: Settings | None = None) -> None:
    """Configure root logging once at application startup."""
    settings = settings or get_settings()
    level = logging.DEBUG if settings.debug else logging.INFO

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": _LOG_FORMAT},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "uvicorn": {"level": level, "propagate": True},
            "sqlalchemy.engine": {
                "level": logging.INFO if settings.db_echo else logging.WARNING,
                "propagate": True,
            },
        },
    }
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """Thin wrapper to keep a single import surface for logging."""
    return logging.getLogger(name)
