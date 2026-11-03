"""Unit tests for evaluation framework metrics calculations."""

from pathlib import Path

from adversary.evaluation.harness import EvaluationHarness
from adversary.evaluation.schemas import EvaluationCondition, GroundTruthDefect
from adversary.models.enums import Confidence, FindingCategory, Severity, VerificationStatus
from adversary.models.schemas import CandidateFinding, SourceLocation


def test_evaluation_metrics_computation() -> None:
    gt = [
        GroundTruthDefect(
            id="GT-001",
            target_file="src/pricing.py",
            target_function="calculate_discount",
            line=50,
            category="boundary_condition",
            description="Division by zero",
            expected_exception_or_failure="ZeroDivisionError",
        ),
        GroundTruthDefect(
            id="GT-002",
            target_file="src/orders.py",
            target_function="cancel_order",
            line=80,
            category="lifecycle_contract",
            description="Restock bug",
            expected_exception_or_failure="AssertionError",
        ),
    ]
    harness = EvaluationHarness(target_repo=Path("."), ground_truth=gt)

    finding1 = CandidateFinding(
        id="FIND-1",
        title="calculate_discount",
        description="",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        originating_tool="ast_rules",
        location=SourceLocation(file_path="src/pricing.py", line_start=50, line_end=55),
        verification_status=VerificationStatus.CONFIRMED,
    )
    # Finding 2 is unrelated / false positive
    finding2 = CandidateFinding(
        id="FIND-2",
        title="unrelated_function",
        description="",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.LOW,
        confidence=Confidence.LOW,
        originating_tool="ast_rules",
        location=SourceLocation(file_path="src/other.py", line_start=10, line_end=15),
        verification_status=VerificationStatus.CONFIRMED,
    )

    metrics = harness._compute_metrics(
        condition=EvaluationCondition.CONDITION_D_FULL_EVIDENCE_GATED,
        condition_name="Evidence-Gated Review",
        flagged=[finding1, finding2],
        confirmed=[finding1, finding2],
        start_time=0.0,
        attribution_acc=1.0,
    )

    # 1 True Positive (finding1), 1 False Positive (finding2), 1 False Negative (GT-002)
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1
    assert metrics.precision == 0.5
    assert metrics.recall == 0.5
    assert metrics.f1_score == 0.5
    assert metrics.attribution_accuracy == 1.0
