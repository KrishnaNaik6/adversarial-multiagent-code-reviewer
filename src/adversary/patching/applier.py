"""Safe patch applier enforcing human approval barriers."""

import re
from pathlib import Path

from adversary.core.errors import PatchError
from adversary.core.logging import get_logger
from adversary.models.schemas import PatchArtifact

logger = get_logger("adversary.patching.applier")


class PatchApplier:
    """Applies validated patches to the target repository only upon explicit human approval."""

    def apply_patch(
        self,
        patch: PatchArtifact,
        repo_path: Path,
        human_approved: bool = False,
    ) -> bool:
        """Apply patch diff to original repository, strictly gated by human approval."""
        if not human_approved:
            logger.warning("Attempted to apply patch %s without human approval gate.", patch.id)
            raise PatchError("Applying patch to the working repository requires explicit human approval.")

        if not patch.affected_files:
            raise PatchError("Patch does not specify any affected files.")

        target_file = repo_path / patch.affected_files[0]
        if not target_file.exists():
            raise PatchError(f"Target file to patch does not exist: {target_file}")

        # Parse simple additions from unified diff
        diff_lines = patch.diff.splitlines()
        added_lines: list[str] = []
        target_line_num: int = 1

        for line in diff_lines:
            if line.startswith("@@"):
                # e.g., @@ -8,3 +8,5 @@
                match = re.search(r"\+(\d+)", line)
                if match:
                    target_line_num = int(match.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])

        if not added_lines:
            raise PatchError("Could not extract patch additions from diff.")

        original_lines = target_file.read_text(encoding="utf-8").splitlines(keepends=True)
        insert_idx = max(0, min(target_line_num - 1, len(original_lines)))

        # Insert added lines
        for added in reversed(added_lines):
            original_lines.insert(insert_idx, added + "\n")

        target_file.write_text("".join(original_lines), encoding="utf-8")
        patch.applied_to_repo = True
        logger.info("Successfully applied patch %s to %s with human approval.", patch.id, target_file)
        return True

