"""Blue Team / Patcher agent proposing minimal repairs and regression verification."""

import difflib
import shutil
import tempfile
from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.enums import ExecutionOutcome, RepairStatus
from adversary.models.schemas import CandidateFinding, DefectHypothesis, PatchArtifact, TestArtifact
from adversary.sandbox.runner import DockerSandboxRunner

logger = get_logger("adversary.patching.patcher")


class BlueTeamPatcher:
    """Proposes minimal bug repairs in isolated workspaces and verifies them against regression suites."""

    def __init__(self) -> None:
        self.sandbox = DockerSandboxRunner()

    def propose_and_verify_repair(
        self,
        finding: CandidateFinding,
        hypothesis: DefectHypothesis,
        reproduction_test: TestArtifact,
        repo_path: Path,
    ) -> PatchArtifact | None:
        """Formulate patch in isolated temporary workspace and verify with adversarial and regression tests."""
        target_file = repo_path / finding.location.file_path
        if not target_file.exists():
            logger.warning("Target file %s does not exist for patch proposal", target_file)
            return None

        original_code = target_file.read_text(encoding="utf-8")
        patched_code = self._generate_minimal_fix(original_code, finding, hypothesis)

        if patched_code == original_code:
            logger.info("Could not formulate deterministic patch for finding %s", finding.id)
            return None

        # Generate unified diff
        diff_lines = list(
            difflib.unified_diff(
                original_code.splitlines(keepends=True),
                patched_code.splitlines(keepends=True),
                fromfile=f"a/{finding.location.file_path}",
                tofile=f"b/{finding.location.file_path}",
            )
        )
        diff_str = "".join(diff_lines)

        # Execute verification in an isolated temporary working copy
        with tempfile.TemporaryDirectory(prefix="adversary_patch_") as isolated_dir_str:
            isolated_repo = Path(isolated_dir_str) / "repo"
            shutil.copytree(repo_path, isolated_repo)

            # Apply patch to isolated copy
            isolated_target = isolated_repo / finding.location.file_path
            isolated_target.write_text(patched_code, encoding="utf-8")

            # 1. Run the original adversarial reproduction test
            # On the patched code, the adversarial test MUST PASS!
            adv_res = self.sandbox.execute_test(
                repo_path=isolated_repo,
                test_artifact=reproduction_test,
                timeout_seconds=reproduction_test.timeout_seconds,
            )
            adversarial_passed = adv_res.outcome == ExecutionOutcome.PASSED

            # 2. Run existing regression tests in isolated repo
            regression_passed = True
            for existing_test in isolated_repo.rglob("test_*.py"):
                if existing_test.name.startswith("test_adv_"):
                    continue
                reg_artifact = TestArtifact(
                    id=f"REG-{existing_test.name}",
                    hypothesis_id=hypothesis.id,
                    file_name=existing_test.name,
                    code=existing_test.read_text(encoding="utf-8"),
                    strategy="regression",
                )
                reg_res = self.sandbox.execute_test(
                    repo_path=isolated_repo,
                    test_artifact=reg_artifact,
                    timeout_seconds=15,
                )
                if reg_res.outcome != ExecutionOutcome.PASSED:
                    regression_passed = False
                    break

            is_validated = adversarial_passed and regression_passed
            status = RepairStatus.VALIDATED if is_validated else RepairStatus.REVERTED

            explanation = (
                f"Minimal repair for {finding.id} in {finding.location.file_path}. "
                f"Adversarial proof passed: {adversarial_passed}. "
                f"Regression tests passed: {regression_passed}."
            )

            patch_artifact = PatchArtifact(
                id=f"PATCH-{finding.id}",
                finding_id=finding.id,
                diff=diff_str,
                affected_files=[finding.location.file_path],
                explanation=explanation,
                repair_status=status,
                adversarial_test_passed=adversarial_passed,
                regression_tests_passed=regression_passed,
                applied_to_repo=False,
            )

            logger.info("Formulated patch %s with status %s", patch_artifact.id, status)
            return patch_artifact

    def _generate_minimal_fix(
        self,
        code: str,
        finding: CandidateFinding,
        hypothesis: DefectHypothesis,
    ) -> str:
        """Formulate deterministic minimal code adjustment targeting the defect pattern."""
        lines = code.splitlines(keepends=True)

        # Division by zero: insert guard check
        if "division by zero" in finding.title.lower() or "AST-DIV" in (finding.rule_id or ""):
            line_idx = finding.location.line_start - 1
            if 0 <= line_idx < len(lines):
                target_line = lines[line_idx]
                indent = len(target_line) - len(target_line.lstrip())
                indent_str = " " * indent

                # Extract collection variable from denominator if possible
                if "len(" in target_line:
                    var_name = target_line.split("len(")[1].split(")")[0].strip()
                    guard = f"{indent_str}if not {var_name}:\n{indent_str}    return 0.0\n"
                    lines.insert(line_idx, guard)
                    return "".join(lines)

        return code

