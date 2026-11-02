"""Unit tests for the Independent Verification Engine."""

from adversary.models.enums import ExecutionOutcome, VerificationStatus
from adversary.models.schemas import DefectHypothesis, ExecutionResult, TestArtifact
from adversary.verification.verifier import IndependentVerifier


def test_verify_confirmed_defect() -> None:
    hyp = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/calculator.py",
        target_function="calculate_average",
        preconditions="empty list",
        trigger_input="numbers=[]",
        expected_behavior="0.0 or ValueError",
        defect_behavior="ZeroDivisionError",
        rationale="Division by len without check",
    )
    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_div.py",
        code="...",
        strategy="boundary",
    )
    exec_result = ExecutionResult(
        id="EXEC-001",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        stdout="",
        stderr="",
        exception_name="ZeroDivisionError",
        traceback_summary="File 'src/calculator.py', line 5, in calculate_average\nZeroDivisionError: division by zero",
    )

    verifier = IndependentVerifier()
    decision = verifier.verify(hyp, test, exec_result)

    assert decision.status == VerificationStatus.CONFIRMED
    assert decision.is_attributed_to_target is True
    assert "Defect successfully reproduced" in decision.explanation
    assert decision.evidence_ids == ["EXEC-001"]


def test_verify_disproved_when_test_passes() -> None:
    hyp = DefectHypothesis(
        id="HYP-002",
        finding_id="FIND-002",
        target_file="clean.py",
        target_function="calculate_average_safe",
        preconditions="empty list",
        trigger_input="numbers=[]",
        expected_behavior="0.0",
        defect_behavior="ZeroDivisionError",
        rationale="Safe function",
    )
    test = TestArtifact(id="TEST-002", hypothesis_id="HYP-002", file_name="t.py", code="...", strategy="boundary")
    exec_result = ExecutionResult(
        id="EXEC-002",
        test_id="TEST-002",
        outcome=ExecutionOutcome.PASSED,
        exit_code=0,
        stdout="1 passed",
        stderr="",
    )

    verifier = IndependentVerifier()
    decision = verifier.verify(hyp, test, exec_result)

    assert decision.status == VerificationStatus.DISPROVED
    assert "Defect hypothesis contradicted" in decision.explanation


def test_verify_inconclusive_on_timeout() -> None:
    hyp = DefectHypothesis(
        id="HYP-003",
        finding_id="FIND-003",
        target_file="app.py",
        target_function="run",
        preconditions="",
        trigger_input="",
        expected_behavior="",
        defect_behavior="Crash",
        rationale="",
    )
    test = TestArtifact(id="TEST-003", hypothesis_id="HYP-003", file_name="t.py", code="...", strategy="boundary")
    exec_result = ExecutionResult(
        id="EXEC-003",
        test_id="TEST-003",
        outcome=ExecutionOutcome.TIMED_OUT,
        exit_code=-1,
        stdout="",
        stderr="Timed out",
    )

    verifier = IndependentVerifier()
    decision = verifier.verify(hyp, test, exec_result)

    assert decision.status == VerificationStatus.INCONCLUSIVE
    assert decision.is_attributed_to_target is False


def test_verify_execution_error_on_unrelated_import_failure() -> None:
    hyp = DefectHypothesis(
        id="HYP-004",
        finding_id="FIND-004",
        target_file="calc.py",
        target_function="divide",
        preconditions="",
        trigger_input="",
        expected_behavior="",
        defect_behavior="ZeroDivisionError",
        rationale="",
    )
    test = TestArtifact(id="TEST-004", hypothesis_id="HYP-004", file_name="t.py", code="...", strategy="boundary")
    exec_result = ExecutionResult(
        id="EXEC-004",
        test_id="TEST-004",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        stdout="",
        stderr="",
        exception_name="ModuleNotFoundError",
        traceback_summary="ModuleNotFoundError: No module named 'non_existent_pkg'",
    )

    verifier = IndependentVerifier()
    decision = verifier.verify(hyp, test, exec_result)

    # Must NOT be marked CONFIRMED!
    assert decision.status == VerificationStatus.INCONCLUSIVE
    assert decision.is_attributed_to_target is False
    assert "not attributable" in decision.explanation
