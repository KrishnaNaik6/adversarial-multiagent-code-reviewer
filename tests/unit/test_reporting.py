"""Unit tests for Markdown and JSON reporting."""

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
from adversary.reporting.json_reporter import JSONReporter
from adversary.reporting.markdown import MarkdownReporter


def test_markdown_and_json_reporting() -> None:
    finding = CandidateFinding(
        id="FIND-001",
        title="ZeroDivisionError in calculate_average",
        description="Division by zero on empty input",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=SourceLocation(file_path="src/calc.py", line_start=2, line_end=2),
        originating_tool="ast",
        rule_id="AST-DIV-001",
        verification_status=VerificationStatus.CONFIRMED,
        suggested_remediation="Add empty list check",
    )
    hypothesis = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/calc.py",
        target_function="calculate_average",
        preconditions="numbers=[]",
        trigger_input="[]",
        expected_behavior="0.0",
        defect_behavior="ZeroDivisionError",
        rationale="sum/len without guard",
    )
    test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_div.py",
        code="def test_div():\n    assert calculate_average([]) == 0.0\n",
        strategy="boundary",
    )
    execution = ExecutionResult(
        id="EXEC-001",
        test_id="TEST-001",
        outcome=ExecutionOutcome.FAILED,
        exit_code=1,
        stdout="",
        stderr="",
        exception_name="ZeroDivisionError",
        traceback_summary="Traceback: ZeroDivisionError: division by zero",
        duration_ms=45.0,
    )
    decision = VerificationDecision(
        id="DEC-001",
        finding_id="FIND-001",
        hypothesis_id="HYP-001",
        status=VerificationStatus.CONFIRMED,
        is_attributed_to_target=True,
        explanation="Reproduced ZeroDivisionError in calculate_average",
        evidence_ids=["EXEC-001"],
    )

    report = ReviewReport(
        run_id="RUN-20261102-001",
        repo_path="/path/to/repo",
        git_commit="abc1234",
        findings=[finding],
        hypotheses=[hypothesis],
        tests=[test],
        executions=[execution],
        decisions=[decision],
        summary={
            "total_findings": 1,
            "confirmed": 1,
            "disproved": 0,
            "inconclusive": 0,
            "unverified": 0,
        },
    )

    # 1. Test Markdown generation
    md_reporter = MarkdownReporter()
    md_content = md_reporter.generate_report(report)

    assert "# Adversary Code Review Report" in md_content
    assert "RUN-20261102-001" in md_content
    assert "[FIND-001] ZeroDivisionError in calculate_average" in md_content
    assert "ZeroDivisionError: division by zero" in md_content
    assert "Defect Hypothesis" in md_content
    assert "Adversarial Reproduction Proof" in md_content
    assert "Methodology and Trust Notice" in md_content

    # 2. Test JSON generation
    json_reporter = JSONReporter()
    json_content = json_reporter.generate_report(report)

    assert '"run_id": "RUN-20261102-001"' in json_content
    # Parse back to ReviewReport
    restored = ReviewReport.model_validate_json(json_content)
    assert restored.run_id == report.run_id
    assert len(restored.findings) == 1
    assert restored.findings[0].verification_status == VerificationStatus.CONFIRMED
