"""Unit tests for differential runner and baseline outcome classification."""

from pathlib import Path
from unittest.mock import MagicMock

from adversary.models.enums import DifferentialOutcome, ExecutionOutcome, VerificationStatus
from adversary.models.schemas import DefectHypothesis, ExecutionResult, TestArtifact
from adversary.sandbox.differential import DifferentialRunner
from adversary.verification.verifier import IndependentVerifier


def test_differential_outcome_new_regression() -> None:
    verifier = IndependentVerifier()
    hyp = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/pricing.py",
        target_function="calculate_discount",
        preconditions="Valid items",
        trigger_input="[]",
        expected_behavior="Return 0.0",
        defect_behavior="ZeroDivisionError",
        rationale="Empty list causes division by zero",
    )
    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_adv.py",
        code="def test_adv(): pass",
        strategy="boundary",
    )
    target_res = ExecutionResult(
        id="EXEC-TGT",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        exception_name="ZeroDivisionError",
        traceback_summary="File src/pricing.py, line 20 in calculate_discount\nZeroDivisionError",
        stdout="",
        stderr="ZeroDivisionError: division by zero",
        duration_ms=10.0,
    )
    base_res = ExecutionResult(
        id="EXEC-BASE",
        test_id="TEST-001",
        outcome=ExecutionOutcome.PASSED,
        exit_code=0,
        exception_name=None,
        traceback_summary=None,
        stdout="OK",
        stderr="",
        duration_ms=10.0,
    )

    decision = verifier.verify(
        hypothesis=hyp,
        test_artifact=test,
        execution_result=target_res,
        base_execution_result=base_res,
    )
    assert decision.status == VerificationStatus.CONFIRMED
    assert decision.differential_outcome == DifferentialOutcome.NEW_REGRESSION
    assert "NEW_REGRESSION" in decision.explanation


def test_differential_outcome_pre_existing_defect() -> None:
    verifier = IndependentVerifier()
    hyp = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/pricing.py",
        target_function="calculate_discount",
        preconditions="Valid items",
        trigger_input="[]",
        expected_behavior="Return 0.0",
        defect_behavior="ZeroDivisionError",
        rationale="Empty list causes division by zero",
    )
    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_adv.py",
        code="def test_adv(): pass",
        strategy="boundary",
    )
    target_res = ExecutionResult(
        id="EXEC-TGT",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        exception_name="ZeroDivisionError",
        traceback_summary="File src/pricing.py, line 20 in calculate_discount\nZeroDivisionError",
        stdout="",
        stderr="ZeroDivisionError",
        duration_ms=10.0,
    )
    base_res = ExecutionResult(
        id="EXEC-BASE",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        exception_name="ZeroDivisionError",
        traceback_summary="File src/pricing.py, line 20 in calculate_discount\nZeroDivisionError",
        stdout="",
        stderr="ZeroDivisionError",
        duration_ms=10.0,
    )

    decision = verifier.verify(
        hypothesis=hyp,
        test_artifact=test,
        execution_result=target_res,
        base_execution_result=base_res,
    )
    assert decision.status == VerificationStatus.CONFIRMED
    assert decision.differential_outcome == DifferentialOutcome.PRE_EXISTING_DEFECT
    assert "PRE_EXISTING_DEFECT" in decision.explanation


def test_differential_runner_without_base_ref() -> None:
    mock_runner = MagicMock()
    mock_runner.execute_test.return_value = ExecutionResult(
        id="EXEC-1",
        test_id="TEST-1",
        outcome=ExecutionOutcome.PASSED,
        exit_code=0,
        exception_name=None,
        traceback_summary=None,
        stdout="",
        stderr="",
        duration_ms=5.0,
    )
    diff = DifferentialRunner(runner=mock_runner)
    test = TestArtifact(
        id="TEST-1",
        hypothesis_id="HYP-1",
        file_name="test.py",
        code="def test(): pass",
        strategy="boundary",
    )
    target_res, base_res = diff.run_differential_test(Path("."), base_ref=None, test_artifact=test)
    assert target_res.outcome == ExecutionOutcome.PASSED
    assert base_res is None
    assert mock_runner.execute_test.call_count == 1
