"""Deterministic AST vulnerability and defect pattern detectors."""

import ast
from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.enums import Confidence, FindingCategory, Severity
from adversary.models.schemas import CandidateFinding, RepositoryManifest, SourceLocation

logger = get_logger("adversary.analysis.static.ast_rules")


class ASTPatternVisitor(ast.NodeVisitor):
    """Walks module AST looking for deterministic defect anti-patterns."""

    def __init__(self, relative_path: str, source_hash: str) -> None:
        self.relative_path = relative_path
        self.source_hash = source_hash
        self.findings: list[CandidateFinding] = []
        self._counter = 1
        self._guarded_vars: set[str] = set()

    def _next_id(self, rule_prefix: str) -> str:
        fid = f"FIND-{rule_prefix}-{self._counter:03d}"
        self._counter += 1
        return fid

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        prev_guards = set(self._guarded_vars)
        self._collect_guards(node.body)
        self._check_mutable_defaults(node)
        self.generic_visit(node)
        self._guarded_vars = prev_guards

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        prev_guards = set(self._guarded_vars)
        self._collect_guards(node.body)
        self._check_mutable_defaults(node)
        self.generic_visit(node)
        self._guarded_vars = prev_guards

    def _collect_guards(self, statements: list[ast.stmt]) -> None:
        """Identify variables that are checked for emptiness/zero before exit."""
        for stmt in statements:
            if isinstance(stmt, ast.If):
                # Check if if-body terminates execution via return or raise
                terminates = any(isinstance(sub, (ast.Return, ast.Raise)) for sub in stmt.body)
                if terminates:
                    # e.g., if not numbers: return
                    if isinstance(stmt.test, ast.UnaryOp) and isinstance(stmt.test.op, ast.Not):
                        if isinstance(stmt.test.operand, ast.Name):
                            self._guarded_vars.add(stmt.test.operand.id)
                    # e.g., if len(numbers) == 0: return
                    elif (
                        isinstance(stmt.test, ast.Compare)
                        and isinstance(stmt.test.left, ast.Call)
                        and isinstance(stmt.test.left.func, ast.Name)
                        and stmt.test.left.func.id == "len"
                        and stmt.test.left.args
                    ):
                        arg0 = stmt.test.left.args[0]
                        if isinstance(arg0, ast.Name):
                            self._guarded_vars.add(arg0.id)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        # Check division by zero or unverified denominator
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.findings.append(
                    CandidateFinding(
                        id=self._next_id("DIV"),
                        title="Literal division by zero",
                        description="Operation divides by constant zero, which will immediately raise ZeroDivisionError at runtime.",
                        category=FindingCategory.CORRECTNESS,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        location=SourceLocation(
                            file_path=self.relative_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        ),
                        originating_tool="ast_rules",
                        rule_id="AST-DIV-001",
                        suggested_remediation="Ensure the denominator is non-zero before performing division.",
                        source_hash=self.source_hash,
                    )
                )
            elif (
                isinstance(node.right, ast.Call)
                and isinstance(node.right.func, ast.Name)
                and node.right.func.id == "len"
            ):
                arg_name = (
                    node.right.args[0].id
                    if node.right.args and isinstance(node.right.args[0], ast.Name)
                    else None
                )
                if arg_name not in self._guarded_vars:
                    self.findings.append(
                        CandidateFinding(
                            id=self._next_id("DIV"),
                            title="Potential division by zero with empty collection",
                            description="Division by len(...) without non-empty check. Will raise ZeroDivisionError when passed an empty sequence.",
                            category=FindingCategory.BOUNDARY_CONDITION,
                            severity=Severity.HIGH,
                            confidence=Confidence.HIGH,
                            location=SourceLocation(
                                file_path=self.relative_path,
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                            ),
                            originating_tool="ast_rules",
                            rule_id="AST-DIV-002",
                            suggested_remediation="Add a check if collection is empty before calculating average or division.",
                            source_hash=self.source_hash,
                        )
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check insecure command execution: os.system or shell=True
        if isinstance(node.func, ast.Attribute) and node.func.attr == "system":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                self.findings.append(
                    CandidateFinding(
                        id=self._next_id("SEC"),
                        title="Insecure command execution with os.system",
                        description="os.system executes commands in a subshell without input sanitization, creating command injection vulnerabilities.",
                        category=FindingCategory.SECURITY,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        location=SourceLocation(
                            file_path=self.relative_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        ),
                        originating_tool="ast_rules",
                        rule_id="AST-SEC-001",
                        suggested_remediation="Use subprocess.run with argument sequence and shell=False.",
                        source_hash=self.source_hash,
                    )
                )
        elif isinstance(node.func, ast.Attribute) and node.func.attr in {"Popen", "run", "call"}:
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    self.findings.append(
                        CandidateFinding(
                            id=self._next_id("SEC"),
                            title="Subprocess execution with shell=True",
                            description="Executing subprocess with shell=True allows command injection if parameters contain untrusted input.",
                            category=FindingCategory.SECURITY,
                            severity=Severity.HIGH,
                            confidence=Confidence.HIGH,
                            location=SourceLocation(
                                file_path=self.relative_path,
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                            ),
                            originating_tool="ast_rules",
                            rule_id="AST-SEC-002",
                            suggested_remediation="Pass command as a list of strings and set shell=False.",
                            source_hash=self.source_hash,
                        )
                    )
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Check swallowed exceptions: pass in handler
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(
                CandidateFinding(
                    id=self._next_id("EXC"),
                    title="Silently swallowed exception",
                    description="Empty except block with pass statement suppresses errors silently, masking unexpected bugs.",
                    category=FindingCategory.EXCEPTION_HANDLING,
                    severity=Severity.MEDIUM,
                    confidence=Confidence.HIGH,
                    location=SourceLocation(
                        file_path=self.relative_path,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                    ),
                    originating_tool="ast_rules",
                    rule_id="AST-EXC-001",
                    suggested_remediation="Log the exception or handle specific expected exceptions appropriately.",
                    source_hash=self.source_hash,
                )
            )
        self.generic_visit(node)

    def _check_mutable_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(
                    CandidateFinding(
                        id=self._next_id("MUT"),
                        title=f"Mutable default argument in function '{node.name}'",
                        description=f"Default argument is mutated across calls to '{node.name}'. Use None as default value instead.",
                        category=FindingCategory.CORRECTNESS,
                        severity=Severity.MEDIUM,
                        confidence=Confidence.HIGH,
                        location=SourceLocation(
                            file_path=self.relative_path,
                            line_start=node.lineno,
                            line_end=node.end_lineno or node.lineno,
                        ),
                        originating_tool="ast_rules",
                        rule_id="AST-MUT-001",
                        suggested_remediation="Set default to None and initialize mutable collection inside function body.",
                        source_hash=self.source_hash,
                    )
                )


class DeterministicASTAnalyzer:
    """Runs deterministic AST pattern checks across repository manifest files."""

    name: str = "deterministic_ast"

    def analyze(self, repo_path: Path, manifest: RepositoryManifest) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        for rel_file in manifest.source_files:
            abs_file = repo_path / rel_file
            if not abs_file.exists():
                continue

            try:
                content = abs_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content, filename=str(abs_file))
            except Exception as e:
                logger.warning("Could not parse %s for AST analysis: %s", rel_file, e)
                continue

            module_info = manifest.modules.get(rel_file)
            source_hash = module_info.sha256_hash if module_info else ""

            visitor = ASTPatternVisitor(rel_file, source_hash)
            visitor.visit(tree)
            findings.extend(visitor.findings)

        return findings
