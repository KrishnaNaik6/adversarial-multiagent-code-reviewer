"""Unit tests for repository scanning and path safety."""

from pathlib import Path

from adversary.repository.git import get_git_info
from adversary.repository.scanner import RepositoryScanner, is_safe_path


def test_is_safe_path(tmp_path: Path) -> None:
    safe_file = tmp_path / "src" / "main.py"
    safe_file.parent.mkdir()
    safe_file.write_text("print('hello')")

    assert is_safe_path(safe_file, tmp_path) is True

    # Path outside base directory
    outside_dir = tmp_path.parent / "outside.py"
    assert is_safe_path(outside_dir, tmp_path) is False


def test_scanner_discovers_sources_and_tests(tmp_path: Path) -> None:
    # Setup mock repo structure
    src_dir = tmp_path / "src"
    test_dir = tmp_path / "tests"
    ignored_dir = tmp_path / ".venv" / "lib"
    src_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    ignored_dir.mkdir(parents=True)

    (src_dir / "calculator.py").write_text("def add(a, b): return a + b\n")
    (test_dir / "test_calculator.py").write_text("def test_add(): pass\n")
    (ignored_dir / "ignored.py").write_text("# ignored\n")

    scanner = RepositoryScanner()
    manifest = scanner.scan(tmp_path)

    assert "src/calculator.py" in manifest.source_files
    assert "tests/test_calculator.py" in manifest.test_files
    assert not any(".venv" in f for f in manifest.source_files)
    assert not any(".venv" in f for f in manifest.test_files)
    assert manifest.total_lines >= 2


def test_git_info_extraction(tmp_path: Path) -> None:
    info = get_git_info(tmp_path)
    # Outside git repo, commit and branch are None
    assert info["commit"] is None
    assert info["branch"] is None

    # Current working workspace is a git repo
    active_info = get_git_info(Path.cwd())
    assert active_info["commit"] is not None
