import json
import logging
from pathlib import Path

from autoforge.core.config import LoggingConfig
from autoforge.infrastructure.observability import configure_logging


def test_configure_logging_writes_redacted_json_to_file(tmp_path: Path) -> None:
    logger = logging.getLogger("autoforge")
    original_handlers = list(logger.handlers)
    original_level = logger.level
    original_propagate = logger.propagate
    try:
        configure_logging(
            LoggingConfig(directory=tmp_path / "logs", max_bytes=1024, backup_count=1)
        )
        logging.getLogger("autoforge.worker").info(
            "connected postgresql://worker:password@db/autoforge token=visible",
            extra={"autoforge_job_id": "job-1", "secret": "must-not-appear"},
        )
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            logger.addHandler(handler)
        logger.setLevel(original_level)
        logger.propagate = original_propagate

    log_path = next((tmp_path / "logs").glob("*.log"))
    payload = json.loads(log_path.read_text(encoding="utf-8"))

    assert payload["autoforge_job_id"] == "job-1"
    assert "password" not in payload["message"]
    assert "visible" not in payload["message"]
    assert "must-not-appear" not in log_path.read_text(encoding="utf-8")
