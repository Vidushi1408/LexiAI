# logging_setup.py
"""Structured logging: JSON lines when LEXI_LOG_FORMAT=json (containers), readable text otherwise."""
import json
import logging
import os
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_lexi_configured", False):
        return
    handler = logging.StreamHandler(sys.stderr)
    if os.getenv("LEXI_LOG_FORMAT", "text") == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root.handlers[:] = [handler]
    root.setLevel(os.getenv("LEXI_LOG_LEVEL", "INFO").upper())
    root._lexi_configured = True  # type: ignore[attr-defined]
