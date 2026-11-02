"""Finding aggregation, normalization, and deduplication engine."""

from pathlib import Path

from adversary.analysis.static.ast_rules import DeterministicASTAnalyzer
from adversary.analysis.static.ruff_adapter import RuffAnalyzer
from adversary.core.interfaces import StaticAnalyzerProtocol
from adversary.core.logging import get_logger
from adversary.models.schemas import CandidateFinding, RepositoryManifest

logger = get_logger("adversary.analysis.findings.engine")


class FindingEngine:
    """Coordinates static analyzers, normalizes IDs, and deduplicates overlapping findings."""

    def __init__(self, analyzers: list[StaticAnalyzerProtocol] | None = None) -> None:
        if analyzers is None:
            self.analyzers: list[StaticAnalyzerProtocol] = [
                DeterministicASTAnalyzer(),
                RuffAnalyzer(),
            ]
        else:
            self.analyzers = analyzers

    def analyze_repository(
        self, repo_path: Path, manifest: RepositoryManifest
    ) -> list[CandidateFinding]:
        """Run all configured analyzers and deduplicate candidate findings."""
        raw_findings: list[CandidateFinding] = []

        for analyzer in self.analyzers:
            try:
                analyzer_findings = analyzer.analyze(repo_path, manifest)
                logger.info(
                    "Analyzer '%s' reported %d findings", analyzer.name, len(analyzer_findings)
                )
                raw_findings.extend(analyzer_findings)
            except Exception as e:
                logger.warning("Analyzer '%s' encountered error: %s", analyzer.name, e)

        return self.deduplicate_and_normalize(raw_findings)

    def deduplicate_and_normalize(self, findings: list[CandidateFinding]) -> list[CandidateFinding]:
        """Deduplicate findings sharing file and line ranges, and assign sequential IDs."""
        deduped: list[CandidateFinding] = []
        seen_keys: set[str] = set()

        for finding in findings:
            key = f"{finding.location.file_path}:{finding.location.line_start}:{finding.category}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(finding)

        # Normalize IDs sequentially: FIND-001, FIND-002, ...
        normalized: list[CandidateFinding] = []
        for i, f in enumerate(deduped, 1):
            normalized.append(
                CandidateFinding(
                    id=f"FIND-{i:03d}",
                    title=f.title,
                    description=f.description,
                    category=f.category,
                    severity=f.severity,
                    confidence=f.confidence,
                    location=f.location,
                    originating_tool=f.originating_tool,
                    rule_id=f.rule_id,
                    suggested_remediation=f.suggested_remediation,
                    verification_status=f.verification_status,
                    source_hash=f.source_hash,
                )
            )

        return normalized
