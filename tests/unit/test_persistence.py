"""Unit tests for SQLite persistence and querying."""

from pathlib import Path

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
    ReviewReport,
    SourceLocation,
    TestArtifact,
    VerificationDecision,
)
from adversary.persistence.repository import RunStore


def test_save_and_retrieve_run(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    store = RunStore(db_file)

    finding = CandidateFinding(
        id="FIND-001",
        title="ZeroDivisionError",
        description="Division by zero",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=SourceLocation(file_path="src/calc.py", line_start=5, line_end=5),
        originating_tool="ast",
        rule_id="AST-DIV-001",
        verification_status=VerificationStatus.CONFIRMED,
    )
    hypothesis = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/calc.py",
        target_function="divide",
        preconditions="b=0",
        trigger_input="0",
        expected_behavior="ValueError",
        defect_behavior="ZeroDivisionError",
        rationale="Unchecked denominator",
    )
    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_div.py",
        code="def test_div(): pass",
        strategy="boundary",
    )
    execution = ExecutionResult(
        id="EXEC-001",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        stdout="",
        stderr="ZeroDivisionError",
        exception_name="ZeroDivisionError",
        duration_ms=10.5,
    )
    decision = VerificationDecision(
        id="DEC-001",
        finding_id="FIND-001",
        hypothesis_id="HYP-001",
        status=VerificationStatus.CONFIRMED,
        is_attributed_to_target=True,
        explanation="Reproduced ZeroDivisionError",
        evidence_ids=["EXEC-001"],
    )

    report = ReviewReport(
        run_id="RUN-TEST-001",
        repo_path="src/",
        findings=[finding],
        hypotheses=[hypothesis],
        tests=[test],
        executions=[execution],
        decisions=[decision],
        summary={"total_findings": 1, "confirmed": 1},
    )

    store.save_run(report)

    # Retrieve by ID
    loaded = store.get_run("RUN-TEST-001")
    assert loaded is not None
    assert loaded.run_id == "RUN-TEST-001"
    assert len(loaded.findings) == 1
    assert loaded.findings[0].id == "FIND-001"
    assert loaded.findings[0].verification_status == VerificationStatus.CONFIRMED

    # Retrieve latest
    latest = store.get_latest_run()
    assert latest is not None
    assert latest.run_id == "RUN-TEST-001"

    # List runs
    runs = store.list_runs()
    assert len(runs) == 1
    assert runs[0]["run_id"] == "RUN-TEST-001"

    # Get finding details
    details = store.get_finding_details("FIND-001", "RUN-TEST-001")
    assert details is not None
    assert details["finding"].title == "ZeroDivisionError"
    assert details["hypothesis"].id == "HYP-001"
    assert details["test"].id == "TEST-001"
    assert details["execution"].exception_name == "ZeroDivisionError"
    assert details["decision"].status == VerificationStatus.CONFIRMED
