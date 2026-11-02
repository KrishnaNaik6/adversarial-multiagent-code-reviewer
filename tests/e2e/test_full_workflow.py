"""End-to-end integration tests: Complete closed-loop review, repair, and re-review lifecycle."""

from pathlib import Path

from typer.testing import CliRunner

from adversary.cli.main import app
from adversary.models.enums import VerificationStatus
from adversary.orchestration.coordinator import ReviewOrchestrator
from adversary.patching.applier import PatchApplier
from adversary.patching.patcher import BlueTeamPatcher

runner = CliRunner()


def test_full_closed_loop_lifecycle(tmp_path: Path) -> None:
    # 1. Setup sample project with a seeded defect
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    calc_file = src_dir / "calculator.py"
    calc_file.write_text(
        "def calculate_average(numbers: list[float]) -> float:\n"
        "    \"\"\"Calculate mean of numbers.\"\"\"\n"
        "    return sum(numbers) / len(numbers)\n",
        encoding="utf-8",
    )

    # 2. Ingest, Analyze, Hypothesize, Test in Sandbox, Independently Verify
    orchestrator = ReviewOrchestrator()
    report = orchestrator.run(tmp_path)

    assert report.summary["total_findings"] >= 1
    assert report.summary["confirmed"] >= 1

    confirmed_finding = next(
        f for f in report.findings if f.verification_status == VerificationStatus.CONFIRMED
    )
    assert "division by zero" in confirmed_finding.title.lower()

    # 3. Retrieve correlated hypothesis and reproduction test
    hypothesis = next(h for h in report.hypotheses if h.finding_id == confirmed_finding.id)
    test = next(t for t in report.tests if t.hypothesis_id == hypothesis.id)
    decision = next(d for d in report.decisions if d.finding_id == confirmed_finding.id)

    assert decision.status == VerificationStatus.CONFIRMED
    assert decision.is_attributed_to_target is True

    # 4. Propose minimal repair in isolated working copy
    patcher = BlueTeamPatcher()
    patch = patcher.propose_and_verify_repair(
        finding=confirmed_finding,
        hypothesis=hypothesis,
        reproduction_test=test,
        repo_path=tmp_path,
    )

    assert patch is not None
    assert patch.adversarial_test_passed is True
    assert patch.regression_tests_passed is True
    assert "+    if not numbers:" in patch.diff

    # 5. Apply patch to original repository with human approval
    applier = PatchApplier()
    applied = applier.apply_patch(patch, repo_path=tmp_path, human_approved=True)
    assert applied is True

    # 6. Re-review the repaired repository: defect should NO LONGER be confirmed!
    re_report = orchestrator.run(tmp_path)
    re_confirmed = [
        f for f in re_report.findings if f.verification_status == VerificationStatus.CONFIRMED
    ]
    assert len(re_confirmed) == 0, f"Expected 0 confirmed defects after repair, got {len(re_confirmed)}"


def test_cli_e2e_commands(tmp_path: Path) -> None:
    # Test adversary init
    init_res = runner.invoke(app, ["init", str(tmp_path)])
    assert init_res.exit_code == 0
    assert "[OK]" in init_res.stdout

    # Test adversary review
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    rev_res = runner.invoke(app, ["review", str(fixtures_dir)])
    assert rev_res.exit_code == 0

    # Test adversary findings
    find_res = runner.invoke(app, ["findings"])
    assert find_res.exit_code == 0
    assert "FIND-001" in find_res.stdout

    # Test adversary explain
    exp_res = runner.invoke(app, ["explain", "FIND-001"])
    assert exp_res.exit_code == 0
    assert "Finding Details: FIND-001" in exp_res.stdout
    assert "Execution Evidence" in exp_res.stdout

    # Test adversary report markdown & json
    rep_md = runner.invoke(app, ["report", "--format", "markdown"])
    assert rep_md.exit_code == 0
    assert "# Adversary Code Review Report" in rep_md.stdout

    rep_json = runner.invoke(app, ["report", "--format", "json"])
    assert rep_json.exit_code == 0
    assert '"run_id":' in rep_json.stdout

