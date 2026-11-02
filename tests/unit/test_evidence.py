"""Unit tests for evidence collection and parsing."""

from adversary.evidence.collector import EvidenceCollector
from adversary.models.enums import ExecutionOutcome


def test_parse_passed_execution() -> None:
    collector = EvidenceCollector()
    result = collector.parse_execution(
        test_id="TEST-001",
        exit_code=0,
        stdout="1 passed in 0.05s",
        stderr="",
        duration_ms=50.0,
    )
    assert result.outcome == ExecutionOutcome.PASSED
    assert result.exit_code == 0
    assert result.exception_name is None


def test_parse_failed_execution_with_zerodivision() -> None:
    collector = EvidenceCollector()
    stdout = """
=================================== FAILURES ===================================
_________________________ test_division_on_empty_input _________________________
    def test_division():
>       calc([])
ZeroDivisionError: division by zero
"""
    result = collector.parse_execution(
        test_id="TEST-002",
        exit_code=1,
        stdout=stdout,
        stderr="",
        duration_ms=85.0,
    )
    assert result.outcome == ExecutionOutcome.FAILED
    assert result.exit_code == 1
    assert result.exception_name == "ZeroDivisionError"
    assert result.traceback_summary is not None
    assert "ZeroDivisionError: division by zero" in result.traceback_summary


def test_parse_timed_out_execution() -> None:
    collector = EvidenceCollector()
    result = collector.parse_execution(
        test_id="TEST-003",
        exit_code=-1,
        stdout="",
        stderr="",
        duration_ms=30000.0,
        timed_out=True,
    )
    assert result.outcome == ExecutionOutcome.TIMED_OUT
    assert result.exit_code == -1
    assert result.exception_name == "TimeoutError"


def test_parse_invalid_test_execution() -> None:
    collector = EvidenceCollector()
    result = collector.parse_execution(
        test_id="TEST-004",
        exit_code=2,
        stdout="ERROR: usage / syntax error",
        stderr="",
        duration_ms=10.0,
    )
    assert result.outcome == ExecutionOutcome.INVALID_TEST
