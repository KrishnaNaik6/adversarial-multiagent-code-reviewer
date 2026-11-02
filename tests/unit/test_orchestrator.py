"""Unit tests for multi-agent workflow orchestration."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from adversary.cli.main import app
from adversary.core.errors import AdversaryError
from adversary.models.enums import VerificationStatus
from adversary.orchestration.coordinator import ReviewOrchestrator
from adversary.orchestration.state import WorkflowContext, WorkflowState


def test_workflow_state_transitions() -> None:
    ctx = WorkflowContext("RUN-001")
    assert ctx.current_state == WorkflowState.CREATED

    ctx.transition_to(WorkflowState.INDEXED, "Indexed")
    assert ctx.current_state.value == WorkflowState.INDEXED.value

    ctx.transition_to(WorkflowState.ANALYZED, "Analyzed")
    assert ctx.current_state.value == WorkflowState.ANALYZED.value

    # Invalid jump from ANALYZED to COMPLETED must raise AdversaryError
    with pytest.raises(AdversaryError, match="Invalid workflow state transition"):
        ctx.transition_to(WorkflowState.COMPLETED)


def test_orchestrator_full_run_on_fixtures() -> None:
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    orchestrator = ReviewOrchestrator()
    report = orchestrator.run(fixtures_dir)

    assert report.run_id.startswith("RUN-")
    assert len(report.findings) >= 4
    assert len(report.hypotheses) >= 4
    assert len(report.tests) >= 4
    assert len(report.executions) >= 4
    assert len(report.decisions) >= 4

    # Confirmed findings should include ZeroDivisionError or mutable defaults
    confirmed = [
        f for f in report.findings if f.verification_status == VerificationStatus.CONFIRMED
    ]
    assert len(confirmed) >= 1
    assert report.summary["confirmed"] >= 1


def test_cli_review_command() -> None:
    runner = CliRunner()
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    result = runner.invoke(app, ["review", str(fixtures_dir)])

    assert result.exit_code == 0
    assert "Review Results for" in result.stdout
    assert "Verification Summary" in result.stdout
