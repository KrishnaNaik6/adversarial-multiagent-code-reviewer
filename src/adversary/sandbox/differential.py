"""Differential runner executing adversarial tests across base and target revisions."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.schemas import ExecutionResult, TestArtifact
from adversary.sandbox.runner import DockerSandboxRunner

logger = get_logger("adversary.sandbox.differential")


class DifferentialRunner:
    """Executes identical adversarial tests against target and baseline revisions.

    Distinguishes newly introduced regressions from pre-existing repository defects.
    """

    def __init__(self, runner: DockerSandboxRunner | None = None) -> None:
        self.runner = runner or DockerSandboxRunner()

    def run_differential_test(
        self,
        target_repo: Path,
        base_ref: str | None,
        test_artifact: TestArtifact,
        timeout_seconds: int = 30,
    ) -> tuple[ExecutionResult, ExecutionResult | None]:
        """Run the test artifact against target repo, and if base_ref is supplied, against base.

        Returns (target_result, base_result).
        """
        # 1. Execute against target repo
        target_result = self.runner.execute_test(
            repo_path=target_repo,
            test_artifact=test_artifact,
            timeout_seconds=timeout_seconds,
        )

        if not base_ref:
            return target_result, None

        # 2. Check out base_ref in an isolated temporary location
        base_result: ExecutionResult | None = None
        base_checkout_dir = self._create_base_checkout(target_repo, base_ref)

        if base_checkout_dir:
            try:
                logger.info(
                    "Executing differential baseline test for %s against %s",
                    test_artifact.id,
                    base_ref,
                )
                base_result = self.runner.execute_test(
                    repo_path=base_checkout_dir,
                    test_artifact=test_artifact,
                    timeout_seconds=timeout_seconds,
                )
            finally:
                self._cleanup_base_checkout(target_repo, base_checkout_dir)
        else:
            logger.warning(
                "Could not create baseline checkout for ref '%s'; differential execution skipped",
                base_ref,
            )

        return target_result, base_result

    def _create_base_checkout(self, repo_path: Path, base_ref: str) -> Path | None:
        """Create an isolated checkout of base_ref without mutating the target working tree."""
        git_bin = shutil.which("git")
        if not git_bin or not (repo_path / ".git").exists():
            return None

        # Verify base_ref exists
        check_ref = subprocess.run(
            [git_bin, "-C", str(repo_path), "rev-parse", "--verify", base_ref],
            capture_output=True,
            text=True,
            check=False,
        )
        if check_ref.returncode != 0:
            logger.debug("Base ref %s not found in %s", base_ref, repo_path)
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="adversary_diff_base_"))

        # Strategy 1: Git worktree (very fast, shared storage)
        worktree_res = subprocess.run(
            [git_bin, "-C", str(repo_path), "worktree", "add", "--detach", str(tmp_dir), base_ref],
            capture_output=True,
            text=True,
            check=False,
        )
        if worktree_res.returncode == 0:
            return tmp_dir

        # Strategy 2: Fallback to git clone --shared
        clone_res = subprocess.run(
            [git_bin, "clone", "--shared", "--branch", base_ref, str(repo_path), str(tmp_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if clone_res.returncode == 0:
            return tmp_dir

        # Cleanup if both failed
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None

    def _cleanup_base_checkout(self, repo_path: Path, checkout_dir: Path) -> None:
        """Safely prune worktree or remove temporary directory."""
        git_bin = shutil.which("git")
        if git_bin and (repo_path / ".git").exists():
            subprocess.run(
                [git_bin, "-C", str(repo_path), "worktree", "remove", "--force", str(checkout_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
        shutil.rmtree(checkout_dir, ignore_errors=True)
