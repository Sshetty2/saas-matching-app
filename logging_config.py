import logging
import logging.handlers
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger
from typing import Optional, Dict, Any

from config import settings

_is_configured = False


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name

        # Add error details if available
        if record.exc_info:
            log_record["error_type"] = record.exc_info[0].__name__
            log_record["error_message"] = str(record.exc_info[1])


@contextmanager
def log_execution_time(logger: logging.Logger, operation: str):
    """Context manager to log operation execution time"""
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        logger.info(
            f"Operation {operation} completed",
            extra={
                "execution_time_ms": round(execution_time * 1000, 2),
            },
        )


def configure_logging() -> logging.Logger:
    """Configure logging for the application with structured JSON logging"""
    global _is_configured

    if _is_configured:
        return logging.getLogger("cpe_matching_agent")

    log_dir = Path(settings.logging.log_file).parent
    log_dir.mkdir(exist_ok=True, parents=True)

    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(logging.INFO)

    formatter = CustomJsonFormatter(
        "%(level)s %(timestamp)s %(message)s", json_ensure_ascii=False
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    app_handler = logging.handlers.TimedRotatingFileHandler(
        settings.logging.log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    error_handler = logging.handlers.TimedRotatingFileHandler(
        str(log_dir / "error.log"),
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger = logging.getLogger("cpe_matching_agent")
    logger.info(
        "Logging initialized",
        extra={
            "log_format": settings.logging.log_format,
            "log_file": str(settings.logging.log_file),
        },
    )

    _is_configured = True
    return logger
