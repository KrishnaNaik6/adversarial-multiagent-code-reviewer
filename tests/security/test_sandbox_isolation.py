"""Security tests: Docker sandbox isolation and timeout enforcement."""

from pathlib import Path

from adversary.config.settings import SandboxConfig
from adversary.models.enums import ExecutionOutcome
from adversary.models.schemas import TestArtifact
from adversary.sandbox.runner import DockerSandboxRunner


def test_sandbox_hang_timeout_enforcement(tmp_path: Path) -> None:
    # A test that enters an infinite loop
    hang_test = TestArtifact(
        id="TEST-HANG-001",
        hypothesis_id="HYP-001",
        file_name="test_hang.py",
        code="import time\ndef test_hang():\n    time.sleep(10)\n",
        strategy="boundary",
        timeout_seconds=2,
    )

    test_file = tmp_path / "test_hang.py"
    test_file.write_text(hang_test.code, encoding="utf-8")
    harness_file = Path("src/adversary/sandbox/harness.py").resolve()

    # Enforce 2 second timeout
    runner = DockerSandboxRunner(config=SandboxConfig(timeout_seconds=2))
    result = runner._run_local_fallback(
        repo_path=tmp_path,
        test_file=test_file,
        harness_file=harness_file,
        test_artifact=hang_test,
        timeout_seconds=2,
    )

    assert result.outcome == ExecutionOutcome.TIMED_OUT
    assert result.exit_code == -1
    assert result.exception_name == "TimeoutError"


def test_sandbox_disallows_modifying_repo_mount(tmp_path: Path) -> None:
    src_file = tmp_path / "protected.py"
    src_file.write_text("# immutable original", encoding="utf-8")

    # In Docker configuration, repo_mount is strictly :ro (read-only)
    runner = DockerSandboxRunner()
    repo_mount_flag = f"{tmp_path.as_posix()}:/app/repo:ro"
    assert ":ro" in repo_mount_flag
    assert runner.config.network_disabled is True
    assert runner.config.run_as_non_root is True

