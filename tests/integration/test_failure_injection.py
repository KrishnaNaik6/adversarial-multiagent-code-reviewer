"""Integration tests: Chaos and failure injection testing."""

from pathlib import Path

import pytest

from adversary.orchestration.coordinator import ReviewOrchestrator
from adversary.repository.scanner import RepositoryScanner


def test_corrupted_syntax_does_not_abort_scan(tmp_path: Path) -> None:
    # 1 good file, 1 corrupted syntax file
    (tmp_path / "valid.py").write_text("def ok(): return 1\n", encoding="utf-8")
    (tmp_path / "corrupt.py").write_text("def broken(x\n  return x +", encoding="utf-8")

    scanner = RepositoryScanner()
    manifest = scanner.scan(tmp_path)

    assert "valid.py" in manifest.source_files
    assert "corrupt.py" in manifest.source_files
    assert manifest.modules["valid.py"].line_count >= 1
    assert manifest.modules["corrupt.py"].line_count >= 1


def test_nonexistent_repo_raises_clear_error(tmp_path: Path) -> None:
    non_existent = tmp_path / "non_existent_dir_12345"
    orchestrator = ReviewOrchestrator()
    with pytest.raises(FileNotFoundError):
        orchestrator.run(non_existent)


def test_orchestrator_handles_empty_repo(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_repo"
    empty_dir.mkdir()

    orchestrator = ReviewOrchestrator()
    report = orchestrator.run(empty_dir)

    assert report.summary["total_findings"] == 0
    assert report.summary["confirmed"] == 0

