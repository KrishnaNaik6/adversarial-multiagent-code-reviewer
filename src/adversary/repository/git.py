"""Safe git metadata extraction."""

import subprocess
from pathlib import Path


def get_git_info(repo_path: Path) -> dict[str, str | None]:
    """Retrieve git commit SHA and branch name if repo is a git repository."""
    info: dict[str, str | None] = {"commit": None, "branch": None}
    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return info

    try:
        # Get HEAD commit hash
        res_commit = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res_commit.returncode == 0:
            info["commit"] = res_commit.stdout.strip()

        # Get active branch name
        res_branch = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res_branch.returncode == 0:
            info["branch"] = res_branch.stdout.strip()

    except Exception:
        # Git operations must fail gracefully
        pass

    return info
