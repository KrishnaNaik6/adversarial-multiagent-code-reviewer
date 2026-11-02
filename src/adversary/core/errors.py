"""Structured error taxonomy for Adversary."""

from typing import Any


class AdversaryError(Exception):
    """Base exception for all Adversary errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(AdversaryError):
    """Raised when configuration validation or loading fails."""


class RepositoryError(AdversaryError):
    """Raised when repository scanning, path validation, or git operations fail."""


class PathTraversalError(RepositoryError):
    """Raised when an unsafe path or symlink attempts to escape repository root."""


class AnalysisError(AdversaryError):
    """Raised during static analysis or AST parsing failures."""


class TestGenerationError(AdversaryError):
    """Raised when adversarial test generation or validation fails."""


class SandboxError(AdversaryError):
    """Raised when Docker sandbox operations fail."""


class SandboxTimeoutError(SandboxError):
    """Raised when container execution exceeds time budget."""


class SandboxResourceExceededError(SandboxError):
    """Raised when container exceeds memory, CPU, or PID limits."""


class VerificationError(AdversaryError):
    """Raised during independent verification evaluation."""


class PatchError(AdversaryError):
    """Raised during patch creation, application, or regression validation."""


class PersistenceError(AdversaryError):
    """Raised when storage or retrieval fails."""
