"""Unit tests for deterministic static analysis and hypothesis generation."""

from pathlib import Path

from adversary.analysis.findings.engine import FindingEngine
from adversary.analysis.static.ast_rules import DeterministicASTAnalyzer
from adversary.hypotheses.generator import HypothesisGenerator
from adversary.repository.scanner import RepositoryScanner


def test_ast_rules_on_fixtures() -> None:
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    scanner = RepositoryScanner()
    manifest = scanner.scan(fixtures_dir)

    analyzer = DeterministicASTAnalyzer()
    findings = analyzer.analyze(fixtures_dir, manifest)

    # Check that buggy.py findings are found
    buggy_findings = [f for f in findings if "buggy.py" in f.location.file_path]
    clean_findings = [f for f in findings if "clean.py" in f.location.file_path]

    # Clean file should trigger 0 findings
    assert len(clean_findings) == 0

    # Buggy file should have all seeded defects detected
    rule_ids = {f.rule_id for f in buggy_findings}
    assert "AST-DIV-002" in rule_ids  # division by len
    assert "AST-MUT-001" in rule_ids  # mutable default
    assert "AST-SEC-001" in rule_ids  # os.system
    assert "AST-EXC-001" in rule_ids  # swallowed exception


def test_finding_engine_deduplication() -> None:
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    scanner = RepositoryScanner()
    manifest = scanner.scan(fixtures_dir)

    engine = FindingEngine()
    findings = engine.analyze_repository(fixtures_dir, manifest)

    assert len(findings) >= 4
    # Check sequential IDs
    assert findings[0].id == "FIND-001"
    assert findings[1].id == "FIND-002"


def test_hypothesis_generation() -> None:
    fixtures_dir = Path(__file__).parent.parent / "fixtures" / "sample_repo"
    scanner = RepositoryScanner()
    manifest = scanner.scan(fixtures_dir)

    engine = FindingEngine()
    findings = engine.analyze_repository(fixtures_dir, manifest)

    generator = HypothesisGenerator()
    hypotheses = generator.generate_hypotheses(findings, manifest)

    assert len(hypotheses) == len(findings)
    assert hypotheses[0].id == "HYP-001"
    assert hypotheses[0].finding_id == findings[0].id

    # Verify target function resolution
    div_hyp = next(h for h in hypotheses if "ZeroDivisionError" in h.defect_behavior)
    assert div_hyp.target_function == "calculate_average"
    assert "empty sequence" in div_hyp.preconditions
