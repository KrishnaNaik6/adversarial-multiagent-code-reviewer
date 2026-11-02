"""Unit tests for Blue Team repair generation, regression verification, and human gate."""

from pathlib import Path

import pytest

from adversary.core.errors import PatchError
from adversary.models.enums import (
    Confidence,
    FindingCategory,
    RepairStatus,
    Severity,
    VerificationStatus,
)
from adversary.models.schemas import (
    CandidateFinding,
    DefectHypothesis,
    SourceLocation,
    TestArtifact,
)
from adversary.patching.applier import PatchApplier
from adversary.patching.patcher import BlueTeamPatcher


def test_blue_team_patch_and_verify(tmp_path: Path) -> None:
    # Setup test workspace
    src_file = tmp_path / "calculator.py"
    src_file.write_text(
        "def calculate_average(numbers: list[float]) -> float:\n    return sum(numbers) / len(numbers)\n",
        encoding="utf-8",
    )

    finding = CandidateFinding(
        id="FIND-001",
        title="Potential division by zero with empty collection",
        description="Division by zero",
        category=FindingCategory.BOUNDARY_CONDITION,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=SourceLocation(file_path="calculator.py", line_start=2, line_end=2),
        originating_tool="ast_rules",
        rule_id="AST-DIV-002",
        verification_status=VerificationStatus.CONFIRMED,
    )
    hypothesis = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="calculator.py",
        target_function="calculate_average",
        preconditions="numbers=[]",
        trigger_input="[]",
        expected_behavior="0.0",
        defect_behavior="ZeroDivisionError",
        rationale="calculate_average in calculator.py",
    )
    reproduction_test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_adv.py",
        code=(
            "from calculator import calculate_average\n"
            "def test_div():\n"
            "    res = calculate_average([])\n"
            "    assert res == 0.0\n"
        ),
        strategy="boundary",
    )

    patcher = BlueTeamPatcher()
    patch = patcher.propose_and_verify_repair(finding, hypothesis, reproduction_test, tmp_path)

    assert patch is not None
    assert patch.repair_status == RepairStatus.VALIDATED
    assert patch.adversarial_test_passed is True
    assert patch.regression_tests_passed is True
    assert "+    if not numbers:" in patch.diff
    assert patch.applied_to_repo is False


def test_human_approval_gate(tmp_path: Path) -> None:
    src_file = tmp_path / "calculator.py"
    src_file.write_text(
        "def calculate_average(numbers: list[float]) -> float:\n    return sum(numbers) / len(numbers)\n",
        encoding="utf-8",
    )

    finding = CandidateFinding(
        id="FIND-001",
        title="Division by zero",
        description="",
        category=FindingCategory.CORRECTNESS,
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        location=SourceLocation(file_path="calculator.py", line_start=2, line_end=2),
        originating_tool="ast",
    )
    hypothesis = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="calculator.py",
        preconditions="",
        trigger_input="",
        expected_behavior="",
        defect_behavior="",
        rationale="",
    )
    reproduction_test = TestArtifact(
        id="TEST-001",
        hypothesis_id="HYP-001",
        file_name="test_adv.py",
        code="from calculator import calculate_average\ndef test_div(): assert calculate_average([]) == 0.0\n",
        strategy="boundary",
    )

    patcher = BlueTeamPatcher()
    patch = patcher.propose_and_verify_repair(finding, hypothesis, reproduction_test, tmp_path)
    assert patch is not None

    applier = PatchApplier()

    # Rejects application if human_approved is False
    with pytest.raises(PatchError, match="requires explicit human approval"):
        applier.apply_patch(patch, repo_path=tmp_path, human_approved=False)

    # Accepts and modifies file when human_approved is True
    applied = applier.apply_patch(patch, repo_path=tmp_path, human_approved=True)
    assert applied is True
    assert patch.applied_to_repo is True
    new_content = src_file.read_text(encoding="utf-8")
    assert "if not numbers:" in new_content

