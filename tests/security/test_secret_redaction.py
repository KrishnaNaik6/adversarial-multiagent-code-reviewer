"""Security tests: Secret and credential redaction audit."""

from adversary.core.logging import redact_secrets


def test_redact_github_pat() -> None:
    pat = "ghp_1234567890abcdef1234567890abcdef1234"
    text = f"Error communicating with GitHub: token={pat}"
    redacted = redact_secrets(text)
    assert pat not in redacted
    assert "[REDACTED" in redacted


def test_redact_bearer_tokens() -> None:
    text = "HTTP Authorization: Bearer abcdef1234567890xyz"
    redacted = redact_secrets(text)
    assert "abcdef1234567890xyz" not in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted


def test_redact_rsa_private_key() -> None:
    raw_key = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1W9a8b+123456789abcdef\n"
        "-----END RSA PRIVATE KEY-----"
    )
    redacted = redact_secrets(raw_key)
    assert "MIIEowIBAAKCAQEA" not in redacted
    assert "[REDACTED_PRIVATE_KEY]" in redacted

