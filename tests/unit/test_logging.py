"""Unit tests for logging and secret redaction."""

import io
import logging

from adversary.core.logging import get_logger, redact_secrets


def test_redact_secrets() -> None:
    text = "Authorization: Bearer my-secret-api-key-12345678"
    redacted = redact_secrets(text)
    assert "my-secret-api-key-12345678" not in redacted
    assert "[REDACTED" in redacted

    private_key = (
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    )
    redacted_key = redact_secrets(private_key)
    assert "MIIEowIBAAKCAQEA" not in redacted_key
    assert "[REDACTED_PRIVATE_KEY]" in redacted_key


def test_logger_redaction_handler() -> None:
    logger = get_logger("test_adversary_logger")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    for h in logger.handlers:
        for f in h.filters:
            handler.addFilter(f)
    logger.addHandler(handler)

    logger.info("Connecting with api_key='sk-1234567890abcdef1234567890'")
    output = stream.getvalue()
    assert "sk-1234567890abcdef1234567890" not in output
