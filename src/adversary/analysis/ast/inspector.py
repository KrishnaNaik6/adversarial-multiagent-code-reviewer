"""Python AST inspection and symbol extraction."""

import ast
from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.schemas import ASTClassInfo, ASTFunctionInfo, ASTModuleInfo

logger = get_logger("adversary.analysis.ast.inspector")


class CallVisitor(ast.NodeVisitor):
    """Collects names of all functions and methods called within an AST subtree."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(node.func.attr)
        self.generic_visit(node)


class ASTInspector:
    """Inspects Python source code and extracts functions, classes, imports, and calls."""

    def inspect_file(self, file_path: Path, relative_path: str, sha256_hash: str) -> ASTModuleInfo:
        """Parse Python source file and return structured module symbols."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning("Could not read file %s: %s", file_path, e)
            return ASTModuleInfo(
                file_path=str(file_path),
                relative_path=relative_path,
                imports=[],
                functions=[],
                classes=[],
                sha256_hash=sha256_hash,
                line_count=0,
            )

        line_count = len(content.splitlines())

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            logger.warning("Syntax error in %s: line %s: %s", relative_path, e.lineno, e.msg)
            return ASTModuleInfo(
                file_path=str(file_path),
                relative_path=relative_path,
                imports=[],
                functions=[],
                classes=[],
                sha256_hash=sha256_hash,
                line_count=line_count,
            )

        imports: list[str] = []
        functions: list[ASTFunctionInfo] = []
        classes: list[ASTClassInfo] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for alias in node.names:
                    imports.append(f"{module_name}.{alias.name}" if module_name else alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(self._parse_function(node))
            elif isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node))

        return ASTModuleInfo(
            file_path=str(file_path),
            relative_path=relative_path,
            imports=imports,
            functions=functions,
            classes=classes,
            sha256_hash=sha256_hash,
            line_count=line_count,
        )

    def _parse_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ASTFunctionInfo:
        """Extract function metadata, docstring, arguments, return type, and calls."""
        docstring = ast.get_docstring(node)
        args = [arg.arg for arg in node.args.args]

        returns: str | None = None
        if node.returns is not None:
            returns = ast.unparse(node.returns)

        # Collect function calls within body
        visitor = CallVisitor()
        for child in node.body:
            visitor.visit(child)

        return ASTFunctionInfo(
            name=node.name,
            docstring=docstring,
            args=args,
            returns=returns,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            called_functions=visitor.calls,
        )

    def _parse_class(self, node: ast.ClassDef) -> ASTClassInfo:
        """Extract class metadata, docstring, and member methods."""
        docstring = ast.get_docstring(node)
        methods: list[ASTFunctionInfo] = []

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._parse_function(item))

        return ASTClassInfo(
            name=node.name,
            docstring=docstring,
            methods=methods,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )
