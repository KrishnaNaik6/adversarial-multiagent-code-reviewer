"""Unit tests for adversarial test generation and validation."""

import pytest

from adversary.core.errors import TestGenerationError
from adversary.models.schemas import DefectHypothesis, RepositoryManifest
from adversary.test_generation.breaker import BreakerAgent
from adversary.test_generation.validator import TestValidator


def test_validator_valid_code() -> None:
    validator = TestValidator()
    code = "def test_example(): assert True"
    validator.validate(code)  # Should not raise


def test_validator_syntax_error() -> None:
    validator = TestValidator()
    code = "def test_invalid(: assert"
    with pytest.raises(TestGenerationError, match="invalid syntax"):
        validator.validate(code)


def test_validator_no_test_functions() -> None:
    validator = TestValidator()
    code = "def helper_function(): return 42"
    with pytest.raises(TestGenerationError, match="does not define any 'test_\\*' functions"):
        validator.validate(code)


def test_validator_rejects_unsafe_code() -> None:
    validator = TestValidator()
    code = "import socket\ndef test_net(): s = socket.socket()"
    with pytest.raises(TestGenerationError, match="Disallowed module import"):
        validator.validate(code)


def test_breaker_generates_division_test() -> None:
    hyp = DefectHypothesis(
        id="HYP-001",
        finding_id="FIND-001",
        target_file="src/calculator.py",
        target_function="calculate_average",
        preconditions="numbers is empty",
        trigger_input="numbers=[]",
        expected_behavior="Return 0.0 or raise ValueError",
        defect_behavior="Uncaught ZeroDivisionError",
        rationale="In src/calculator.py (calculate_average), division without len check.",
    )
    manifest = RepositoryManifest(root_path=".", source_files=["src/calculator.py"])

    breaker = BreakerAgent()
    artifacts = breaker.generate_tests(hyp, manifest)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.hypothesis_id == "HYP-001"
    assert "test_division_on_empty_input" in artifact.code
    assert artifact.strategy == "boundary_empty_input"
    assert artifact.timeout_seconds > 0


def test_breaker_generates_mutable_default_test() -> None:
    hyp = DefectHypothesis(
        id="HYP-002",
        finding_id="FIND-002",
        target_file="buggy.py",
        target_function="append_to_list",
        preconditions="Multiple calls",
        trigger_input="Consecutive calls",
        expected_behavior="Independent lists",
        defect_behavior="Shared state",
        rationale="Mutable default argument in buggy.py",
    )
    manifest = RepositoryManifest(root_path=".", source_files=["buggy.py"])

    breaker = BreakerAgent()
    artifacts = breaker.generate_tests(hyp, manifest)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.hypothesis_id == "HYP-002"
    assert "test_mutable_default_isolation" in artifact.code
    assert artifact.strategy == "state_accumulation"

