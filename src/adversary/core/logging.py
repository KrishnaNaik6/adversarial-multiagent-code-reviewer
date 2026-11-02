"""Structured logging with automated secret and credential redaction."""

import logging
import re

# Patterns matching sensitive keys, tokens, credentials, and private keys
SENSITIVE_PATTERNS = [
    re.compile(
        r"(?i)(api[_-]?key|token|secret|password|auth|private_key)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"
    ),
    re.compile(r"(?i)\bbearer\s+([a-zA-Z0-9_\-\.]{8,})"),
    re.compile(
        r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL
    ),
    re.compile(r"(?i)(ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})"),
    re.compile(r"sk-[a-zA-Z0-9]{20,48}"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive credentials, tokens, and secrets from text."""
    if not isinstance(text, str):
        return text

    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        if "PRIVATE KEY" in pattern.pattern:
            redacted = pattern.sub("[REDACTED_PRIVATE_KEY]", redacted)
        elif "bearer" in pattern.pattern.lower():
            redacted = pattern.sub("Bearer [REDACTED_TOKEN]", redacted)
        elif pattern.groups >= 2:
            redacted = pattern.sub(r"\1: [REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter that scrubs sensitive patterns from all record messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: redact_secrets(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_secrets(a) if isinstance(a, str) else a for a in record.args
                )
        return True


def get_logger(name: str = "adversary", level: int = logging.INFO) -> logging.Logger:
    """Configure and return an application logger with redaction filter."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers if already present
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SecretRedactingFilter())
        logger.addHandler(handler)

    return logger
