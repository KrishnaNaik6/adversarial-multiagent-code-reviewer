"""Unit tests for Docker sandbox runner and isolation."""

import hashlib
from pathlib import Path

from adversary.config.settings import SandboxConfig
from adversary.models.enums import ExecutionOutcome
from adversary.models.schemas import TestArtifact
from adversary.sandbox.runner import DockerSandboxRunner


def test_sandbox_fallback_execution(tmp_path: Path) -> None:
    # Setup test file
    repo_file = tmp_path / "calculator.py"
    repo_file.write_text("def divide(a, b): return a / b\n", encoding="utf-8")
    initial_hash = hashlib.sha256(repo_file.read_bytes()).hexdigest()

    # Create adversarial test that triggers ZeroDivisionError
    test_artifact = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_div.py",
        code="from calculator import divide\ndef test_div(): divide(10, 0)\n",
        strategy="boundary",
    )

    test_file = tmp_path / "test_div.py"
    test_file.write_text(test_artifact.code, encoding="utf-8")

    runner = DockerSandboxRunner(config=SandboxConfig(timeout_seconds=10))
    result = runner._run_local_fallback(
        repo_path=tmp_path,
        test_file=test_file,
        test_artifact=test_artifact,
        timeout_seconds=10,
    )

    assert result.test_id == "TEST-001"
    assert result.outcome == ExecutionOutcome.FAILED
    assert result.exception_name == "ZeroDivisionError"
    assert result.duration_ms > 0

    # Ensure source repository was not modified
    current_hash = hashlib.sha256(repo_file.read_bytes()).hexdigest()
    assert current_hash == initial_hash, "Target repository file was unexpectedly modified"
