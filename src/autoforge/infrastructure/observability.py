"""Process-local JSON logging for AutoForge entry points."""

from __future__ import annotations

import json
import logging
import os
import re
import socket
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Final

from autoforge.core.config import LoggingConfig

_LOGGER_NAME: Final = "autoforge"
_MANAGED_HANDLER: Final = "_autoforge_managed_handler"
_SAFE_EXTRA_FIELDS: Final = (
    "autoforge_event_id",
    "autoforge_event_type",
    "autoforge_event_version",
    "autoforge_correlation_id",
    "autoforge_causation_id",
    "autoforge_job_id",
    "autoforge_producer",
)
_URL_CREDENTIALS = re.compile(r"://([^:/\s]+):([^@/\s]+)@")
_SECRET_VALUE = re.compile(
    r"(?i)\b(password|token|secret|api[_-]?key)\s*([=:])\s*([^,\s]+)"
)


class JsonFormatter(logging.Formatter):
    """Keep a small allowlist of structured fields and redact message secrets."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self._redact(record.getMessage()),
        }
        for field_name in _SAFE_EXTRA_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        if record.exc_info:
            payload["exception"] = self._redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _redact(value: str) -> str:
        value = _URL_CREDENTIALS.sub(r"://\1:[REDACTED]@", value)
        return _SECRET_VALUE.sub(r"\1\2[REDACTED]", value)


def configure_logging(config: LoggingConfig) -> logging.Logger:
    """Configure AutoForge's named logger without changing global logging state."""

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(config.level.upper())
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, _MANAGED_HANDLER, False):
            logger.removeHandler(handler)
            handler.close()

    directory = config.directory
    directory.mkdir(parents=True, exist_ok=True)
    filename = directory / f"autoforge-{socket.gethostname()}-{os.getpid()}.log"
    formatter = JsonFormatter()
    for handler in (
        logging.StreamHandler(),
        RotatingFileHandler(
            filename,
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        ),
    ):
        handler.setFormatter(formatter)
        setattr(handler, _MANAGED_HANDLER, True)
        logger.addHandler(handler)
    return logger
