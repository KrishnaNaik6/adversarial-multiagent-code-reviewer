"""Security tests: Path traversal and boundary escape prevention."""

from pathlib import Path

from adversary.repository.scanner import RepositoryScanner, is_safe_path


def test_path_traversal_detection(tmp_path: Path) -> None:
    safe_dir = tmp_path / "target_repo"
    safe_dir.mkdir()
    secret_dir = tmp_path / "sensitive_host_dir"
    secret_dir.mkdir()
    (secret_dir / "secret.key").write_text("SUPER_SECRET_KEY")

    # Legitimate file inside safe_dir
    legit_file = safe_dir / "main.py"
    legit_file.write_text("print('hello')")
    assert is_safe_path(legit_file, safe_dir) is True

    # Relative path traversal escaping safe_dir
    traversal_path = safe_dir / ".." / "sensitive_host_dir" / "secret.key"
    assert is_safe_path(traversal_path, safe_dir) is False


def test_scanner_rejects_external_paths(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "clean.py").write_text("x = 1\n")

    scanner = RepositoryScanner()
    manifest = scanner.scan(repo_dir)

    # Manifest must only contain paths within repo_dir
    for src in manifest.source_files:
        p = repo_dir / src
        assert is_safe_path(p, repo_dir) is True

