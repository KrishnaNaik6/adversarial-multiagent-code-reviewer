"""Unit tests for AST inspection and symbol extraction."""

from pathlib import Path

from adversary.analysis.ast.inspector import ASTInspector


def test_ast_inspect_functions_and_classes(tmp_path: Path) -> None:
    code = '''"""Module docstring."""
import os
from math import sqrt

class Calculator:
    """Class docstring."""
    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

async def async_fetch(url: str) -> str:
    res = sqrt(16)
    return f"Fetched {res}"
'''
    file_path = tmp_path / "sample.py"
    file_path.write_text(code, encoding="utf-8")

    inspector = ASTInspector()
    info = inspector.inspect_file(file_path, "sample.py", "dummy_sha")

    assert "os" in info.imports
    assert "math.sqrt" in info.imports
    assert len(info.classes) == 1
    assert info.classes[0].name == "Calculator"
    assert info.classes[0].docstring == "Class docstring."
    assert len(info.classes[0].methods) == 1
    assert info.classes[0].methods[0].name == "multiply"
    assert info.classes[0].methods[0].args == ["self", "x", "y"]
    assert info.classes[0].methods[0].returns == "int"

    assert len(info.functions) == 1
    assert info.functions[0].name == "async_fetch"
    assert info.functions[0].is_async is True
    assert "sqrt" in info.functions[0].called_functions


def test_ast_syntax_error_resilience(tmp_path: Path) -> None:
    broken_code = "def broken_syntax(x\n    return x +"
    file_path = tmp_path / "broken.py"
    file_path.write_text(broken_code, encoding="utf-8")

    inspector = ASTInspector()
    info = inspector.inspect_file(file_path, "broken.py", "dummy_sha")

    assert info.line_count == 2
    assert len(info.functions) == 0
    assert len(info.classes) == 0
