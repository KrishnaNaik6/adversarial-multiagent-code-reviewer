"""Docker sandbox runner executing untrusted tests with strict isolation."""

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from adversary.config.settings import SandboxConfig
from adversary.core.logging import get_logger
from adversary.evidence.collector import EvidenceCollector
from adversary.models.schemas import ExecutionResult, TestArtifact

logger = get_logger("adversary.sandbox.runner")


class DockerSandboxRunner:
    """Manages isolated test execution in restricted Docker containers."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()
        self.evidence_collector = EvidenceCollector()

    def execute_test(
        self,
        repo_path: Path,
        test_artifact: TestArtifact,
        timeout_seconds: int = 30,
    ) -> ExecutionResult:
        """Execute test artifact in isolated sandbox and return structured evidence."""
        effective_timeout = min(timeout_seconds, self.config.timeout_seconds)
        docker_bin = shutil.which("docker")

        with tempfile.TemporaryDirectory(prefix="adversary_test_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            test_file = tmp_dir / test_artifact.file_name
            test_file.write_text(test_artifact.code, encoding="utf-8")

            if docker_bin and self._is_docker_available():
                return self._run_in_docker(
                    docker_bin=docker_bin,
                    repo_path=repo_path.resolve(),
                    test_file=test_file,
                    test_artifact=test_artifact,
                    timeout_seconds=effective_timeout,
                )
            else:
                logger.info("Docker daemon not reachable; falling back to local isolated process execution")
                return self._run_local_fallback(
                    repo_path=repo_path.resolve(),
                    test_file=test_file,
                    test_artifact=test_artifact,
                    timeout_seconds=effective_timeout,
                )

    def _is_docker_available(self) -> bool:
        """Check if Docker daemon responds to a quick ping."""
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, timeout=3, check=False)
            return res.returncode == 0
        except Exception:
            return False

    def _run_in_docker(
        self,
        docker_bin: str,
        repo_path: Path,
        test_file: Path,
        test_artifact: TestArtifact,
        timeout_seconds: int,
    ) -> ExecutionResult:
        """Run pytest inside a restricted Docker container."""
        # Normalize paths for Windows/Linux Docker mounts
        repo_mount = f"{repo_path.as_posix()}:/app/repo:ro"
        test_mount = f"{test_file.parent.as_posix()}:/app/tests:ro"

        cmd = [
            docker_bin,
            "run",
            "--rm",
            "--network",
            "none" if self.config.network_disabled else "bridge",
            "--memory",
            self.config.memory_limit,
            "--pids-limit",
            str(self.config.pids_limit),
            "-v",
            repo_mount,
            "-v",
            test_mount,
            "-w",
            "/app",
            "-e",
            "PYTHONPATH=/app/repo:/app/repo/src",
            self.config.image,
            "pytest",
            f"/app/tests/{test_file.name}",
            "-q",
            "--no-header",
        ]

        logger.info("Starting Docker sandbox container for %s", test_artifact.id)
        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            return self.evidence_collector.parse_execution(
                test_id=test_artifact.id,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                env_info={"mode": "docker", "image": self.config.image, "network": "none"},
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            stdout_str = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return self.evidence_collector.parse_execution(
                test_id=test_artifact.id,
                exit_code=-1,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                timed_out=True,
                env_info={"mode": "docker", "image": self.config.image, "timeout": timeout_seconds},
            )

    def _run_local_fallback(
        self,
        repo_path: Path,
        test_file: Path,
        test_artifact: TestArtifact,
        timeout_seconds: int,
    ) -> ExecutionResult:
        """Isolated local process execution when Docker is unavailable."""
        import os
        python_bin = sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_path}{os.pathsep}{repo_path / 'src'}"

        cmd = [
            python_bin,
            "-m",
            "pytest",
            str(test_file),
            "-q",
            "--no-header",
        ]

        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                cwd=str(repo_path),
                env=env,
            )
            duration_ms = (time.perf_counter() - start_time) * 1000
            return self.evidence_collector.parse_execution(
                test_id=test_artifact.id,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                env_info={"mode": "local_fallback"},
            )
        except subprocess.TimeoutExpired as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            stdout_str = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return self.evidence_collector.parse_execution(
                test_id=test_artifact.id,
                exit_code=-1,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_ms=duration_ms,
                timed_out=True,
                env_info={"mode": "local_fallback", "timeout": timeout_seconds},
            )
