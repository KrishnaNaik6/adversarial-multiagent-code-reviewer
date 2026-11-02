"""Safe repository discovery and manifest builder."""

import hashlib
from pathlib import Path

from adversary.analysis.ast.inspector import ASTInspector
from adversary.core.errors import PathTraversalError
from adversary.core.logging import get_logger
from adversary.models.schemas import ASTModuleInfo, RepositoryManifest
from adversary.repository.git import get_git_info

logger = get_logger("adversary.repository.scanner")

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    "build",
    "dist",
    "node_modules",
    ".adversary",
}


def is_safe_path(candidate_path: Path, base_dir: Path) -> bool:
    """Verify that candidate_path does not escape base_dir via symlinks or traversal."""
    try:
        resolved_base = base_dir.resolve(strict=True)
        resolved_candidate = candidate_path.resolve(strict=False)
        return resolved_candidate.is_relative_to(resolved_base)
    except (ValueError, RuntimeError):
        return False


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class RepositoryScanner:
    """Scans local repositories, validates security boundaries, and extracts AST manifests."""

    def __init__(self, ignore_dirs: set[str] | None = None) -> None:
        self.ignore_dirs = DEFAULT_IGNORE_DIRS if ignore_dirs is None else ignore_dirs
        self.ast_inspector = ASTInspector()

    def scan(self, repo_path: Path) -> RepositoryManifest:
        """Scan repository and produce structured manifest."""
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        canonical_repo = repo_path.resolve()
        logger.info("Scanning repository at %s", canonical_repo)

        source_files: list[str] = []
        test_files: list[str] = []
        modules: dict[str, ASTModuleInfo] = {}
        total_lines = 0

        for file_path in canonical_repo.rglob("*.py"):
            # Check for path traversal / symlink escapement
            if not is_safe_path(file_path, canonical_repo):
                logger.warning("Skipping unsafe path escaping repository root: %s", file_path)
                raise PathTraversalError(f"Detected path traversal attempting to escape repository: {file_path}")

            # Check if any part of the path is in ignore list
            rel_parts = file_path.relative_to(canonical_repo).parts
            if any(part in self.ignore_dirs for part in rel_parts):
                continue

            rel_str = str(file_path.relative_to(canonical_repo)).replace("\\", "/")
            is_test = (
                file_path.name.startswith("test_")
                or file_path.name.endswith("_test.py")
                or "tests" in rel_parts
            )

            if is_test:
                test_files.append(rel_str)
            else:
                source_files.append(rel_str)

            # Extract AST module info
            sha256 = compute_file_sha256(file_path)
            module_info = self.ast_inspector.inspect_file(file_path, rel_str, sha256)
            modules[rel_str] = module_info
            total_lines += module_info.line_count

        git_meta = get_git_info(canonical_repo)

        return RepositoryManifest(
            root_path=str(canonical_repo),
            git_commit=git_meta.get("commit"),
            source_files=sorted(source_files),
            test_files=sorted(test_files),
            total_lines=total_lines,
            modules=modules,
        )
