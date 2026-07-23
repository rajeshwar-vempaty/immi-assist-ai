"""Logging helpers — redact secrets from log records."""

from __future__ import annotations

import logging
import re

_PATTERNS = [
    (re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9\-_\.]+)"), r"\1****"),
    (re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"), r"\1****"),
    (re.compile(r"(?i)(encrypted_api_key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)"), r"\1****"),
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), "sk-ant-****"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}"), "sk-****"),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pattern, repl in _PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
            record.args = ()
        except Exception:
            pass
        return True


def install_redacting_filter() -> None:
    filt = RedactingFilter()
    root = logging.getLogger()
    root.addFilter(filt)
    for handler in root.handlers:
        handler.addFilter(filt)
