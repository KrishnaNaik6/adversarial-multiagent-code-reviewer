"""Syntax and safety validation for generated test artifacts."""

import ast

from adversary.core.errors import TestGenerationError
from adversary.core.logging import get_logger
from adversary.models.enums import TestValidationStatus
from adversary.models.schemas import TestValidationResult

logger = get_logger("adversary.test_generation.validator")

# Unsafe symbols or modules that should never be invoked in generated tests
DISALLOWED_MODULES = {"shutil", "socket", "urllib", "http", "ftplib", "subprocess"}


class SafetyVisitor(ast.NodeVisitor):
    """AST visitor that checks for dangerous calls or imports in test code."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root_mod = alias.name.split(".")[0]
            if root_mod in DISALLOWED_MODULES:
                self.violations.append(f"Disallowed module import in test: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in DISALLOWED_MODULES:
            self.violations.append(f"Disallowed module import in test: {node.module}")
        self.generic_visit(node)


class TestValidator:
    """Validates syntax, structure, capability, and security constraints of generated tests."""

    def assess_quality(
        self, test_code: str, target_func: str | None = None
    ) -> TestValidationResult:
        """Perform multi-dimensional quality assessment on generated test artifact."""
        checks_passed: list[str] = []
        reasons: list[str] = []

        if not test_code or not test_code.strip():
            return TestValidationResult(
                is_valid=False,
                status=TestValidationStatus.SYNTAX_ERROR,
                reasons=["Generated test code is empty."],
                checks_passed=[],
            )

        try:
            tree = ast.parse(test_code, filename="<generated_test>")
            checks_passed.append("valid_ast_syntax")
        except SyntaxError as e:
            return TestValidationResult(
                is_valid=False,
                status=TestValidationStatus.SYNTAX_ERROR,
                reasons=[f"Syntax error at line {e.lineno}: {e.msg}"],
                checks_passed=[],
            )

        # 1. Safety check
        safety = SafetyVisitor()
        safety.visit(tree)
        if safety.violations:
            return TestValidationResult(
                is_valid=False,
                status=TestValidationStatus.DISALLOWED_MODULE,
                reasons=safety.violations,
                checks_passed=checks_passed,
            )
        checks_passed.append("safe_imports_and_calls")

        # 2. Check for test_* functions
        has_test_func = any(
            isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            for node in tree.body
        )
        if not has_test_func:
            return TestValidationResult(
                is_valid=False,
                status=TestValidationStatus.VACUOUS_OR_UNASSERTED,
                reasons=["Test artifact does not define any 'test_*' functions."],
                checks_passed=checks_passed,
            )
        checks_passed.append("has_test_function")

        # 3. Check for assertions or exception triggers (must not be a vacuous test)
        has_assertion = any(
            isinstance(node, ast.Assert)
            or (
                isinstance(node, ast.Call)
                and getattr(node.func, "attr", "") in {"raises", "fail"}
            )
            for node in ast.walk(tree)
        )
        if not has_assertion:
            return TestValidationResult(
                is_valid=False,
                status=TestValidationStatus.VACUOUS_OR_UNASSERTED,
                reasons=["Test is vacuous: contains no assert statements or exception validations."],
                checks_passed=checks_passed,
            )
        checks_passed.append("contains_executable_assertions")

        # 4. Check target linkage if target function is specified
        if target_func:
            pure_func = target_func.split(".")[-1]
            has_target_ref = any(
                isinstance(node, ast.Name) and node.id == pure_func
                or (isinstance(node, ast.Attribute) and node.attr == pure_func)
                or (isinstance(node, ast.alias) and node.name == pure_func)
                for node in ast.walk(tree)
            )
            if not has_target_ref:
                reasons.append(
                    f"Test code does not reference target entity '{pure_func}'."
                )
                return TestValidationResult(
                    is_valid=False,
                    status=TestValidationStatus.UNLINKED_TARGET,
                    reasons=reasons,
                    checks_passed=checks_passed,
                )
            checks_passed.append(f"linked_to_target_{pure_func}")

        return TestValidationResult(
            is_valid=True,
            status=TestValidationStatus.VALID,
            reasons=[],
            checks_passed=checks_passed,
        )

    def validate(self, test_code: str, target_func: str | None = None) -> None:
        """Parse and validate generated test code, raising TestGenerationError if invalid."""
        result = self.assess_quality(test_code, target_func)
        if not result.is_valid:
            raise TestGenerationError(
                f"Generated test failed validation ({result.status.value}): {'; '.join(result.reasons)}"
            )
