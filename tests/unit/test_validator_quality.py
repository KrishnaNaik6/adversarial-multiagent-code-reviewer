"""Unit tests for breaker test quality assessment and validation."""

from adversary.models.enums import TestValidationStatus
from adversary.test_generation.validator import TestValidator


def test_validator_accepts_valid_targeted_test() -> None:
    validator = TestValidator()
    code = """
def test_pricing_calculation():
    from shopcore.pricing import calculate_order_totals
    res = calculate_order_totals([10], 0)
    assert res["total"] == 10
"""
    result = validator.assess_quality(code, target_func="calculate_order_totals")
    assert result.is_valid is True
    assert result.status == TestValidationStatus.VALID
    assert "valid_ast_syntax" in result.checks_passed
    assert "contains_executable_assertions" in result.checks_passed
    assert any("linked_to_target" in c for c in result.checks_passed)


def test_validator_rejects_syntax_error() -> None:
    validator = TestValidator()
    code = "def test_broken(:"
    result = validator.assess_quality(code, target_func="broken")
    assert result.is_valid is False
    assert result.status == TestValidationStatus.SYNTAX_ERROR


def test_validator_rejects_disallowed_modules() -> None:
    validator = TestValidator()
    code = """
import socket

def test_exploit():
    s = socket.socket()
    assert True
"""
    result = validator.assess_quality(code, target_func="exploit")
    assert result.is_valid is False
    assert result.status == TestValidationStatus.DISALLOWED_MODULE


def test_validator_rejects_vacuous_unasserted_test() -> None:
    validator = TestValidator()
    code = """
def test_no_assertions():
    from shopcore.pricing import calculate_order_totals
    calculate_order_totals([], 0)
"""
    result = validator.assess_quality(code, target_func="calculate_order_totals")
    assert result.is_valid is False
    assert result.status == TestValidationStatus.VACUOUS_OR_UNASSERTED


def test_validator_rejects_unlinked_target() -> None:
    validator = TestValidator()
    code = """
def test_unrelated():
    assert 1 + 1 == 2
"""
    result = validator.assess_quality(code, target_func="calculate_order_totals")
    assert result.is_valid is False
    assert result.status == TestValidationStatus.UNLINKED_TARGET
