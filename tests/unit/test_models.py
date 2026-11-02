"""Unit tests for typed domain models."""

import pytest
from pydantic import ValidationError

from adversary.models.enums import (
    Confidence,
    ExecutionOutcome,
    FindingCategory,
    Severity,
    VerificationStatus,
)
from adversary.models.schemas import (
    CandidateFinding,
    DefectHypothesis,
    ExecutionResult,
    SourceLocation,
    TestArtifact,
    VerificationDecision,
)


def test_source_location_validation() -> None:
    loc = SourceLocation(file_path="src/calc.py", line_start=10, line_end=15)
    assert loc.file_path == "src/calc.py"
    assert loc.line_start == 10

    # Line numbers must be >= 1
    with pytest.raises(ValidationError):
        SourceLocation(file_path="src/calc.py", line_start=0, line_end=5)


def test_candidate_finding_instantiation() -> None:
    finding = CandidateFinding(
        id="FIND-001",
        title="ZeroDivisionError in calculate_average",
        description="Division by zero when list is empty",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=SourceLocation(file_path="src/calc.py", line_start=2, line_end=2),
        originating_tool="ast_checker",
        rule_id="AST-DIV-001",
    )
    assert finding.id == "FIND-001"
    assert finding.verification_status == VerificationStatus.CANDIDATE


def test_hypothesis_and_test_artifact() -> None:
    hyp = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/calc.py",
        target_function="calculate_average",
        preconditions="numbers is an empty list",
        trigger_input="numbers=[]",
        expected_behavior="Return 0.0 or raise ValueError with informative message",
        defect_behavior="Raises unhandled ZeroDivisionError",
        rationale="len(numbers) evaluates to 0 in sum(numbers)/len(numbers)",
    )
    assert hyp.finding_id == "FIND-001"

    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_calc_empty.py",
        code="def test_empty(): pass",
        strategy="empty_input",
    )
    assert test.strategy == "empty_input"


def test_execution_and_verification_decision() -> None:
    exec_result = ExecutionResult(
        id="EXEC-001",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        stdout="",
        stderr="ZeroDivisionError: division by zero",
        exception_name="ZeroDivisionError",
    )
    assert exec_result.outcome == ExecutionOutcome.FAILED

    decision = VerificationDecision(
        id="DEC-001",
        finding_id="FIND-001",
        hypothesis_id="HYP-001",
        status=VerificationStatus.CONFIRMED,
        is_attributed_to_target=True,
        explanation="ZeroDivisionError reproduced on empty input in calculate_average",
        evidence_ids=["EXEC-001"],
    )
    assert decision.status == VerificationStatus.CONFIRMED
    assert decision.is_attributed_to_target is True
