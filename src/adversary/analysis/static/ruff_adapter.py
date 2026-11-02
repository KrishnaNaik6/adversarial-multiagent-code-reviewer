"""Ruff static analysis adapter."""

import json
import shutil
import subprocess
from pathlib import Path

from adversary.core.logging import get_logger
from adversary.models.enums import Confidence, FindingCategory, Severity
from adversary.models.schemas import CandidateFinding, RepositoryManifest, SourceLocation

logger = get_logger("adversary.analysis.static.ruff")


class RuffAnalyzer:
    """Executes Ruff static analysis and normalizes findings into domain schemas."""

    name: str = "ruff"

    def analyze(self, repo_path: Path, manifest: RepositoryManifest) -> list[CandidateFinding]:
        ruff_bin = shutil.which("ruff")
        if not ruff_bin:
            logger.info("Ruff binary not found in PATH; skipping ruff analysis")
            return []

        findings: list[CandidateFinding] = []
        try:
            res = subprocess.run(
                [ruff_bin, "check", "--output-format", "json", str(repo_path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            # Ruff outputs JSON array of diagnostics even when return code is 1 (found errors)
            if not res.stdout.strip():
                return findings

            diagnostics = json.loads(res.stdout)
            for i, diag in enumerate(diagnostics, 1):
                raw_filename = diag.get("filename", "")
                try:
                    rel_path = str(Path(raw_filename).relative_to(repo_path)).replace("\\", "/")
                except ValueError:
                    rel_path = raw_filename

                # Only include files in our scanned manifest source_files
                if rel_path not in manifest.source_files:
                    continue

                code = diag.get("code", "RUFF-GEN")
                category = self._map_category(code)
                severity = self._map_severity(code)

                location = SourceLocation(
                    file_path=rel_path,
                    line_start=diag.get("location", {}).get("row", 1),
                    line_end=diag.get("end_location", {}).get("row", 1),
                    col_start=diag.get("location", {}).get("column"),
                    col_end=diag.get("end_location", {}).get("column"),
                )

                module_info = manifest.modules.get(rel_path)
                source_hash = module_info.sha256_hash if module_info else None

                finding = CandidateFinding(
                    id=f"FIND-RUFF-{i:03d}",
                    title=f"Ruff [{code}]: {diag.get('message', '')}",
                    description=diag.get("message", "Static analyzer diagnostic"),
                    category=category,
                    severity=severity,
                    confidence=Confidence.MEDIUM,
                    location=location,
                    originating_tool="ruff",
                    rule_id=code,
                    suggested_remediation=diag.get("fix", {}).get("message")
                    if diag.get("fix")
                    else None,
                    source_hash=source_hash,
                )
                findings.append(finding)

        except Exception as e:
            logger.warning("Ruff analysis failed: %s", e)

        return findings

    def _map_category(self, code: str) -> FindingCategory:
        if code.startswith("S"):
            return FindingCategory.SECURITY
        if code.startswith("B"):
            return FindingCategory.CORRECTNESS
        if code.startswith("E") or code.startswith("F"):
            return FindingCategory.CORRECTNESS
        return FindingCategory.CORRECTNESS

    def _map_severity(self, code: str) -> Severity:
        if code.startswith("S"):
            return Severity.HIGH
        if code in {"F821", "F822", "E999"}:  # Undefined names, syntax error
            return Severity.HIGH
        if code.startswith("B"):
            return Severity.MEDIUM
        return Severity.LOW
