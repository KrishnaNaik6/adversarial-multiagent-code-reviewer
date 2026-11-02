"""Syntax and safety validation for generated test artifacts."""

import ast

from adversary.core.errors import TestGenerationError
from adversary.core.logging import get_logger

logger = get_logger("adversary.test_generation.validator")

# Unsafe symbols or modules that should never be invoked in generated tests
DISALLOWED_MODULES = {"shutil", "socket", "urllib", "http", "ftplib", "subprocess"}


class SafetyVisitor(ast.NodeVisitor):
    """AST visitor that checks for dangerous calls or imports in test code."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name in DISALLOWED_MODULES:
                self.violations.append(f"Disallowed module import in test: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split(".")[0] in DISALLOWED_MODULES:
            self.violations.append(f"Disallowed module import in test: {node.module}")
        self.generic_visit(node)


class TestValidator:
    """Validates syntax, structure, and security constraints of generated tests."""

    def validate(self, test_code: str) -> None:
        """Parse and validate generated test code, raising TestGenerationError if invalid."""
        if not test_code or not test_code.strip():
            raise TestGenerationError("Generated test code is empty.")

        try:
            tree = ast.parse(test_code, filename="<generated_test>")
        except SyntaxError as e:
            raise TestGenerationError(f"Generated test contains invalid syntax at line {e.lineno}: {e.msg}") from e

        # Check safety constraints
        safety_visitor = SafetyVisitor()
        safety_visitor.visit(tree)
        if safety_visitor.violations:
            raise TestGenerationError(f"Generated test failed safety checks: {', '.join(safety_visitor.violations)}")

        # Ensure at least one test function is defined
        has_test_func = any(
            isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            for node in tree.body
        )
        if not has_test_func:
            raise TestGenerationError("Generated test does not define any 'test_*' functions.")

