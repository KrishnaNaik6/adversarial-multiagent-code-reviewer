"""Independent Verification Engine evaluating execution evidence against bug hypotheses."""

from adversary.core.logging import get_logger
from adversary.models.enums import ExecutionOutcome, VerificationStatus
from adversary.models.schemas import (
    DefectHypothesis,
    ExecutionResult,
    TestArtifact,
    VerificationDecision,
)

logger = get_logger("adversary.verification.verifier")


class IndependentVerifier:
    """Evaluates whether adversarial execution evidence genuinely supports a defect hypothesis."""

    def verify(
        self,
        hypothesis: DefectHypothesis,
        test_artifact: TestArtifact,
        execution_result: ExecutionResult,
    ) -> VerificationDecision:
        """Independently assess execution evidence and determine finding verification status."""
        dec_id = f"DEC-{hypothesis.finding_id}"
        evidence_ids = [execution_result.id]

        # 1. Check for infrastructure, timeout, or invalid test errors
        if execution_result.outcome == ExecutionOutcome.TIMED_OUT:
            return VerificationDecision(
                id=dec_id,
                finding_id=hypothesis.finding_id,
                hypothesis_id=hypothesis.id,
                status=VerificationStatus.INCONCLUSIVE,
                is_attributed_to_target=False,
                explanation="Execution timed out. Cannot confirm defect behavior within execution budget.",
                evidence_ids=evidence_ids,
            )

        if execution_result.outcome in {ExecutionOutcome.ERROR, ExecutionOutcome.INVALID_TEST}:
            return VerificationDecision(
                id=dec_id,
                finding_id=hypothesis.finding_id,
                hypothesis_id=hypothesis.id,
                status=VerificationStatus.EXECUTION_ERROR,
                is_attributed_to_target=False,
                explanation=f"Execution failed due to test harness or environment error: {execution_result.stderr or execution_result.stdout}",
                evidence_ids=evidence_ids,
            )

        # 2. Check if the adversarial test passed (defect was not reproduced)
        if execution_result.outcome == ExecutionOutcome.PASSED:
            return VerificationDecision(
                id=dec_id,
                finding_id=hypothesis.finding_id,
                hypothesis_id=hypothesis.id,
                status=VerificationStatus.DISPROVED,
                is_attributed_to_target=True,
                explanation=f"Adversarial test passed without triggering {hypothesis.defect_behavior}. Defect hypothesis contradicted under tested conditions.",
                evidence_ids=evidence_ids,
            )

        # 3. Execution outcome is FAILED. Check evidence attribution.
        tb_text = (
            execution_result.traceback_summary or execution_result.stdout or execution_result.stderr
        )
        is_attributed = self._is_attributed(hypothesis, tb_text)

        if not is_attributed:
            return VerificationDecision(
                id=dec_id,
                finding_id=hypothesis.finding_id,
                hypothesis_id=hypothesis.id,
                status=VerificationStatus.INCONCLUSIVE,
                is_attributed_to_target=False,
                explanation=f"Test failed, but failure was not attributable to {hypothesis.target_file} ({hypothesis.target_function}). Possible unrelated test harness issue.",
                evidence_ids=evidence_ids,
            )

        # 4. Check if the observed exception matches expected defect behavior
        expected_exc = self._extract_expected_exception(hypothesis.defect_behavior)
        observed_exc = execution_result.exception_name

        if expected_exc and observed_exc and expected_exc != observed_exc:
            # Different exception than hypothesized
            return VerificationDecision(
                id=dec_id,
                finding_id=hypothesis.finding_id,
                hypothesis_id=hypothesis.id,
                status=VerificationStatus.INCONCLUSIVE,
                is_attributed_to_target=True,
                explanation=f"Failure observed, but raised '{observed_exc}' instead of hypothesized '{expected_exc}'.",
                evidence_ids=evidence_ids,
            )

        # 5. Confirmed defect
        return VerificationDecision(
            id=dec_id,
            finding_id=hypothesis.finding_id,
            hypothesis_id=hypothesis.id,
            status=VerificationStatus.CONFIRMED,
            is_attributed_to_target=True,
            explanation=(
                f"Defect successfully reproduced in {hypothesis.target_file} ({hypothesis.target_function}). "
                f"Observed: {observed_exc or 'Assertion failure'}. Evidence strictly matches defect hypothesis."
            ),
            evidence_ids=evidence_ids,
        )

    def _is_attributed(self, hypothesis: DefectHypothesis, traceback_text: str) -> bool:
        """Check if traceback points to target file or target function."""
        # Unrelated errors like ModuleNotFoundError in test setup must not be attributed
        if "ModuleNotFoundError" in traceback_text or "ImportError" in traceback_text:
            return False

        target_file_stem = hypothesis.target_file.split("/")[-1].replace(".py", "")
        return bool(
            target_file_stem in traceback_text
            or (hypothesis.target_function and hypothesis.target_function in traceback_text)
        )

    def _extract_expected_exception(self, defect_behavior: str) -> str | None:
        """Extract anticipated exception name from hypothesis statement if specified."""
        for exc in [
            "ZeroDivisionError",
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "AssertionError",
        ]:
            if exc in defect_behavior:
                return exc
        return None
